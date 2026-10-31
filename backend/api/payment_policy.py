"""Runtime-owned payment switch. Clients and database settings cannot enable it."""
import os
from fastapi import HTTPException

MESSAGE = 'Payments temporarily unavailable during public beta. Free events and virtual auditoriums remain available.'

def actions_enabled():
    flag = os.getenv('MINDAAM_PAYMENT_ACTIONS_ENABLED')
    # Fail closed for public production; local/staging keep existing behavior unless gated.
    if flag is not None:
        return flag == 'true'
    return os.getenv('APP_ENV', 'local') not in ('production',)

def require_payment_actions():
    if not actions_enabled():
        raise HTTPException(409, MESSAGE)

ARENA_MESSAGE = 'Mindaam Grand Arena — Coming Soon'
def grand_arena_enabled():
    return os.getenv('MINDAAM_GRAND_ARENA_ENABLED') == 'true'
def require_grand_arena():
    if not grand_arena_enabled():
        raise HTTPException(409, ARENA_MESSAGE)
