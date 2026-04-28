"""SDE import Celery task — official JSONL format with multi-language support."""
import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import redis.asyncio as aioredis
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_pool
from app.models.sde import SDECategory, SDEGroup, SDEType
from app.tasks.celery_app import celery_app
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)

BATCH_SIZE = 500

REDIS_KEY_STATUS = "helm:sde:status"
REDIS_KEY_VERSION = "helm:sde:version"
REDIS_KEY_RELEASE_DATE = "helm:sde:release_date"
REDIS_KEY_ROW_COUNT = "helm:sde:row_count"
REDIS_KEY_LAST_IMPORT_AT = "helm:sde:last_import_at"
REDIS_KEY_LAST_ERROR = "helm:sde:last_error"
REDIS_KEY_SOURCE_URL = "helm:sde:source_url"


async def _set_sde_status(status: str, **extra: str | int) -> None:
    r = aioredis.Redis(connection_pool=get_pool())
    try:
        await r.set(f"helm:sde:status", status)
        for k, v in extra.items():
            await r.set(f"helm:sde:{k}", str(v))
    finally:
        await r.aclose()


async def _import_from_zip(zip_path: str) -> dict:
    """
    Parse SDE from a local zip file (eve-online-static-data-latest-jsonl.zip).
    Returns dict with keys: type_count, group_count, category_count.
    """
    upload_dir = Path(settings.sde_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        # 1. Parse _sde.jsonl for metadata (JSONL format: one object per line)
        meta = {}
        if "_sde.jsonl" in names:
            with zf.open("_sde.jsonl") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    meta = json.loads(line)
                    break

        build_number = meta.get("buildNumber", "unknown")
        release_date = meta.get("releaseDate", "")

        await _set_sde_status("running", version=build_number, release_date=release_date)
        logger.info("SDE metadata: buildNumber=%s, releaseDate=%s", build_number, release_date)

        type_count = 0
        group_count = 0
        category_count = 0

        # Import in dependency order: categories → groups → types
        # types.jsonl has no categoryID field; we backfill it from sde_group after import.
        if "categories.jsonl" in names:
            category_count = await _upsert_categories_jsonl(zf, "categories.jsonl")

        if "groups.jsonl" in names:
            group_count = await _upsert_groups_jsonl(zf, "groups.jsonl")

        if "types.jsonl" in names:
            type_count = await _upsert_types_jsonl(zf, "types.jsonl")
            await _backfill_type_category_ids()

        return {
            "type_count": type_count,
            "group_count": group_count,
            "category_count": category_count,
            "build_number": build_number,
            "release_date": release_date,
        }


async def _upsert_types_jsonl(zf: zipfile.ZipFile, filename: str) -> int:
    """Stream-parse types.jsonl and upsert SDEType records. Returns row count."""
    batch: list[dict] = []
    total = 0

    async with AsyncSessionLocal() as db:
        with zf.open(filename) as f:
            # JSONL: one JSON object per line, parse each line individually
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                try:
                    raw_key = record.get("_key")
                    if raw_key is None:
                        continue
                    type_id = int(raw_key)

                    name_dict = record.get("name") or {}
                    desc_dict = record.get("description") or {}

                    batch.append({
                        "type_id": type_id,
                        "name": name_dict if isinstance(name_dict, dict) else {"en": str(name_dict)},
                        "description": desc_dict if isinstance(desc_dict, dict) else {"en": str(desc_dict)},
                        "group_id": record.get("groupID"),
                        "category_id": record.get("categoryID"),
                        "market_group_id": record.get("marketGroupID"),
                        "icon_id": record.get("iconID"),
                        "base_price": record.get("basePrice"),
                        "mass": record.get("mass"),
                        "volume": record.get("volume"),
                        "published": record.get("published", False),
                    })
                except (ValueError, TypeError):
                    continue

                if len(batch) >= BATCH_SIZE:
                    await _upsert_types_batch(db, batch)
                    total += len(batch)
                    batch = []
                    logger.info("SDE types import progress: %d rows", total)

            if batch:
                await _upsert_types_batch(db, batch)
                total += len(batch)

    logger.info("SDE types import complete: %d rows", total)
    return total


async def _upsert_types_batch(db: AsyncSessionLocal, batch: list[dict]) -> None:
    stmt = pg_insert(SDEType).values(batch).on_conflict_do_update(
        index_elements=["type_id"],
        set_={
            "name": pg_insert(SDEType).excluded.name,
            "description": pg_insert(SDEType).excluded.description,
            "group_id": pg_insert(SDEType).excluded.group_id,
            "category_id": pg_insert(SDEType).excluded.category_id,
            "market_group_id": pg_insert(SDEType).excluded.market_group_id,
            "icon_id": pg_insert(SDEType).excluded.icon_id,
            "base_price": pg_insert(SDEType).excluded.base_price,
            "mass": pg_insert(SDEType).excluded.mass,
            "volume": pg_insert(SDEType).excluded.volume,
            "published": pg_insert(SDEType).excluded.published,
            "updated_at": pg_insert(SDEType).excluded.updated_at,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def _upsert_groups_jsonl(zf: zipfile.ZipFile, filename: str) -> int:
    """Stream-parse groups.jsonl and upsert SDEGroup records. Returns row count."""
    batch: list[dict] = []
    total = 0

    async with AsyncSessionLocal() as db:
        with zf.open(filename) as f:
            # JSONL: one JSON object per line
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                try:
                    raw_key = record.get("_key")
                    if raw_key is None:
                        continue
                    group_id = int(raw_key)

                    name_dict = record.get("name") or {}

                    batch.append({
                        "group_id": group_id,
                        "name": name_dict if isinstance(name_dict, dict) else {"en": str(name_dict)},
                        "category_id": record.get("categoryID"),
                        "published": record.get("published", False),
                    })
                except (ValueError, TypeError):
                    continue

                if len(batch) >= BATCH_SIZE:
                    await _upsert_groups_batch(db, batch)
                    total += len(batch)
                    batch = []

            if batch:
                await _upsert_groups_batch(db, batch)
                total += len(batch)

    logger.info("SDE groups import complete: %d rows", total)
    return total


async def _upsert_groups_batch(db: AsyncSessionLocal, batch: list[dict]) -> None:
    stmt = pg_insert(SDEGroup).values(batch).on_conflict_do_update(
        index_elements=["group_id"],
        set_={
            "name": pg_insert(SDEGroup).excluded.name,
            "category_id": pg_insert(SDEGroup).excluded.category_id,
            "published": pg_insert(SDEGroup).excluded.published,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def _upsert_categories_jsonl(zf: zipfile.ZipFile, filename: str) -> int:
    """Stream-parse categories.jsonl and upsert SDECategory records. Returns row count."""
    batch: list[dict] = []
    total = 0

    async with AsyncSessionLocal() as db:
        with zf.open(filename) as f:
            # JSONL: one JSON object per line
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                try:
                    raw_key = record.get("_key")
                    if raw_key is None:
                        continue
                    category_id = int(raw_key)

                    name_dict = record.get("name") or {}

                    batch.append({
                        "category_id": category_id,
                        "name": name_dict if isinstance(name_dict, dict) else {"en": str(name_dict)},
                        "published": record.get("published", False),
                    })
                except (ValueError, TypeError):
                    continue

                if len(batch) >= BATCH_SIZE:
                    await _upsert_categories_batch(db, batch)
                    total += len(batch)
                    batch = []

            if batch:
                await _upsert_categories_batch(db, batch)
                total += len(batch)

    logger.info("SDE categories import complete: %d rows", total)
    return total


async def _backfill_type_category_ids() -> None:
    """Fill sde_type.category_id from sde_group, since types.jsonl has no categoryID field."""
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "UPDATE sde_type t SET category_id = g.category_id "
            "FROM sde_group g WHERE t.group_id = g.group_id"
        ))
        await db.commit()
    logger.info("SDE type category_id backfill complete")


async def _upsert_categories_batch(db: AsyncSessionLocal, batch: list[dict]) -> None:
    stmt = pg_insert(SDECategory).values(batch).on_conflict_do_update(
        index_elements=["category_id"],
        set_={
            "name": pg_insert(SDECategory).excluded.name,
            "published": pg_insert(SDECategory).excluded.published,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def _download_and_import(url: str) -> dict:
    """Download the official JSONL zip and import it. Returns counts dict."""
    await _set_sde_status("running", source_url=url)
    logger.info("SDE download started: %s", url)

    async with httpx.AsyncClient(timeout=settings.sde_import_timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    logger.info("SDE download complete, size=%d bytes, importing...", len(resp.content))

    # Save to a temp file for zipfile access
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        result = await _import_from_zip(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return result


@celery_app.task(
    name="app.tasks.sde.import_sde",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def import_sde(
    url: str | None = None,
    uploaded_file_path: str | None = None,
) -> dict:
    """
    Celery task: download and import official EVE SDE (JSONL format, multi-language).

    Args:
        url: URL to the official eve-online-static-data-latest-jsonl.zip.
             Defaults to settings.sde_default_jsonl_url.
        uploaded_file_path: Path to a locally uploaded .zip file (supersedes url).

    Returns:
        {"status": "success", "type_count": int, "group_count": int, "category_count": int}
    """
    async def _inner():
        source = uploaded_file_path or url or settings.sde_default_jsonl_url

        try:
            if uploaded_file_path:
                logger.info("SDE import from uploaded file: %s", uploaded_file_path)
                result = await _import_from_zip(uploaded_file_path)
            else:
                result = await _download_and_import(source)

            await _set_sde_status(
                "success",
                row_count=result["type_count"],
                version=result.get("build_number", ""),
                release_date=result.get("release_date", ""),
                last_import_at=int(datetime.now(UTC).timestamp()),
                last_error="",
                source_url=source,
            )
            logger.info("SDE import complete: %s", result)
            return {"status": "success", **result}
        except Exception as e:
            await _set_sde_status("failed", last_error=str(e))
            logger.exception("SDE import failed: %s", e)
            raise

    return run_async(_inner())
