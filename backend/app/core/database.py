from pathlib import Path
from sqlalchemy import create_engine, event, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

class Base(DeclarativeBase):
    pass

def make_engine(url):
    options = {'pool_pre_ping': True}
    if url.startswith('sqlite'):
        filename = make_url(url).database
        if filename != ':memory:':
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
        options['connect_args'] = {'check_same_thread': False, 'timeout': 15}
    else:
        options.update(pool_size=2, max_overflow=2, pool_timeout=10, connect_args={'connect_timeout': 5})
    result = create_engine(url, **options)
    if url.startswith('sqlite'):
        @event.listens_for(result, 'connect')
        def configure(conn, record):
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA journal_mode=WAL')
    return result

engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as session:
        yield session

def lock_account(db, user_id):
    # A no-op UPDATE locks the account within this transaction on both databases.
    from app.models import User
    db.execute(update(User).where(User.id == user_id).values(disabled=User.disabled))

def init_db():
    from app.models import Space, Storage
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(Storage, 1) is None:
            db.add(Storage(id=1, used_bytes=0))
        if db.query(Space).filter_by(owner_id=None).first() is None:
            db.add(Space(name='公共图库', owner_id=None, is_public=True))
        db.commit()
