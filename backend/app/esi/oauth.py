import hashlib
import logging
import secrets
from urllib.parse import urlencode

import httpx
from jose import jwt as jose_jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Authoritative whitelist sourced from the ESI OpenAPI spec (tranquility, 2025-12-16).
# https://esi.evetech.net/latest/swagger.json → components.securitySchemes.OAuth2.flows.authorizationCode.scopes
_KNOWN_ESI_SCOPES: frozenset[str] = frozenset([
    "esi-access.read_lists.v1",
    "esi-activities.read_character.v1",
    "esi-alliances.read_contacts.v1",
    "esi-assets.read_assets.v1",
    "esi-assets.read_corporation_assets.v1",
    "esi-calendar.read_calendar_events.v1",
    "esi-calendar.respond_calendar_events.v1",
    "esi-characters.read_agents_research.v1",
    "esi-characters.read_blueprints.v1",
    "esi-characters.read_contacts.v1",
    "esi-characters.read_corporation_roles.v1",
    "esi-characters.read_fatigue.v1",
    "esi-characters.read_freelance_jobs.v1",
    "esi-characters.read_fw_stats.v1",
    "esi-characters.read_loyalty.v1",
    "esi-characters.read_medals.v1",
    "esi-characters.read_notifications.v1",
    "esi-characters.read_standings.v1",
    "esi-characters.read_titles.v1",
    "esi-characters.write_contacts.v1",
    "esi-clones.read_clones.v1",
    "esi-clones.read_implants.v1",
    "esi-contracts.read_character_contracts.v1",
    "esi-contracts.read_corporation_contracts.v1",
    "esi-corporations.read_blueprints.v1",
    "esi-corporations.read_contacts.v1",
    "esi-corporations.read_container_logs.v1",
    "esi-corporations.read_corporation_membership.v1",
    "esi-corporations.read_divisions.v1",
    "esi-corporations.read_facilities.v1",
    "esi-corporations.read_freelance_jobs.v1",
    "esi-corporations.read_fw_stats.v1",
    "esi-corporations.read_medals.v1",
    "esi-corporations.read_projects.v1",
    "esi-corporations.read_standings.v1",
    "esi-corporations.read_starbases.v1",
    "esi-corporations.read_structures.v1",
    "esi-corporations.read_titles.v1",
    "esi-corporations.track_members.v1",
    "esi-fittings.read_fittings.v1",
    "esi-fittings.write_fittings.v1",
    "esi-fleets.read_fleet.v1",
    "esi-fleets.write_fleet.v1",
    "esi-industry.read_character_jobs.v1",
    "esi-industry.read_character_mining.v1",
    "esi-industry.read_corporation_jobs.v1",
    "esi-industry.read_corporation_mining.v1",
    "esi-killmails.read_corporation_killmails.v1",
    "esi-killmails.read_killmails.v1",
    "esi-location.read_location.v1",
    "esi-location.read_online.v1",
    "esi-location.read_ship_type.v1",
    "esi-mail.organize_mail.v1",
    "esi-mail.read_mail.v1",
    "esi-mail.send_mail.v1",
    "esi-markets.read_character_orders.v1",
    "esi-markets.read_corporation_orders.v1",
    "esi-markets.structure_markets.v1",
    "esi-planets.manage_planets.v1",
    "esi-planets.read_customs_offices.v1",
    "esi-search.search_structures.v1",
    "esi-skills.read_skillqueue.v1",
    "esi-skills.read_skills.v1",
    "esi-structures.read_character.v1",
    "esi-structures.read_corporation.v1",
    "esi-ui.open_window.v1",
    "esi-ui.write_waypoint.v1",
    "esi-universe.read_structures.v1",
    "esi-wallet.read_character_wallet.v1",
    "esi-wallet.read_corporation_wallets.v1",
])

EVE_SSO_AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
EVE_SSO_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
EVE_SSO_JWKS_URL = "https://login.eveonline.com/oauth/jwks"

# Core ESI scopes requested by the system
CORE_SCOPES = [
    "esi-characters.read_titles.v1",
    "esi-location.read_location.v1",
    "esi-location.read_online.v1",
    "esi-location.read_ship_type.v1",
    "esi-wallet.read_character_wallet.v1",
    "esi-skills.read_skills.v1",
    "esi-skills.read_skillqueue.v1",
    "esi-assets.read_assets.v1",
    "esi-mail.read_mail.v1",
    "esi-characters.read_notifications.v1",
    "esi-universe.read_structures.v1",
    "esi-contracts.read_character_contracts.v1",
    "esi-contracts.read_corporation_contracts.v1",
]


def filter_plugin_scopes(scopes: list[str]) -> list[str]:
    """Validate and deduplicate plugin-supplied ESI scopes.

    Only scopes present in the ESI whitelist (_KNOWN_ESI_SCOPES) are accepted.
    Scopes already covered by CORE_SCOPES and duplicate entries are silently
    dropped; unrecognised values are dropped with a warning.
    """
    seen: set[str] = set(CORE_SCOPES)
    valid: list[str] = []
    for scope in scopes:
        if not isinstance(scope, str) or scope not in _KNOWN_ESI_SCOPES:
            logger.warning("Plugin supplied unknown/invalid ESI scope (dropped): %r", scope)
            continue
        if scope in seen:
            continue
        seen.add(scope)
        valid.append(scope)
    return valid


def _pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE."""
    verifier = secrets.token_urlsafe(64)
    challenge = (
        hashlib.sha256(verifier.encode()).digest().hex()
    )
    # EVE SSO uses plain challenge or S256; use S256 (base64url without padding)
    import base64
    challenge_b64 = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge_b64


def get_login_url(state: str, extra_scopes: list[str] | None = None) -> tuple[str, str]:
    """Return (login_url, code_verifier). Store code_verifier in session."""
    validated_extras = filter_plugin_scopes(extra_scopes or [])
    scopes = CORE_SCOPES + validated_extras
    verifier, challenge = _pkce_pair()
    params = {
        "response_type": "code",
        "redirect_uri": settings.eve_callback_url,
        "client_id": settings.eve_client_id,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{EVE_SSO_AUTH_URL}?{urlencode(params)}", verifier


async def exchange_code(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for tokens. Returns raw token response."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            EVE_SSO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.eve_client_id,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Use refresh_token to get a new access_token. Returns raw token response."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            EVE_SSO_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.eve_client_id,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def verify_token(access_token: str) -> dict:
    """Verify EVE JWT and return payload with character_id, name, scopes."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(EVE_SSO_JWKS_URL)
        resp.raise_for_status()
        jwks = resp.json()

    # Decode without full JWKS verification for now; EVE tokens are HS256 or RS256
    # Use jose to decode and verify
    header = jose_jwt.get_unverified_header(access_token)
    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == header.get("kid"):
            key = k
            break

    payload = jose_jwt.decode(
        access_token,
        key or jwks["keys"][0],
        algorithms=[header.get("alg", "RS256")],
        audience="EVE Online",
        options={"verify_aud": False},
    )

    # EVE token "sub" format: "CHARACTER:EVE:<character_id>"
    sub = payload.get("sub", "")
    character_id = int(sub.split(":")[-1]) if ":" in sub else int(sub)

    return {
        "character_id": character_id,
        "character_name": payload.get("name", ""),
        "scopes": payload.get("scp", []),
        "owner_hash": payload.get("owner", ""),
    }
