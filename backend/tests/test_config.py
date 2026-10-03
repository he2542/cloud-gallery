import os
import subprocess
import sys
import pytest

@pytest.mark.parametrize('overrides', [
    {'GALLERY_ENV':'prodution'},
    {'COOKIE_SECURE':'perhaps'},
    {'ALLOWED_ORIGINS':'https://example.com/invalid-path'},
    {'ALLOWED_ORIGINS':''},
    {'DATABASE_URL':'mysql://unsupported'},
    {'DATABASE_URL':'sqlite:///:memory:'},
])
def test_invalid_config_fails_at_startup(overrides):
    result=subprocess.run([sys.executable,'-c','from app.core.config import settings'],
                          env={**os.environ,**overrides}, capture_output=True, text=True)
    assert result.returncode != 0

@pytest.mark.parametrize('overrides', [
    {'GALLERY_ENV':'production','COOKIE_SECURE':'false','DATABASE_URL':'postgresql+psycopg://test:test@127.0.0.1/test'},
    {'GALLERY_ENV':'production','COOKIE_SECURE':'true','DATABASE_URL':'sqlite:///./data/test.db'},
])
def test_production_requires_secure_cookie_and_postgresql(overrides):
    result=subprocess.run([sys.executable,'-c','from app.core.config import settings'],
                          env={**os.environ,**overrides}, capture_output=True, text=True)
    assert result.returncode != 0
