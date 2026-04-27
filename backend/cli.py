"""Helm CLI — management commands."""
import asyncio
import bz2
import csv
import io
import sys
from typing import Optional

import httpx
import typer
from rich import print
from rich.table import Table

app = typer.Typer(name="helm", help="Helm management commands")
bucket_app = typer.Typer(help="Bucket management")
sde_app = typer.Typer(help="EVE Static Data Export management")

app.add_typer(bucket_app, name="bucket")
app.add_typer(sde_app, name="sde")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.run(coro)


async def _get_buckets_with_state():
    import json
    import redis.asyncio as aioredis
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.core.redis import get_pool
    from app.models.bucket import Bucket, BucketToken

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Bucket))
        buckets = list(result.scalars().all())

        rows = []
        r = aioredis.Redis(connection_pool=get_pool())
        try:
            for bucket in buckets:
                count_result = await db.execute(
                    select(func.count()).select_from(BucketToken).where(BucketToken.bucket_id == bucket.id)
                )
                token_count = count_result.scalar() or 0

                state_raw = await r.get(f"helm:bucket:{bucket.id}:state")
                state = json.loads(state_raw) if state_raw else {}
                rows.append({
                    "id": bucket.id,
                    "name": bucket.name,
                    "capacity": bucket.capacity,
                    "is_active": bucket.is_active,
                    "token_count": token_count,
                    "health": state.get("health", "unknown"),
                    "last_run_at": state.get("last_run_at", "-"),
                })
        finally:
            await r.aclose()
    return rows


# ── Bucket commands ───────────────────────────────────────────────────────────

@bucket_app.command("list")
def bucket_list():
    """List all buckets with status."""
    rows = _run(_get_buckets_with_state())
    if not rows:
        print("[yellow]No buckets found. Run migrations and restart the app to create the default bucket.[/yellow]")
        return

    table = Table(title="Helm Buckets")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Active")
    table.add_column("Tokens / Cap")
    table.add_column("Health")
    table.add_column("Last Run")

    for row in rows:
        health_color = {"available": "green", "balanced": "yellow", "overload": "red"}.get(row["health"], "white")
        table.add_row(
            str(row["id"]),
            row["name"],
            "✓" if row["is_active"] else "✗",
            f"{row['token_count']} / {row['capacity']}",
            f"[{health_color}]{row['health']}[/{health_color}]",
            row["last_run_at"],
        )
    print(table)


@bucket_app.command("info")
def bucket_info(bucket_id: int = typer.Argument(..., help="Bucket ID")):
    """Show detailed info for a single bucket."""
    rows = _run(_get_buckets_with_state())
    row = next((r for r in rows if r["id"] == bucket_id), None)
    if row is None:
        print(f"[red]Bucket {bucket_id} not found.[/red]")
        raise typer.Exit(1)

    for key, value in row.items():
        print(f"[bold]{key}:[/bold] {value}")


@bucket_app.command("balance")
def bucket_balance():
    """Redistribute BucketTokens evenly across all active buckets."""
    async def _balance():
        from sqlalchemy import select, delete
        from app.core.database import AsyncSessionLocal
        from app.models.bucket import Bucket, BucketToken
        from app.models.character import Character

        async with AsyncSessionLocal() as db:
            bucket_result = await db.execute(select(Bucket).where(Bucket.is_active == True))
            buckets = list(bucket_result.scalars().all())
            if not buckets:
                print("[red]No active buckets.[/red]")
                return

            char_result = await db.execute(select(Character.id).where(Character.is_active == True))
            char_ids = [row[0] for row in char_result.fetchall()]

            await db.execute(delete(BucketToken))

            for i, char_id in enumerate(char_ids):
                bucket = buckets[i % len(buckets)]
                db.add(BucketToken(bucket_id=bucket.id, character_id=char_id))

            await db.commit()
            print(f"[green]Balanced {len(char_ids)} characters across {len(buckets)} buckets.[/green]")

    _run(_balance())


# ── SDE commands ──────────────────────────────────────────────────────────────

@sde_app.command("import")
def sde_import(
    url: Optional[str] = typer.Option(None, "--url", help="URL to invTypes CSV or CSV.bz2"),
    file: Optional[str] = typer.Option(None, "--file", help="Path to local invTypes CSV"),
):
    """Import EVE SDE type info into the database."""
    if not url and not file:
        print("[red]Provide --url or --file.[/red]")
        raise typer.Exit(1)

    async def _import():
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from app.core.database import AsyncSessionLocal
        from app.models.sde import TypeInfo

        if url:
            print(f"[blue]Downloading SDE from {url} ...[/blue]")
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                raw = resp.content
            if url.endswith(".bz2"):
                raw = bz2.decompress(raw)
            content = raw.decode("utf-8")
        else:
            with open(file, "rb") as f:
                raw = f.read()
            if file.endswith(".bz2"):
                raw = bz2.decompress(raw)
            content = raw.decode("utf-8")

        reader = csv.DictReader(io.StringIO(content))
        batch = []
        total = 0
        BATCH_SIZE = 500

        async with AsyncSessionLocal() as db:
            for row in reader:
                try:
                    type_id = int(row.get("typeID") or row.get("type_id", 0))
                    name = row.get("typeName") or row.get("name", "")
                    if not type_id or not name:
                        continue
                    batch.append({
                        "type_id": type_id,
                        "name": name,
                        "description": row.get("description", "") or "",
                        "group_id": int(row["groupID"]) if row.get("groupID") else None,
                        "mass": float(row["mass"]) if row.get("mass") else None,
                        "volume": float(row["volume"]) if row.get("volume") else None,
                    })
                except (ValueError, KeyError):
                    continue

                if len(batch) >= BATCH_SIZE:
                    stmt = pg_insert(TypeInfo).values(batch).on_conflict_do_update(
                        index_elements=["type_id"],
                        set_={"name": pg_insert(TypeInfo).excluded.name, "description": pg_insert(TypeInfo).excluded.description},
                    )
                    await db.execute(stmt)
                    await db.commit()
                    total += len(batch)
                    batch = []
                    print(f"  [dim]{total} rows imported...[/dim]", end="\r")

            if batch:
                stmt = pg_insert(TypeInfo).values(batch).on_conflict_do_update(
                    index_elements=["type_id"],
                    set_={"name": pg_insert(TypeInfo).excluded.name, "description": pg_insert(TypeInfo).excluded.description},
                )
                await db.execute(stmt)
                await db.commit()
                total += len(batch)

        print(f"\n[green]SDE import complete: {total} type records.[/green]")

    _run(_import())


if __name__ == "__main__":
    app()
