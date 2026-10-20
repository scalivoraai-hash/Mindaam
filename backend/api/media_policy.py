"""Bounded launch controls stored in the existing audited Config architecture."""
import json
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from .core import Strict
from .db import get_db
from .models import Config, Audit
from .economy import config
from .operations import super_admin

DEFAULTS = json.loads((Path(__file__).resolve().parents[2]/'shared/media-policy.json').read_text())
class Policy(Strict):
    startup_cost_mode: Literal[True] = True
    default_video: Literal[False] = False
    avatar_video_max: int = Field(default=360, ge=180, le=360)
    fullscreen_video_max: int = Field(default=720, ge=360, le=720)
    allow_1080p: Literal[False] = False
    adaptive_stream: Literal[True] = True
    dynacast: Literal[True] = True
    auto_subscribe: Literal[False] = False
    max_visible_video_subscriptions: int = Field(default=4, ge=1, le=4)
    auditorium_default_camera: Literal[False] = False
    auditorium_default_mic: Literal[False] = False
    auditorium_max_stage_video: int = Field(default=4, ge=1, le=4)
    auditorium_max_screen_share: Literal[1] = 1
    free_event_max_audience: int = Field(default=50, ge=2, le=50)
    standard_event_max_audience: int = Field(default=100, ge=2, le=100)
    large_event_max_audience: int = Field(default=250, ge=2, le=250)
    event_capacity_limit: int = Field(default=100, ge=2, le=250)
    large_event_load_test_evidence: str = Field(default='', max_length=1000)
    @model_validator(mode='after')
    def measured_capacity(self):
        if not self.free_event_max_audience <= self.standard_event_max_audience <= self.large_event_max_audience:
            raise ValueError('Event capacity tiers must be ordered')
        if self.event_capacity_limit > self.standard_event_max_audience and (not self.large_event_load_test_evidence.strip() or self.event_capacity_limit > self.large_event_max_audience):
            raise ValueError('Large events require a recorded successful load-test reference')
        return self

def settings(db): return Policy(**{**DEFAULTS, **config(db, 'media_policy', {})}).model_dump()
router = APIRouter(prefix='/api/super-admin/media-policy')
@router.get('')
def read(u=Depends(super_admin), db=Depends(get_db)): return settings(db)
@router.put('')
def write(data:Policy, u=Depends(super_admin), db=Depends(get_db)):
    value=data.model_dump(); row=db.get(Config,'media_policy')
    if row: row.value=value
    else: db.add(Config(key='media_policy',value=value))
    db.add(Audit(actor_id=u.id,action='media.policy_updated',target='media_policy',details=value))
    return value
