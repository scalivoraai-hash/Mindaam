"""Presentation-only rollout. Production is deliberately ineligible."""
import os
import json
from pathlib import Path
from fastapi import APIRouter
from .locations import CITIES

router = APIRouter(prefix='/api')
STYLES = json.loads((Path(__file__).resolve().parents[2] / 'shared/city-visual-styles.json').read_text())
APPROVED = {city['id'] for city in CITIES if not city.get('requires_activation')}


def selected_profile(city, environment, configured):
    if environment == 'staging' and configured == 'cinematic-world-v2' and city in APPROVED and city in STYLES:
        return 'cinematic-world-v2'
    return ('cinematic-world-v1' if environment == 'staging'
            and city == 'milton-keynes' and configured == 'cinematic-world-v1'
            else 'standard')


@router.get('/visual-profile/{city}')
def visual_profile(city: str):
    return {'city': city, 'profile': selected_profile(
        city, os.getenv('APP_ENV', ''), os.getenv('MINDAAM_VISUAL_PROFILE', ''))}
