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
        raise HTTPException(503, MESSAGE)
