import io
import time
import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.config import settings
from app.models import LoginSession, Picture, Storage, User
from app.storage import process_image
from app.main import app
from conftest import login

def image_bytes():
    stream = io.BytesIO()
    Image.new('RGB', (64, 48), '#245dbc').save(stream, 'PNG')
    return stream.getvalue()

def space(client, private=True):
    return next(s['id'] for s in client.get('/api/spaces').json() if s['is_public'] != private)

def upload(client, headers, private=True, **fields):
    return client.post('/api/pictures', headers=headers,
                       data={'space_id': space(client, private), 'title': '测试图片', 'tags': '["测试"]', **fields},
                       files={'file': ('picture.png', image_bytes(), 'image/png')})

def test_setup_session_logout_and_expiry(client):
    assert client.get('/api/health').json()['setup_required'] is True
    credentials = {'username': 'owner', 'password': 'test-only-password'}
    r = client.post('/api/auth/setup', json=credentials)
    assert r.status_code == 200
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
    assert client.post('/api/auth/setup', json=credentials).status_code == 409
    headers = {'X-CSRF-Token': r.json()['csrf_token']}
    assert client.post('/api/auth/logout', headers=headers).status_code == 204
    assert client.get('/api/auth/me').json()['user'] is None
    login(client, 'owner')
    with SessionLocal() as db:
        record = db.scalar(select(LoginSession))
        record.expires_at = int(time.time()) - 1
        db.commit()
    assert client.get('/api/auth/me').json()['user'] is None

def test_private_files_metadata_and_tags_are_isolated(client, users):
    headers = login(client)
    r = upload(client, headers, title='私密计划', tags='["机密"]')
    assert r.status_code == 201
    p = r.json()
    assert client.get(f"/api/pictures/{p['id']}/content").status_code == 200
    assert client.get('/api/storage').json()['visible_bytes'] == p['byte_size']
    login(client, 'bob')
    assert client.get('/api/pictures').json()['total'] == 0
    assert client.get('/api/tags').json() == []
    assert client.get('/api/storage').json()['visible_bytes'] == 0
    for suffix in ('', '?thumb=true'):
        assert client.get(f"/api/pictures/{p['id']}/content{suffix}").status_code == 404
    assert client.patch(f"/api/pictures/{p['id']}", json={'title': '偷改'}, headers=login(client, 'bob')).status_code == 404

def test_public_read_owner_only_edit_and_privacy_switch(client, users):
    headers = login(client)
    created = client.post('/api/spaces', json={'name': '可公开空间', 'is_public': True}, headers=headers).json()
    p = upload(client, headers, space_id=created['id']).json()
    with TestClient(app) as guest:
        r = guest.get(f"/api/pictures/{p['id']}/content?thumb=true")
        assert r.status_code == 200
        assert r.headers['cache-control'] == 'no-store'
        assert guest.get('/api/pictures').json()['total'] == 1
        assert guest.delete(f"/api/pictures/{p['id']}").status_code == 401
    bob = login(client, 'bob')
    assert client.patch(f"/api/pictures/{p['id']}", json={'title': '偷改'}, headers=bob).status_code == 403
    assert upload(client, bob, space_id=created['id']).status_code == 404
    headers = login(client)
    assert client.patch(f"/api/spaces/{created['id']}", json={'name': '私有空间', 'is_public': False}, headers=headers).status_code == 200
    with TestClient(app) as guest:
        assert guest.get(f"/api/pictures/{p['id']}/content").status_code == 404
        assert guest.get('/api/pictures').json()['total'] == 0

def test_write_requires_csrf_and_allowed_origin(client, users):
    headers = login(client)
    assert upload(client, {}).status_code == 403
    assert upload(client, {**headers, 'Origin': 'https://attacker.invalid'}).status_code == 403
    assert upload(client, {**headers, 'Origin': 'http://127.0.0.1:5173'}).status_code == 201

def test_invalid_image_and_limits_leave_no_files(client, users, monkeypatch):
    headers = login(client)
    bad = client.post('/api/pictures', headers=headers, data={'space_id': space(client)},
                      files={'file': ('fake.png', b'not an image', 'image/png')})
    assert bad.status_code == 415
    monkeypatch.setattr(settings, 'max_pixels', 100)
    assert upload(client, headers).status_code == 413
    monkeypatch.setattr(settings, 'max_pixels', 12000000)
    monkeypatch.setattr(settings, 'quota', 1)
    assert upload(client, headers).status_code == 413
    assert client.get('/api/pictures').json()['total'] == 0
    assert not settings.storage_dir.exists() or not list(settings.storage_dir.iterdir())
    with SessionLocal() as db:
        assert db.get(Storage, 1).used_bytes == 0

def test_metadata_search_pagination_delete_and_counter(client, users):
    headers = login(client)
    p = upload(client, headers).json()
    r = client.patch(f"/api/pictures/{p['id']}", headers=headers,
                     json={'title': '100% 自然风景', 'description': '测试说明', 'tags': [' 山 ', '山', 'Nature']})
    assert r.status_code == 200
    assert r.json()['tags'] == ['山', 'nature']
    assert client.get('/api/pictures', params={'q': '%'}).json()['total'] == 1
    assert client.get('/api/pictures', params={'tag': 'nature'}).json()['total'] == 1
    assert client.get('/api/pictures', params={'page': 2, 'size': 1}).json()['items'] == []
    assert client.delete(f"/api/pictures/{p['id']}", headers=headers).status_code == 204
    assert client.get('/api/tags').json() == []
    assert list(settings.storage_dir.iterdir()) == []
    with SessionLocal() as db:
        assert db.get(Storage, 1).used_bytes == 0

def test_transparent_png_strips_metadata_and_preserves_alpha(client, users):
    headers = login(client)
    image = Image.new('RGBA', (40, 30), (15, 85, 145, 70))
    exif = Image.Exif()
    exif[315] = 'private-author-marker'
    stream = io.BytesIO()
    image.save(stream, 'PNG', exif=exif, icc_profile=b'private-profile-marker')
    r = client.post('/api/pictures', headers=headers, data={'space_id': space(client)},
                    files={'file': ('alpha.png', stream.getvalue(), 'image/png')})
    assert r.status_code == 201
    for thumb in (False, True):
        raw = client.get(f"/api/pictures/{r.json()['id']}/content", params={'thumb': thumb}).content
        with Image.open(io.BytesIO(raw)) as result:
            result.load()
            assert not result.getexif()
            assert not any(k in result.info for k in ('exif', 'icc_profile', 'xmp'))
            assert result.mode == 'RGBA'
            assert result.getpixel((0, 0))[3] == 70

def test_non_ascii_csrf_is_rejected_not_server_error(client, users):
    login(client)
    r = client.post('/api/spaces', headers=[(b'x-csrf-token', b'\xe9')],
                    json={'name':'blocked'})
    assert r.status_code == 403

def test_parallel_space_creation_respects_limit(client, users):
    from sqlalchemy import event
    from app.core.database import engine
    headers = login(client)
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == 'alice'))
        from app.models import Space
        for i in range(18):
            db.add(Space(name=f'private {i}', owner_id=u.id, is_public=False))
        db.commit()
    cookies = dict(client.cookies)
    def send(i):
        with TestClient(app) as c:
            c.cookies.update(cookies)
            return c.post('/api/spaces', headers=headers, json={'name':f'concurrent {i}'}).status_code
    def slow_count(conn, cursor, statement, parameters, context, executemany):
        if 'count(gallery_spaces.id)' in statement:
            time.sleep(0.05)
    event.listen(engine, 'after_cursor_execute', slow_count)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(send, range(2))) == [201,400]
    finally:
        event.remove(engine, 'after_cursor_execute', slow_count)
    assert len([s for s in client.get('/api/spaces').json() if s['owner_id'] is not None]) == 20

def test_parallel_uploads_cannot_exceed_global_quota(client, users, monkeypatch):
    headers = login(client)
    raw = image_bytes()
    full, thumb, _, _ = process_image(raw)
    monkeypatch.setattr(settings, 'quota', len(full) + len(thumb))
    target = space(client)
    cookies = dict(client.cookies)
    def send(_):
        with TestClient(app) as c:
            c.cookies.update(cookies)
            return c.post('/api/pictures', headers=headers, data={'space_id': target},
                          files={'file': ('x.png', raw, 'image/png')}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, range(2))) == [201, 413]
    with SessionLocal() as db:
        assert db.get(Storage, 1).used_bytes == settings.quota
        assert len(db.scalars(select(Picture)).all()) == 1

def test_production_setup_is_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, 'environment', 'production')
    assert client.post('/api/auth/setup', json={'username': 'owner', 'password': 'test-only-password'}).status_code == 404

def test_login_rate_limit_and_disabled_accounts(client, users):
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == 'alice'))
        u.disabled = True
        db.commit()
    for _ in range(10):
        assert client.post('/api/auth/login', json={'username': 'alice', 'password': 'test-only-password'}).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'alice', 'password': 'test-only-password'}).status_code == 429

def test_parallel_delete_decrements_counter_once(client, users):
    headers = login(client)
    p = upload(client, headers).json()
    cookies = dict(client.cookies)
    def send(_):
        with TestClient(app) as c:
            c.cookies.update(cookies)
            return c.delete(f"/api/pictures/{p['id']}", headers=headers).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(send, range(2))) == [204, 404]
    with SessionLocal() as db:
        assert db.get(Storage, 1).used_bytes == 0

def test_demo_is_disabled_idempotent_and_cleanable(client):
    from app.demo import seed, clear
    seed()
    seed()
    assert client.get('/api/health').json()['setup_required'] is True
    assert client.get('/api/pictures').json()['total'] == 8
    with SessionLocal() as db:
        demo = db.scalar(select(User).where(User.username == '__demo__'))
        assert demo.disabled is True
    clear()
    assert client.get('/api/pictures').json()['total'] == 0
    with SessionLocal() as db:
        assert db.get(Storage, 1).used_bytes == 0
    assert list(settings.storage_dir.iterdir()) == []

def test_image_orientation_and_thumbnail_size(client, users):
    headers = login(client)
    source = Image.new('RGB', (1000, 800), '#357ab0')
    exif = Image.Exif()
    exif[274] = 6
    raw = io.BytesIO()
    source.save(raw, 'JPEG', exif=exif)
    r = client.post('/api/pictures', headers=headers, data={'space_id': space(client)},
                    files={'file': ('portrait.jpg', raw.getvalue(), 'image/jpeg')})
    assert r.status_code == 201
    assert (r.json()['width'], r.json()['height']) == (800, 1000)
    response = client.get(f"/api/pictures/{r.json()['id']}/content?thumb=true")
    with Image.open(io.BytesIO(response.content)) as thumbnail:
        assert thumbnail.format == 'WEBP'
        assert thumbnail.size == (576,720)

def test_upload_byte_limit(client, users, monkeypatch):
    headers = login(client)
    monkeypatch.setattr(settings, 'max_upload', 1)
    r = upload(client, headers)
    assert r.status_code == 413
    assert '上传大小' in r.json()['detail']
    with SessionLocal() as db:
        assert db.get(Storage,1).used_bytes == 0

@pytest.mark.parametrize('failure', ['commit','thumbnail_write'])
def test_upload_failure_rolls_back_files_and_quota(client, users, monkeypatch, failure):
    from pathlib import Path
    from sqlalchemy.orm import Session
    headers = login(client)
    with TestClient(app, raise_server_exceptions=False) as fault:
        fault.cookies.update(dict(client.cookies))
        if failure == 'commit':
            def fail_commit(self):
                raise RuntimeError('synthetic commit failure')
            monkeypatch.setattr(Session, 'commit', fail_commit)
        else:
            original_write=Path.write_bytes
            def fail_thumb(path, content):
                if path.name.endswith('.thumb.webp'):
                    raise OSError('synthetic disk failure')
                return original_write(path,content)
            monkeypatch.setattr(Path,'write_bytes',fail_thumb)
        r=upload(fault,headers)
        assert r.status_code == 500
        assert 'synthetic' not in r.text
    with SessionLocal() as db:
        assert db.get(Storage,1).used_bytes == 0
        assert db.scalar(select(Picture.id)) is None
    assert not settings.storage_dir.exists() or list(settings.storage_dir.iterdir()) == []

def test_text_validation_rejects_empty_titles_and_null_bytes(client, users):
    headers=login(client)
    p=upload(client,headers).json()
    for payload in ({'title':'   '},{'title':'bad\x00name'},
                    {'title':'ok','description':'bad\x00description'},
                    {'title':'ok','tags':['bad\x00tag']}):
        assert client.patch(f"/api/pictures/{p['id']}",headers=headers,json=payload).status_code == 422
    for name in ('   ','bad\x00space'):
        assert client.post('/api/spaces',headers=headers,json={'name':name}).status_code == 422
    for query in ({'q':'bad\x00query'},{'tag':'bad\x00tag'}):
        assert client.get('/api/pictures',params=query).status_code == 422
    r=client.patch(f"/api/pictures/{p['id']}",headers=headers,json={'title':'  trimmed  '})
    assert r.json()['title'] == 'trimmed'

def test_invalid_credentials_are_not_echoed(client):
    marker = 'validation-sensitive-marker-' * 6
    r = client.post('/api/auth/login', json={'username':'owner','password':marker})
    assert r.status_code == 422
    assert marker not in r.text
    assert all('input' not in item for item in r.json()['detail'])
