from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.database import get_db, lock_account
from app.core.security import optional_user, require_write
from app.models import Picture, Space
from app.schemas import SpaceInput

router = APIRouter(prefix='/spaces', tags=['空间'])

def visible_spaces(user):
    return or_(Space.is_public.is_(True), Space.owner_id == user.id) if user else Space.is_public.is_(True)

@router.get('')
def list_spaces(user=Depends(optional_user), db: Session = Depends(get_db)):
    spaces = db.scalars(select(Space).where(visible_spaces(user)).order_by(Space.id)).all()
    return [{'id': s.id, 'name': s.name, 'owner_id': s.owner_id, 'is_public': s.is_public,
             'picture_count': db.scalar(select(func.count(Picture.id)).where(Picture.space_id == s.id)),
             'used_bytes': db.scalar(select(func.coalesce(func.sum(Picture.byte_size), 0)).where(Picture.space_id == s.id))} for s in spaces]

@router.post('', status_code=201)
def create_space(body: SpaceInput, user=Depends(require_write), db: Session = Depends(get_db)):
    lock_account(db, user.id)
    if db.scalar(select(func.count(Space.id)).where(Space.owner_id == user.id)) >= 20:
        raise HTTPException(400, '最多创建 20 个空间')
    if not body.name.strip():
        raise HTTPException(422, '请输入空间名称')
    space = Space(name=body.name.strip(), owner_id=user.id, is_public=body.is_public)
    db.add(space)
    db.commit()
    return {'id': space.id}

@router.patch('/{space_id}')
def edit_space(space_id: int, body: SpaceInput, user=Depends(require_write), db: Session = Depends(get_db)):
    space = db.get(Space, space_id)
    if not space or space.owner_id != user.id:
        raise HTTPException(404, '空间不存在')
    if not body.name.strip():
        raise HTTPException(422, '请输入空间名称')
    space.name, space.is_public = body.name.strip(), body.is_public
    db.commit()
    return {'id': space.id}
