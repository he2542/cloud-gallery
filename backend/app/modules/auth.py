import secrets
import time
from threading import Lock
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import check_login_limit, hash_password, optional_user, require_write, token_hash, verify_password
from app.models import LoginSession, Space, User
from app.schemas import Credentials

router = APIRouter(prefix='/auth', tags=['登录'])
_setup_lock = Lock()
_dummy_hash = hash_password(secrets.token_urlsafe(32))

def start_session(user, db, response):
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at < int(time.time())))
    db.add(LoginSession(token_hash=token_hash(raw), user_id=user.id, csrf=csrf, expires_at=int(time.time()) + 7 * 86400))
    db.commit()
    response.set_cookie('gallery_session', raw, httponly=True, secure=settings.cookie_secure, samesite='strict', max_age=7 * 86400, path='/')
    response.headers['Cache-Control'] = 'no-store'
    return {'user': {'id': user.id, 'username': user.username}, 'csrf_token': csrf}

@router.post('/setup')
def setup(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    if settings.environment == 'production':
        raise HTTPException(404)
    check_login_limit(request)
    with _setup_lock:
        if db.scalar(select(func.count(User.id)).where(User.disabled.is_(False))):
            raise HTTPException(409, '已有账户，请使用登录')
        user = User(username=body.username, password_hash=hash_password(body.password))
        db.add(user)
        db.flush()
        db.add(Space(name='我的私有空间', owner_id=user.id, is_public=False))
        return start_session(user, db, response)

@router.post('/login')
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    check_login_limit(request)
    user = db.scalar(select(User).where(User.username == body.username))
    valid = verify_password(body.password, user.password_hash if user else _dummy_hash)
    if not user or user.disabled or not valid:
        raise HTTPException(401, '用户名或密码不正确')
    return start_session(user, db, response)

@router.get('/me')
def me(request: Request, response: Response, user=Depends(optional_user)):
    response.headers['Cache-Control'] = 'no-store'
    return {'user': {'id': user.id, 'username': user.username} if user else None, 'csrf_token': request.state.login.csrf if user else ''}

@router.post('/logout', status_code=204)
def logout(request: Request, response: Response, user=Depends(require_write), db: Session = Depends(get_db)):
    db.delete(request.state.login)
    db.commit()
    response.delete_cookie('gallery_session', path='/', secure=settings.cookie_secure, httponly=True, samesite='strict')
