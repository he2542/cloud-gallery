import base64
import hashlib
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import LoginSession, User

def hash_password(password):
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return base64.b64encode(salt + key).decode()

def verify_password(password, stored):
    try:
        data = base64.b64decode(stored)
        key = hashlib.scrypt(password.encode(), salt=data[:16], n=16384, r=8, p=1)
        return secrets.compare_digest(key, data[16:])
    except (ValueError, TypeError):
        return False

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def optional_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get('gallery_session', '')
    login = db.get(LoginSession, token_hash(token)) if token else None
    if login is None or login.expires_at <= time.time():
        return None
    request.state.login = login
    user = db.get(User, login.user_id)
    return user if user and not user.disabled else None

def require_user(user=Depends(optional_user)):
    if user is None:
        raise HTTPException(401, '请先登录')
    return user

def require_write(request: Request, user=Depends(require_user)):
    supplied = request.headers.get('x-csrf-token', '')
    if not supplied.isascii() or not secrets.compare_digest(supplied, request.state.login.csrf):
        raise HTTPException(403, '请求验证失败，请刷新页面后重试')
    return user

_attempts = defaultdict(deque)
_lock = Lock()

def check_login_limit(request):
    key, now = request.client.host if request.client else 'unknown', time.monotonic()
    with _lock:
        if len(_attempts) > 4096:
            for old in list(_attempts):
                if not _attempts[old] or _attempts[old][-1] < now - 300:
                    del _attempts[old]
            if len(_attempts) > 4096:
                raise HTTPException(429, '登录繁忙，请稍后重试')
        bucket = _attempts[key]
        while bucket and bucket[0] < now - 300:
            bucket.popleft()
        if len(bucket) >= 10:
            raise HTTPException(429, '尝试次数过多，请 5 分钟后重试')
        bucket.append(now)
