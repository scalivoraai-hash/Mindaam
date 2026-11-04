"""Presentation-only rollout. Production is deliberately ineligible."""
import os
from fastapi import APIRouter

router = APIRouter(prefix='/api')


def selected_profile(city, environment, configured):
    return ('cinematic-world-v1' if environment == 'staging'
            and city == 'milton-keynes' and configured == 'cinematic-world-v1'
            else 'standard')


@router.get('/visual-profile/{city}')
def visual_profile(city: str):
    return {'city': city, 'profile': selected_profile(
        city, os.getenv('APP_ENV', ''), os.getenv('MINDAAM_VISUAL_PROFILE', ''))}
