import os
import tempfile
from pathlib import Path
import pytest

# Always use a temporary database. Never load a developer/production database.
_workspace = tempfile.TemporaryDirectory(prefix='cloud-gallery-tests-')
os.environ.update(GALLERY_ENV='development',
                  DATABASE_URL=f"sqlite:///{Path(_workspace.name, 'test.db').as_posix()}",
                  STORAGE_DIR=str(Path(_workspace.name, 'images')),
                  STORAGE_QUOTA_BYTES=str(10 * 1024**3), MAX_UPLOAD_BYTES=str(10 * 1024**2),
                  MAX_IMAGE_PIXELS='12000000', ALLOWED_ORIGINS='http://127.0.0.1:5173,http://127.0.0.1:8040',
                  COOKIE_SECURE='false')
from app.core.database import Base, engine, init_db, SessionLocal
from app.core.config import settings
from app.core.security import _attempts, hash_password
from app.models import User, Space
from app.main import app
from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def clean_database(tmp_path, monkeypatch):
    Base.metadata.drop_all(engine)
    init_db()
    _attempts.clear()
    monkeypatch.setattr(settings, 'storage_dir', tmp_path / 'images')
    yield

@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value

@pytest.fixture
def users():
    with SessionLocal() as db:
        for name in ('alice', 'bob'):
            u = User(username=name, password_hash=hash_password('test-only-password'))
            db.add(u)
            db.flush()
            db.add(Space(name=f'{name} private', owner_id=u.id, is_public=False))
        db.commit()
    return ('alice', 'bob')

def login(client, name='alice'):
    response = client.post('/api/auth/login', json={'username': name, 'password': 'test-only-password'})
    assert response.status_code == 200
    return {'X-CSRF-Token': response.json()['csrf_token']}
