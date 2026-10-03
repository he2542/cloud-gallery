from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from app.core.config import settings
from app.core.database import SessionLocal, engine, init_db
from app.models import User
from app.modules import auth, pictures, spaces

@asynccontextmanager
async def lifespan(app):
    if settings.environment == 'development':
        init_db()
    yield
    engine.dispose()

app = FastAPI(title='云图库 API', version='0.1.1', lifespan=lifespan)

@app.middleware('http')
async def request_guard(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        if origin and origin not in settings.origins:
            return JSONResponse({'detail': '来源不被允许'}, status_code=403)
    if request.method == 'POST' and request.url.path == '/api/pictures':
        length = request.headers.get('content-length')
        if not length:
            return JSONResponse({'detail': '上传必须提供 Content-Length'}, status_code=411)
        try:
            if int(length) < 0 or int(length) > settings.max_upload + 1024**2:
                return JSONResponse({'detail': '上传请求过大'}, status_code=413)
        except ValueError:
            return JSONResponse({'detail': '请求长度不合法'}, status_code=400)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.exception_handler(Exception)
async def unexpected_error(request, error):
    return JSONResponse({'detail': '服务暂时不可用，请稍后重试'}, status_code=500,
                        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # Do not echo submitted passwords or other input values in validation errors.
    details = [{key: item[key] for key in ('loc', 'msg', 'type')} for item in error.errors()]
    return JSONResponse({'detail': details}, status_code=422)

@app.get('/api/health')
def health():
    try:
        with SessionLocal() as db:
            db.execute(text('SELECT 1'))
            setup_required = settings.environment == 'development' and db.scalar(select(func.count(User.id)).where(User.disabled.is_(False))) == 0
        return {'status': 'ok', 'setup_required': setup_required, 'storage': 'local', 'database': engine.dialect.name}
    except Exception:
        return JSONResponse({'status': 'unavailable'}, status_code=503)

app.include_router(auth.router, prefix='/api')
app.include_router(spaces.router, prefix='/api')
app.include_router(pictures.router, prefix='/api')
