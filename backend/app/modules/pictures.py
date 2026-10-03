import json
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.core.config import settings
from app.core.database import get_db
from app.core.security import optional_user, require_write
from app.models import Picture, PictureTag, Space, Storage, Tag
from app.schemas import PictureEdit
from app.storage import image_paths, process_image, remove_paths
from .spaces import visible_spaces

router = APIRouter(tags=['图片'])

def serialize(p, user):
    return {'id': p.id, 'title': p.title, 'description': p.description, 'space_id': p.space_id,
            'space_name': p.space.name, 'is_public': p.space.is_public, 'width': p.width, 'height': p.height,
            'byte_size': p.byte_size, 'created_at': p.created_at, 'tags': [t.name for t in p.tags],
            'can_edit': bool(user and p.owner_id == user.id)}

def get_visible(picture_id, user, db):
    picture = db.get(Picture, picture_id)
    if not picture or not (picture.space.is_public or (user and picture.space.owner_id == user.id)):
        raise HTTPException(404, '图片不存在')
    return picture

def assign_tags(picture, names, db):
    tags = []
    for name in names:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            try:
                with db.begin_nested():
                    tag = Tag(name=name)
                    db.add(tag)
                    db.flush()
            except IntegrityError:
                tag = db.scalar(select(Tag).where(Tag.name == name))
        tags.append(tag)
    picture.tags = tags

@router.get('/pictures')
def list_pictures(q: str = Query('', max_length=100, pattern=r'^[^\x00]*$'), tag: str = Query('', max_length=24, pattern=r'^[^\x00]*$'), space_id: int | None = None,
                  page: int = Query(1, ge=1), size: int = Query(24, ge=1, le=60), user=Depends(optional_user), db: Session = Depends(get_db)):
    criteria = [visible_spaces(user)]
    if space_id is not None:
        criteria.append(Picture.space_id == space_id)
    if tag:
        criteria.append(Picture.tags.any(Tag.name == tag.strip().casefold()))
    if q.strip():
        escaped = q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = f'%{escaped}%'
        criteria.append(or_(Picture.title.ilike(pattern, escape='\\'), Picture.tags.any(Tag.name.ilike(pattern, escape='\\'))))
    query = select(Picture).join(Space).where(*criteria)
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.options(selectinload(Picture.tags)).order_by(Picture.created_at.desc(), Picture.id).offset((page - 1) * size).limit(size)).all()
    return {'items': [serialize(p, user) for p in rows], 'total': count, 'page': page, 'size': size}

@router.get('/tags')
def list_tags(user=Depends(optional_user), db: Session = Depends(get_db)):
    query = select(Tag.name, func.count(Picture.id)).join(PictureTag, PictureTag.tag_id == Tag.id).join(Picture, Picture.id == PictureTag.picture_id).join(Space).where(visible_spaces(user)).group_by(Tag.name).order_by(Tag.name)
    return [{'name': name, 'count': count} for name, count in db.execute(query)]

@router.get('/storage')
def storage_status(user=Depends(optional_user), db: Session = Depends(get_db)):
    visible = db.scalar(select(func.coalesce(func.sum(Picture.byte_size), 0)).join(Space).where(visible_spaces(user)))
    return {'visible_bytes': visible, 'quota_bytes': settings.quota, 'max_upload_bytes': settings.max_upload, 'max_pixels': settings.max_pixels}

@router.post('/pictures', status_code=201)
def upload(file: UploadFile = File(...), space_id: int = Form(...), title: str = Form(''), tags: str = Form('[]'), user=Depends(require_write), db: Session = Depends(get_db)):
    space = db.get(Space, space_id)
    if not space or (space.owner_id is not None and space.owner_id != user.id):
        raise HTTPException(404, '空间不存在或无上传权限')
    try:
        fields = PictureEdit(title=title.strip() or (file.filename or '未命名图片')[:100], tags=json.loads(tags))
    except (ValidationError, ValueError, TypeError):
        raise HTTPException(422, '图片名称或标签格式不正确') from None
    raw = bytearray()
    while chunk := file.file.read(65536):
        raw.extend(chunk)
        if len(raw) > settings.max_upload:
            raise HTTPException(413, '图片超过上传大小限制')
    full, thumb, ext, (width, height) = process_image(raw)
    p = Picture(id=str(uuid.uuid4()), title=fields.title, description='', owner_id=user.id, space_id=space_id, width=width, height=height, byte_size=len(full) + len(thumb), extension=ext)
    paths = image_paths(p.id, ext)
    try:
        reservation = db.execute(update(Storage).where(Storage.id == 1, Storage.used_bytes + p.byte_size <= settings.quota).values(used_bytes=Storage.used_bytes + p.byte_size))
        if reservation.rowcount != 1:
            raise HTTPException(413, '图库存储配额已用完')
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        paths[0].write_bytes(full)
        paths[1].write_bytes(thumb)
        db.add(p)
        assign_tags(p, fields.tags, db)
        db.flush()
        result = serialize(p, user)
        db.commit()
        return result
    except Exception:
        db.rollback()
        remove_paths(paths)
        raise

@router.get('/pictures/{picture_id}/content')
def content(picture_id: str, thumb: bool = False, user=Depends(optional_user), db: Session = Depends(get_db)):
    p = get_visible(picture_id, user, db)
    path = image_paths(p.id, p.extension)[int(thumb)]
    if not path.is_file():
        raise HTTPException(404, '文件不存在')
    return FileResponse(path, media_type='image/webp' if thumb else ('image/png' if p.extension == 'png' else 'image/jpeg'), headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})

@router.patch('/pictures/{picture_id}')
def edit(picture_id: str, body: PictureEdit, user=Depends(require_write), db: Session = Depends(get_db)):
    p = get_visible(picture_id, user, db)
    if p.owner_id != user.id:
        raise HTTPException(403, '只能修改自己的图片')
    p.title, p.description = body.title, body.description
    assign_tags(p, body.tags, db)
    db.commit()
    return serialize(p, user)

@router.delete('/pictures/{picture_id}', status_code=204)
def delete_picture(picture_id: str, user=Depends(require_write), db: Session = Depends(get_db)):
    p = get_visible(picture_id, user, db)
    if p.owner_id != user.id:
        raise HTTPException(403, '只能删除自己的图片')
    paths = image_paths(p.id, p.extension)
    size = db.execute(delete(Picture).where(Picture.id == p.id).returning(Picture.byte_size)).scalar_one_or_none()
    if size is None:
        db.rollback()
        raise HTTPException(404, '图片不存在')
    db.execute(update(Storage).where(Storage.id == 1).values(used_bytes=Storage.used_bytes - size))
    db.commit()
    remove_paths(paths)
