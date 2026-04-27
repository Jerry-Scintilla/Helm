from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_user, require_permission
from app.models.character import Character
from app.models.esi_data import CharacterAsset, CharacterMail, CharacterSkill, CharacterWallet
from app.models.user import User

router = APIRouter(prefix="/api/v1/characters", tags=["characters"])


async def _get_character_for_user(
    character_id: int, user: User, db: AsyncSession
) -> Character:
    result = await db.execute(
        select(Character).where(
            Character.character_id == character_id,
            Character.user_id == user.id,
        )
    )
    char = result.scalar_one_or_none()
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return char


@router.get("/")
async def list_characters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    result = await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_active == True)
    )
    characters = result.scalars().all()
    return [
        {
            "character_id": c.character_id,
            "character_name": c.character_name,
            "corporation_id": c.corporation_id,
            "alliance_id": c.alliance_id,
        }
        for c in characters
    ]


@router.get("/{character_id}/")
async def get_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    return {
        "character_id": char.character_id,
        "character_name": char.character_name,
        "corporation_id": char.corporation_id,
        "alliance_id": char.alliance_id,
        "scopes": char.scopes,
        "updated_at": char.updated_at,
    }


@router.get("/{character_id}/wallet")
async def get_wallet(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterWallet).where(CharacterWallet.character_id == char.id)
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        return {"balance": None, "updated_at": None}
    return {"balance": wallet.balance, "updated_at": wallet.updated_at}


@router.get("/{character_id}/skills")
async def get_skills(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterSkill).where(CharacterSkill.character_id == char.id)
    )
    skills = result.scalars().all()
    return {
        "total_sp": sum(s.skillpoints_in_skill for s in skills),
        "skills": [
            {
                "skill_id": s.skill_id,
                "trained_skill_level": s.trained_skill_level,
                "skillpoints_in_skill": s.skillpoints_in_skill,
            }
            for s in skills
        ],
        "updated_at": skills[0].updated_at if skills else None,
    }


@router.get("/{character_id}/assets")
async def get_assets(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterAsset).where(CharacterAsset.character_id == char.id)
    )
    assets = result.scalars().all()
    return [
        {
            "item_id": a.item_id,
            "type_id": a.type_id,
            "location_id": a.location_id,
            "location_type": a.location_type,
            "quantity": a.quantity,
        }
        for a in assets
    ]


@router.get("/{character_id}/mail")
async def get_mail(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("character.view")),
):
    char = await _get_character_for_user(character_id, current_user, db)
    result = await db.execute(
        select(CharacterMail)
        .where(CharacterMail.character_id == char.id)
        .order_by(CharacterMail.timestamp.desc())
        .limit(50)
    )
    mails = result.scalars().all()
    return [
        {
            "mail_id": m.mail_id,
            "subject": m.subject,
            "from_id": m.from_id,
            "timestamp": m.timestamp,
            "is_read": m.is_read,
        }
        for m in mails
    ]
