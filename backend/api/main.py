import hashlib
import asyncio
import anyio
import os
import time
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
import logging
from collections import defaultdict, deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select, delete, or_
from sqlalchemy.exc import IntegrityError
from .db import engine, SessionLocal, APP_ENV
from . import (
    core,
    world,
    social,
    media,
    commerce,
    identity,
    discovery,
    gameplay,
    subscriptions,
    events,
    growth,transit,civic,operations,expansion,mobility,business_spatial,gifts,event_presentation,event_tickets,event_engagement,event_creators,grand_arena,venue_rentals,credit_catalog,collectible_rotation,
)
from .auth import user_for_token
from .models import Presence, Notification, MediaSession, Session, User
from .core import serialize
from . import conversations
from pydantic import Field, ValidationError
from typing import Literal


def maintenance():
    ended = []
    with SessionLocal.begin() as db:
        # A hidden/tab-suspended media call may interrupt its heartbeat. Hide stale
        # presence via existing 45s visibility checks, but keep virtual coordinates
        # while authentication is valid so reconnect cannot respawn the player.
        active_users=select(Session.user_id).where(Session.expires_at>time.time())
        db.execute(delete(Presence).where(Presence.updated_at < time.time() - 60,~Presence.user_id.in_(active_users)))
        db.execute(delete(Session).where(Session.expires_at < time.time()))
        events.maintenance(db)
        transit.maintenance(db)
        mobility.maintenance(db)
        operations.sample(db)
        for s in db.scalars(select(MediaSession).where(MediaSession.state == "accepted")):
            conversations.enforce(db,s)
            if not s.event_id and (not s.accepted_at or s.accepted_at<time.time()-(86400 if s.kind=='text' else 600)):
                s.state='ended';s.ended_at=time.time();s.end_reason='expired';ended.append(s.id)
        # Retry provider cleanup after timeouts, and revoke rooms recreated by a
        # previously issued short-lived join token. Never touch unrelated rooms.
        ended.extend(db.scalars(select(MediaSession.id).where(
            MediaSession.state == "ended",
            MediaSession.kind.in_(["voice", "liveface"]),
            MediaSession.ended_at > time.time() - 300,
        )))
    return list(set(ended))

async def cleanup():
    while True:
        await asyncio.sleep(2)
        try:
            ended = await run_in_threadpool(maintenance)
            def participant_jobs():
                with SessionLocal.begin() as db:return conversations.cleanup_participants(db)
            for session_id,user_id in await run_in_threadpool(participant_jobs):
                try:await asyncio.wait_for(media.remove_participant(session_id,user_id),timeout=5)
                except Exception:logging.getLogger('pulseworld').warning('Participant cleanup will retry')
            def permission_jobs():
                with SessionLocal.begin() as db:return events.permission_jobs(db)
            for event_id,sid,uid,role,kind,can_share,revision in await run_in_threadpool(permission_jobs):
                try:
                    def reconcile():
                        with SessionLocal.begin() as db:event_presentation.reconcile_permission(db,event_id,uid)
                    await run_in_threadpool(reconcile)
                except Exception:logging.getLogger('pulseworld').warning('Stage permission cleanup will retry')
            for id in ended:
                try:
                    await asyncio.wait_for(media.terminate_room(id),timeout=5)
                except Exception:
                    logging.getLogger("pulseworld").exception("Room cleanup will retry")
        except Exception:
            logging.getLogger("pulseworld").exception("Maintenance failed")


async def deliver_mail():
    from .identity import drain_outbox
    while True:
        if os.getenv("SMTP_HOST") and os.getenv("MAIL_ENCRYPTION_KEY"):
            try:
                await run_in_threadpool(drain_outbox, 5)
            except Exception:
                logging.getLogger("pulseworld").error("Mail delivery worker failed; retrying")
        await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app):
    if APP_ENV!='test':
        def initialise():
            with SessionLocal.begin() as db:
                # Map indexing is CPU-bound. The request pool's 10-second idle limit
                # must not terminate this bounded first-start inventory transaction.
                # SET LOCAL resets automatically at commit; runtime requests stay strict.
                if db.bind.dialect.name=='postgresql':
                    db.connection().exec_driver_sql("SET LOCAL idle_in_transaction_session_timeout = '120s'")
                    db.connection().exec_driver_sql("SET LOCAL lock_timeout = '120s'")
                    db.connection().exec_driver_sql("SELECT pg_advisory_xact_lock(2052011101)")
                expansion.seed_catalog(db)
                from .world_content import seed_active
                seed_active(db)
                mobility.seed_assets(db);mobility.seed_water(db);transit.seed_network(db);civic.seed_buildings(db);business_spatial.seed_businesses(db);operations.seed_inventory(db);operations.bootstrap_owner(db)
        await run_in_threadpool(initialise)
    tasks = [asyncio.create_task(cleanup()), asyncio.create_task(deliver_mail())]
    try:
        yield
    finally:
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Mindaam API", version="0.1.0-alpha", lifespan=lifespan)
for route in [
    core.router,
    world.router,
    social.router,
    media.router,
    commerce.router,
    identity.router,
    discovery.router,
    gameplay.router,
    subscriptions.router,
    events.router,
    growth.router,transit.router,civic.router,operations.router,expansion.router,mobility.router,business_spatial.router,gifts.router,event_presentation.router,event_tickets.router,event_engagement.router,event_creators.router,grand_arena.router,venue_rentals.router,credit_catalog.router,collectible_rotation.router,
]:
    app.include_router(route)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("PUBLIC_ORIGIN", "http://localhost:3000")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
local_buckets = defaultdict(deque)
redis_client = None
if os.getenv("REDIS_URL"):
    import redis

    redis_client = redis.Redis.from_url(
        os.environ["REDIS_URL"], socket_connect_timeout=1, socket_timeout=1
    )
if APP_ENV in {"staging", "production"} and not redis_client:
    raise RuntimeError("Redis required outside local/test")

from . import realtime_cache
realtime_cache.configure(redis_client)

@app.middleware("http")
async def security(request: Request, call_next):
    try:
        declared_size = int(request.headers.get("content-length", "0") or 0)
    except ValueError:
        return JSONResponse({"detail": "Invalid content length"}, 400)
    if declared_size < 0:
        return JSONResponse({"detail": "Invalid content length"}, 400)
    body_limit=262144
    if request.url.path=='/api/super-admin/creatives':
        from .auth import request_token,check_browser_origin
        def allowed_upload():
            with SessionLocal() as db:
                user=user_for_token(db,request_token(request,request.headers.get('authorization','')))
                return user.role=='super_admin' and not user.must_change_password
        try:
            if not await run_in_threadpool(allowed_upload):return JSONResponse({'detail':'Super Admin access required'},403)
            if not request.headers.get('authorization','').startswith('Bearer '):check_browser_origin(request)
        except HTTPException as error:return JSONResponse({'detail':error.detail},error.status_code)
        body_limit=7000000
    if declared_size > body_limit:
        return JSONResponse({"detail": "Request too large"}, 413)
    if request.method in {"POST", "PUT", "PATCH"}:
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > body_limit:
                return JSONResponse({"detail": "Request too large"}, 413)
            body.extend(chunk)
        request._body = bytes(body)
    if request.url.path not in {"/health", "/ready", "/api/payments/webhook"}:
        ip = request.client.host if request.client else "unknown"
        sensitive = request.url.path.startswith("/api/auth")
        limit = 20 if sensitive else 1200
        window = 60
        key = ("auth:" if sensitive else "api:") + ip
        try:
            if redis_client:
                tick = int(time.time() // window)
                rkey = "rate:" + key + ":" + str(tick)
                count = await run_in_threadpool(redis_client.eval,
                    "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
                    1,
                    rkey,
                    window,
                )
            else:
                q = local_buckets[key]
                now = time.time()
                while q and q[0] < now - window:
                    q.popleft()
                q.append(now)
                count = len(q)
            if count > limit:
                return JSONResponse(
                    {"detail": "Too many requests. Retry shortly."},
                    429,
                    headers={"Retry-After": "60"},
                )
        except Exception:
            return JSONResponse(
                {"detail": "Rate-limit service unavailable. Retry shortly."}, 503
            )
    response = await call_next(request)
    # Lifecycle diagnostics only: never request bodies, credentials or media content.
    path=request.url.path
    action=('bus.board' if path=='/api/transit/board' else 'bus.exit' if path=='/api/transit/exit'
        else 'vehicle.exit' if path=='/api/mobility/exit'
        else 'vehicle.enter' if path.startswith('/api/mobility/assets/') and path.endswith('/rent')
        else 'media.grant' if path.startswith('/api/media/') and path.endswith('/token') else None)
    if action and request.method=='POST':
        logging.getLogger('pulseworld.lifecycle').info('%s status=%s',action,response.status_code)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        {
            "detail": "This operation conflicts with an existing record. Refresh and retry."
        },
        status_code=409,
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0-alpha"}


@app.get("/api/health")
@app.get("/ready")
def ready():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1 FROM users LIMIT 1"))
            if APP_ENV in {"staging", "production"}:
                c.execute(text("SELECT PostGIS_Version()"))
        if redis_client:
            redis_client.ping()
    except Exception:
        raise HTTPException(503, "Database/migrations or Redis unavailable")
    return {"status": "ready", "environment": APP_ENV, "release_ready": False}


def realtime_state(token, with_expiry=False):
    with SessionLocal.begin() as db:
        u = user_for_token(db, token)
        expires_at=db.get(Session,hashlib.sha256(token.encode()).hexdigest()).expires_at
        p = db.get(Presence, u.id)
        result = (
            world.snapshot(db, u, p.city)
            if p
            else {"players": [], "collectibles": []}
        )
        result["type"] = "state"
        from .talk import snapshot as talk_snapshot
        result["talk"] = talk_snapshot(db,u)
        result["notifications"] = [
            serialize(n)
            for n in db.scalars(
                select(Notification)
                .where(
                    Notification.user_id == u.id,
                    Notification.created_at > time.time() - 120,
                )
                .order_by(Notification.created_at.desc())
                .limit(20)
            )
        ]
        result['media']=media.sessions(u,db)
        result['nearby_conversations']=conversations.nearby_conversations(db,u)
        result['communication_rules']=conversations.rules()
        if redis_client:
            redis_client.setex(
                "presence:" + u.id,
                45,
                str(
                    {"city": u.city, "x": p.x if p else 0, "z": p.z if p else 0}
                ),
            )
    return (result,expires_at) if with_expiry else result


class MotionInput(core.Strict):
    type: Literal['input']
    seq: int = Field(ge=1, le=9007199254740991)
    city: str = Field(max_length=50)
    zone: str = Field(max_length=100)
    action: Literal['move','drive']
    x: float = Field(ge=-1, le=1, allow_inf_nan=False)
    z: float = Field(ge=-1, le=1, allow_inf_nan=False)
    mode: Literal['walk','run'] = 'walk'


def realtime_motion(token, data):
    """Use the same authenticated movement/lease handlers, never client positions."""
    with SessionLocal.begin() as db:
        u=user_for_token(db,token)
        db.scalar(select(User.id).where(User.id==u.id).with_for_update())
        p=db.get(Presence,u.id)
        if not p or (p.city,p.zone_id)!=(data.city,data.zone):
            raise HTTPException(409,'Your location changed. Movement was cleared.')
        growth.require_access(db,u,p.city)
        result=(mobility.drive(mobility.Drive(steer=data.x,throttle=-data.z),u,db)
                if data.action=='drive' else world.move(world.Movement(dx=data.x,dz=data.z,mode=data.mode),u,db))
        if 'position' not in result:result={'position':result,'exited':result.get('exited',False)}
        return {'type':'motion','seq':data.seq,'city':data.city,'input_zone':data.zone,**result}


@app.websocket("/api/realtime")
async def realtime(socket: WebSocket):
    origin = socket.headers.get("origin")
    if (origin or socket.cookies.get("pulse-session")) and origin != os.getenv("PUBLIC_ORIGIN", "http://localhost:3000"):
        await socket.close(code=4403)
        return
    await socket.accept()
    tasks=[]
    try:
        initial = await asyncio.wait_for(socket.receive_json(), timeout=5)
        if not isinstance(initial,dict):raise HTTPException(401,'Invalid session')
        token = initial.get("token") or socket.cookies.get("pulse-session", "")
        if not isinstance(token, str) or len(token) > 256:
            raise HTTPException(401, "Invalid session")
        send_lock=asyncio.Lock()
        pending=asyncio.Queue(maxsize=2)
        async def send(value):
            async with send_lock:await socket.send_json(value)
        state_cache=realtime_cache.StateCache()
        def read_state():return state_cache.read(lambda:realtime_state(token,with_expiry=True))
        initial_state=await run_in_threadpool(read_state)
        initial_state['movement_transport']='input-v1'
        await send(initial_state)
        async def states():
            while True:
                await asyncio.sleep(.5)
                result=await run_in_threadpool(read_state)
                result['movement_transport']='input-v1'
                await send(result)
        async def receive_inputs():
            last_seq=0;arrivals=deque()
            while True:
                raw=await socket.receive_text()
                if len(raw)>512:raise HTTPException(400,'Input too large')
                now=time.monotonic()
                while arrivals and arrivals[0]<now-1:arrivals.popleft()
                arrivals.append(now)
                if len(arrivals)>30:raise HTTPException(429,'Input rate exceeded')
                try:data=MotionInput.model_validate_json(raw)
                except ValidationError:
                    await send({'type':'motion_error','message':'Invalid movement input'});continue
                if data.seq<=last_seq:continue
                last_seq=data.seq
                # Keep a press/release pair so a quick tap is not erased.
                # The two-slot bound and age check prevent an old input backlog.
                if pending.full():pending.get_nowait()
                pending.put_nowait((time.monotonic(),data))
        async def moves():
            while True:
                received,data=await pending.get()
                if time.monotonic()-received>.35:continue
                try:await send(await run_in_threadpool(realtime_motion,token,data))
                except HTTPException as error:
                    if error.status_code in [401,403]:raise
                    await send({'type':'motion_error','seq':data.seq,'message':error.detail})
                # Limit processing even when a client sends faster than the UI.
                await asyncio.sleep(1/15)
        tasks=[asyncio.create_task(fn()) for fn in (states,receive_inputs,moves)]
        done,_=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        for task in done:task.result()
    except (WebSocketDisconnect, asyncio.TimeoutError, asyncio.CancelledError):
        pass
    except HTTPException as error:
        await socket.close(code=4401 if error.status_code==401 else 4429 if error.status_code==429 else 4403)
    except Exception:
        logging.getLogger("pulseworld").exception("Realtime state failed")
        try:
            await socket.close(code=1011)
        except Exception:
            pass
    finally:
        for task in tasks:task.cancel()
        with anyio.CancelScope(shield=True):
            await asyncio.gather(*tasks,return_exceptions=True)

from .geography import router as geography_router
app.include_router(geography_router)

from .talk import router as talk_router
app.include_router(talk_router)
from .places import router as places_router
app.include_router(places_router)
from .oauth import router as oauth_router
app.include_router(oauth_router)

from .collections import router as collections_router
app.include_router(collections_router)

from .media_policy import router as media_policy_router
app.include_router(media_policy_router)

from .public_profiles import router as public_profiles_router
app.include_router(public_profiles_router)

from .profile_media import router as profile_media_router
app.include_router(profile_media_router)

from .feedback import router as feedback_router
app.include_router(feedback_router)
