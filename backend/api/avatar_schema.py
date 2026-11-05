"""Allowlisted cosmetic data only; legacy saves are preserved without a bulk migration."""
import json
import re
from pathlib import Path

CATALOG = json.loads((Path(__file__).resolve().parents[2] / 'shared/avatar-catalog.json').read_text())
COLORS = {'color', 'skin', 'hair', 'pants', 'accent'}

def validate_avatar(value):
    if not isinstance(value, dict) or len(value) > 24 or len(json.dumps(value)) > 2000:
        raise ValueError('Appearance is too large')
    for key, item in value.items():
        if not isinstance(item, str):
            raise ValueError('Appearance values must be text')
        if key in COLORS:
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', item):
                raise ValueError('Use a six-digit appearance colour')
        elif key == 'version':
            if item != '2':
                raise ValueError('Unsupported appearance version')
        elif key in CATALOG and key != 'presets':
            if item not in CATALOG[key] and not (key == 'style' and item == 'cap'):
                raise ValueError('Unsupported appearance choice: ' + key)
        else:
            raise ValueError('Unknown appearance field: ' + key)
    return value.copy()
