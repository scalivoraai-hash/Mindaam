"""Profile metadata only: no credentials, remote fetching, or inferred verification."""
import re
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator

PLATFORMS = {
    'instagram': 'www.instagram.com', 'facebook': 'www.facebook.com',
    'linkedin': 'www.linkedin.com', 'x': 'x.com',
    'youtube': 'www.youtube.com', 'tiktok': 'www.tiktok.com',
}
THEMES = ('Midnight Neon', 'Aurora', 'Ocean', 'Sunset', 'Electric Violet', 'Minimal Light')

class SocialLink(BaseModel):
    model_config = ConfigDict(extra='forbid')
    url: str = Field(max_length=500)
    visible: bool = True


def normalize_link(platform, value):
    value = value.strip()
    if not value:
        return ''
    if platform not in {*PLATFORMS, 'website'}:
        raise ValueError('Unsupported social platform')
    if re.search(r'[\s\\\x00-\x1f\x7f]', value):
        raise ValueError('Invalid profile URL')
    if platform in PLATFORMS and re.fullmatch(r'@?[A-Za-z0-9_.-]{1,100}', value):
        handle = value.lstrip('@')
        prefix = 'in/' if platform == 'linkedin' else '@' if platform in {'youtube', 'tiktok'} else ''
        value = 'https://' + PLATFORMS[platform] + '/' + prefix + handle
    elif '://' not in value and ':' not in value:
        value = 'https://' + value
    try:
        parts = urlsplit(value)
        host = parts.hostname or ''
        port = parts.port
    except ValueError as e:
        raise ValueError('Invalid profile URL') from e
    if parts.scheme != 'https' or parts.username or parts.password or port not in {None, 443}:
        raise ValueError('Only public HTTPS links are accepted')
    if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,63}', host):
        raise ValueError('A public domain is required')
    if platform in PLATFORMS:
        allowed = {PLATFORMS[platform], PLATFORMS[platform].removeprefix('www.')}
        if platform == 'x': allowed |= {'twitter.com', 'www.twitter.com', 'www.x.com'}
        if host.lower() not in allowed or not parts.path.strip('/'):
            raise ValueError('Use a profile URL on the selected platform')
        host = PLATFORMS[platform]
        if parts.path.lower().startswith(('/intent/', '/share', '/login', '/redirect')):
            raise ValueError('Use a profile URL, not a sharing or redirect link')
    return urlunsplit(('https', host.lower(), parts.path, '', ''))

class ProfileFields(BaseModel):
    model_config = ConfigDict(extra='forbid')
    identity: Literal['Male','Female','Transgender','Non-binary','Prefer not to say','Custom / Other'] = 'Prefer not to say'
    custom_identity: str = Field(default='', max_length=60)
    show_identity: bool = False
    country: str = Field(default='', max_length=80)
    town: str = Field(default='', max_length=80)
    area: str = Field(default='', max_length=80)
    show_location: bool = False
    display_name: str = Field(default='', max_length=80)
    bio: str = Field(default='', max_length=300)
    public_interests: list[str] = Field(default_factory=list, max_length=12)
    languages: list[str] = Field(default_factory=list, max_length=8)
    category: Literal['', 'Personal', 'Creator', 'Business'] = ''
    theme: Literal['Midnight Neon', 'Aurora', 'Ocean', 'Sunset', 'Electric Violet', 'Minimal Light'] = 'Midnight Neon'
    links: dict[str, SocialLink] = Field(default_factory=dict, max_length=7)

    @field_validator('public_interests', 'languages')
    @classmethod
    def small_labels(cls, values):
        if any(not v.strip() or len(v.strip()) > 40 for v in values):
            raise ValueError('Use labels between 1 and 40 characters')
        return list(dict.fromkeys(v.strip() for v in values))

    @field_validator('links')
    @classmethod
    def safe_links(cls, values):
        return {key: SocialLink(url=normalize_link(key, link.url), visible=link.visible)
                for key, link in values.items()}

class ProfileUpdate(ProfileFields):
    username: str | None = Field(default=None, min_length=3, max_length=40, pattern=r'^[a-zA-Z0-9_ -]+$')
