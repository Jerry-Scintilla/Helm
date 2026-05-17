"""EVE Online notification text parser and HTML renderer."""
import html as _html
import re as _re

_UNICODE_ESC = _re.compile(r'\\u([0-9a-fA-F]{4})')
_KV = _re.compile(r'^(\w+)\s*:\s*(.*)')
_INT_ONLY = _re.compile(r'^-?\d+$')

# Keys whose values are EVE item type IDs → resolve via SDE
_TYPE_ID_KEYS = frozenset({
    'typeID', 'structureTypeID', 'shipTypeID', 'itemTypeID',
    'moonTypeID', 'planetTypeID', 'componentTypeID', 'destroyedShipTypeID',
})

# Keys whose integer values are NOT entity IDs (timestamps, amounts, flags)
_SKIP_ID_KEYS = frozenset({
    'timeStarted', 'timeDeclared', 'timeEnded', 'startTime', 'endTime',
    'delayHours', 'cost', 'amount', 'quantity', 'hostileState',
    'newStanding', 'oldStanding', 'level', 'rankNew', 'rankOld',
    'standing', 'warID', 'transitSystemCount', 'jumps',
})


def decode_unicode_escapes(text: str) -> str:
    """Decode literal \\uXXXX escape sequences in EVE notification YAML text."""
    return _UNICODE_ESC.sub(lambda m: chr(int(m.group(1), 16)), text)


def extract_notification_ids(text: str) -> tuple[list[int], list[int]]:
    """
    Scan notification YAML text for integer values that need name resolution.
    Returns (entity_ids, type_ids):
      entity_ids — suitable for ESI /universe/names/
      type_ids   — suitable for SDE lookup
    """
    entity_ids: list[int] = []
    type_ids: list[int] = []

    for line in text.splitlines():
        m = _KV.match(line.strip())
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if not _INT_ONLY.match(val):
            continue
        n = int(val)
        if n <= 0 or key in _SKIP_ID_KEYS:
            continue

        if key in _TYPE_ID_KEYS:
            if 1 <= n <= 100_000:
                type_ids.append(n)
        elif (key.endswith('ID') or key.endswith('Id')) and n >= 1_000_000:
            entity_ids.append(n)

    return entity_ids, type_ids


def render_notification_text(
    text: str,
    entity_names: dict[int, dict],      # {id: {"name": str, "category": str}}
    type_names: dict[int, str | None],  # {type_id: name}
) -> str:
    """
    Parse EVE notification YAML text and return formatted HTML.

    Handles:
    - \\uXXXX Unicode escape sequences
    - Key-value pairs with ID resolution
    - List items (lines starting with -)
    - Embedded EVE HTML tags (preserved as-is)
    - Quoted string values
    """
    text = decode_unicode_escapes(text)
    rows: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        kv = _KV.match(stripped)
        if kv:
            key, raw_val = kv.group(1), kv.group(2).strip()
            if len(raw_val) >= 2 and raw_val[0] == '"' and raw_val[-1] == '"':
                raw_val = raw_val[1:-1]
            display = _resolve_value(raw_val, key, entity_names, type_names)
            rows.append(
                f'<div class="nf-row">'
                f'<span class="nf-key">{_html.escape(key)}</span>'
                f'<span class="nf-val">{display}</span>'
                f'</div>'
            )
        elif stripped.startswith('-'):
            val = stripped[1:].strip()
            display = _resolve_value(val, None, entity_names, type_names)
            rows.append(f'<div class="nf-item"><span class="nf-val">{display}</span></div>')
        else:
            rows.append(f'<div class="nf-cont">{_html.escape(stripped)}</div>')

    return '<div class="notif-body">' + ''.join(rows) + '</div>'


def _resolve_value(
    raw: str,
    key: str | None,
    entity_names: dict[int, dict],
    type_names: dict[int, str | None],
) -> str:
    if _INT_ONLY.match(raw):
        n = int(raw)
        if n > 0:
            if key and key in _TYPE_ID_KEYS:
                name = type_names.get(n)
                if name:
                    return f'<span class="nf-name">{_html.escape(name)}</span>'
            info = entity_names.get(n)
            if info:
                name = info.get('name', '')
                return (
                    f'<span class="nf-name">{_html.escape(name)}</span>'
                    f' <span class="nf-id">#{n}</span>'
                )

    # Preserve EVE-embedded HTML tags (e.g. <b>station name</b>)
    if '<' in raw:
        return raw

    return _html.escape(raw)
