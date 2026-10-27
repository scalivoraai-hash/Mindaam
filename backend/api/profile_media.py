"""Bounded profile photographs in existing SQL storage, gated on every read."""
import base64
import io
import time
from typing import Literal
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, ForeignKey, LargeBinary, Float, select, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, get_db
from .auth import current_user
from .models import Audit, User
from .public_profiles import visible

class ProfilePhoto(Base):
    __tablename__ = 'profile_photos'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[float] = mapped_column(Float)

class PhotoInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    content: str = Field(max_length=245760)

router=APIRouter(prefix='/api')

@router.put('/me/photos/{kind}')
def upload_photo(kind: Literal['picture','cover'], body: PhotoInput, u=Depends(current_user), db=Depends(get_db)):
    u=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
    if u.suspended:raise HTTPException(403,'Account unavailable')
    if db.scalar(select(func.count()).select_from(Audit).where(Audit.actor_id==u.id,Audit.action=='profile.photo',Audit.created_at>time.time()-60)) >= 6:
        raise HTTPException(429,'Wait before uploading another photograph')
    try:
        raw=base64.b64decode(body.content,validate=True)
        if len(raw)>184320: raise ValueError('Image too large')
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in {'JPEG','PNG','WEBP'} or source.width*source.height>4_000_000 or min(source.size)<32 or max(source.size)>2048 or getattr(source,'n_frames',1)!=1:
                raise ValueError('Invalid photograph')
            source.load()
            size=(384,384) if kind=='picture' else (1200,400)
            photo=ImageOps.fit(ImageOps.exif_transpose(source).convert('RGB'),size)
            output=io.BytesIO();photo.save(output,format='JPEG',quality=82,optimize=True)
            encoded=output.getvalue()
            if len(encoded)>184320:raise ValueError('Image too detailed')
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError):
        raise HTTPException(422,'Use a resized JPEG, PNG or WebP photograph under 180 KiB and 2048 pixels')
    row=db.get(ProfilePhoto,(u.id,kind))
    if row is None:row=ProfilePhoto(user_id=u.id,kind=kind);db.add(row)
    row.data=encoded;row.updated_at=time.time()
    db.add(Audit(actor_id=u.id,action='profile.photo',target=kind))
    u.profile={**(u.profile or {}),kind+'_version':str(int(row.updated_at*1000))}
    return {'url':f'/api/profiles/{u.id}/photos/{kind}', 'version':u.profile[kind+'_version']}

@router.delete('/me/photos/{kind}')
def remove_photo(kind: Literal['picture','cover'],u=Depends(current_user),db=Depends(get_db)):
    u=db.scalar(select(User).where(User.id==u.id).with_for_update().execution_options(populate_existing=True))
    if u.suspended:raise HTTPException(403,'Account unavailable')
    row=db.get(ProfilePhoto,(u.id,kind))
    if row:db.delete(row)
    u.profile={k:v for k,v in (u.profile or {}).items() if k!=kind+'_version'}
    return {'ok':True}

@router.get('/profiles/{user_id}/photos/{kind}')
def photo(user_id:str,kind:Literal['picture','cover'],u=Depends(current_user),db=Depends(get_db)):
    if not visible(db,u,db.get(User,user_id)):raise HTTPException(404,'Photograph unavailable')
    row=db.get(ProfilePhoto,(user_id,kind))
    if not row:raise HTTPException(404,'Photograph unavailable')
    return Response(row.data,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
