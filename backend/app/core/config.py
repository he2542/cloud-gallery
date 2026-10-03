import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

def boolean_env(name, default='false'):
    value = os.getenv(name, default).strip().casefold()
    if value not in {'true', 'false'}:
        raise ValueError(f'{name} must be true or false')
    return value == 'true'

def parse_origins(raw):
    result = []
    for origin in raw.split(','):
        origin = origin.strip().rstrip('/')
        parsed = urlsplit(origin)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path or parsed.query or parsed.fragment):
            raise ValueError('ALLOWED_ORIGINS must contain HTTP(S) origins without paths')
        parsed.port
        result.append(origin)
    if not result:
        raise ValueError('At least one allowed origin is required')
    return tuple(dict.fromkeys(result))

@dataclass
class Settings:
    environment: str = os.getenv('GALLERY_ENV', 'development').strip().casefold()
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./data/gallery.db')
    storage_dir: Path = Path(os.getenv('STORAGE_DIR', './data/images')).resolve()
    quota: int = int(os.getenv('STORAGE_QUOTA_BYTES', str(10 * 1024**3)))
    max_upload: int = int(os.getenv('MAX_UPLOAD_BYTES', str(10 * 1024**2)))
    max_pixels: int = int(os.getenv('MAX_IMAGE_PIXELS', '12000000'))
    cookie_secure: bool = boolean_env('COOKIE_SECURE')
    origins: tuple = parse_origins(os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8040,http://localhost:4173,http://127.0.0.1:4173'))

    def __post_init__(self):
        if self.environment not in {'development', 'production'}:
            raise ValueError('GALLERY_ENV must be development or production')
        if min(self.quota, self.max_upload, self.max_pixels) <= 0:
            raise ValueError('Storage limits must be positive')
        try:
            url = make_url(self.database_url)
        except Exception:
            raise ValueError('DATABASE_URL is not a valid database URL') from None
        if url.drivername not in {'sqlite', 'postgresql+psycopg'} or not url.database:
            raise ValueError('Use a SQLite file or postgresql+psycopg database URL')
        if url.drivername == 'sqlite' and (url.database == ':memory:' or url.query.get('mode') == 'memory'):
            raise ValueError('Use a persistent SQLite file for the gallery')
        if self.environment == 'production':
            if url.drivername != 'postgresql+psycopg' or not self.cookie_secure:
                raise ValueError('Production requires PostgreSQL and COOKIE_SECURE=true')
            if any(not origin.startswith('https://') for origin in self.origins):
                raise ValueError('Production origins require HTTPS')

settings = Settings()
