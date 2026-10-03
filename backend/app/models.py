import time
import uuid
from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = 'gallery_users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)

class LoginSession(Base):
    __tablename__ = 'gallery_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('gallery_users.id', ondelete='CASCADE'), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(BigInteger)

class Space(Base):
    __tablename__ = 'gallery_spaces'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey('gallery_users.id'), index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

class Storage(Base):
    __tablename__ = 'gallery_storage'
    id: Mapped[int] = mapped_column(primary_key=True)
    used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

class Tag(Base):
    __tablename__ = 'gallery_tags'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(24), unique=True)

class PictureTag(Base):
    __tablename__ = 'gallery_picture_tags'
    picture_id: Mapped[str] = mapped_column(ForeignKey('gallery_pictures.id', ondelete='CASCADE'), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey('gallery_tags.id', ondelete='CASCADE'), primary_key=True)

class Picture(Base):
    __tablename__ = 'gallery_pictures'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default='')
    owner_id: Mapped[int] = mapped_column(ForeignKey('gallery_users.id'), index=True)
    space_id: Mapped[int] = mapped_column(ForeignKey('gallery_spaces.id'), index=True)
    width: Mapped[int]
    height: Mapped[int]
    byte_size: Mapped[int] = mapped_column(BigInteger)
    extension: Mapped[str] = mapped_column(String(5))
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time.time()), index=True)
    tags: Mapped[list[Tag]] = relationship(secondary='gallery_picture_tags', lazy='selectin')
    space: Mapped[Space] = relationship(lazy='joined')
