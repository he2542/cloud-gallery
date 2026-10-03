"""Optional, original illustration fixtures. No external images or login password."""
import io
import math
import secrets
import uuid
from PIL import Image, ImageDraw
from sqlalchemy import select, update
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models import Picture, Space, Storage, User
from app.modules.pictures import assign_tags
from app.storage import process_image, image_paths, remove_paths

PALETTES = [
    ('远山与晨光', '#efcfae', '#ece9d3', '#809aa0', '#355761', '山野'),
    ('日落海岸', '#ebc2a7', '#eebf8e', '#638c8c', '#244f64', '海边'),
    ('绿色森林', '#dce5ca', '#b7d5ce', '#609382', '#235d55', '自然'),
    ('城市余晖', '#ddd2e6', '#a3b1ce', '#6e819f', '#364661', '城市'),
    ('沙漠旅途', '#f4ddae', '#f1c29e', '#c18c67', '#825d4e', '旅行'),
    ('蓝色海湾', '#c6dfdf', '#8dbac9', '#49869c', '#234d74', '海边'),
    ('雪山日记', '#dfe6ed', '#bacbdc', '#8ca7be', '#4e718d', '山野'),
    ('秋日山林', '#ede1c9', '#dbb382', '#a58457', '#686c44', '自然'),
]

def illustration(index):
    title, top, bottom, back, front, tag = PALETTES[index]
    size = 960, 720
    im = Image.new('RGB', size)
    draw = ImageDraw.Draw(im)
    c1 = tuple(bytes.fromhex(top[1:]))
    c2 = tuple(bytes.fromhex(bottom[1:]))
    for y in range(size[1]):
        t = y / size[1]
        color = tuple(round(a + (b-a)*t) for a,b in zip(c1,c2))
        draw.line((0,y,size[0],y), fill=color)
    sun_x = 680 if index % 2 else 280
    draw.ellipse((sun_x-58,140,sun_x+58,256), fill='#fff2ce')
    for layer, (color, level) in enumerate(((back,380),(front,515))):
        points = [(0,720)]
        for x in range(0,1001,40):
            y = level + math.sin(x/145+index*1.4+layer)*80 + math.cos(x/68+index)*25
            points.append((x,y))
        points.append((960,720))
        draw.polygon(points, fill=color)
    if index in (1,5):
        for i in range(12):
            y = 565 + i*10
            draw.line((80+i*19,y,800-i*12,y), fill=bottom, width=2)
    elif index == 3:
        for i in range(12):
            x = i*84
            h = 60+(i*37)%150
            draw.rectangle((x,590-h,x+54,720),fill=front)
            for yy in range(620-h,700,22):
                draw.rectangle((x+12,yy,x+17,yy+5),fill=bottom)
    else:
        for i in range(7):
            x = 55+i*149
            y = 620+int(math.sin(i)*40)
            draw.polygon([(x,y-90),(x-29,y),(x+29,y)],fill=front)
    raw = io.BytesIO()
    im.save(raw, 'PNG')
    return raw.getvalue()

def seed():
    if settings.environment != 'development':
        raise SystemExit('示例图仅允许用于开发环境')
    init_db()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == '__demo__'))
        if user is None:
            user = User(username='__demo__', password_hash=hash_password(secrets.token_urlsafe(48)), disabled=True)
            db.add(user)
            db.flush()
        if db.scalar(select(Picture.id).where(Picture.owner_id == user.id)):
            print('示例图已存在，无需重复生成')
            return
        public_space = db.scalar(select(Space).where(Space.owner_id.is_(None)))
        paths = []
        try:
            settings.storage_dir.mkdir(parents=True, exist_ok=True)
            for i, (title, *_, tag) in enumerate(PALETTES):
                full, thumb, ext, (w,h) = process_image(illustration(i))
                size = len(full)+len(thumb)
                r = db.execute(update(Storage).where(Storage.id==1, Storage.used_bytes+size<=settings.quota).values(used_bytes=Storage.used_bytes+size))
                if r.rowcount != 1:
                    raise RuntimeError('存储配额不足')
                p = Picture(id=str(uuid.uuid4()),title=title, description='原创示例插画，用于体验图库布局。可通过 clear-demo 清理。',
                            owner_id=user.id,space_id=public_space.id,width=w,height=h,byte_size=size,extension=ext)
                pair = image_paths(p.id,ext)
                paths.extend(pair)
                pair[0].write_bytes(full)
                pair[1].write_bytes(thumb)
                db.add(p)
                assign_tags(p,[tag,'示例'],db)
            db.commit()
        except Exception:
            db.rollback()
            remove_paths(paths)
            raise
    print('已生成 8 张示例插画；示例账户禁止登录')

def clear():
    if settings.environment != 'development':
        raise SystemExit('此命令仅允许用于开发环境')
    paths = []
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == '__demo__', User.disabled.is_(True)))
        if user:
            for p in db.scalars(select(Picture).where(Picture.owner_id==user.id)).all():
                paths.extend(image_paths(p.id,p.extension))
                db.execute(update(Storage).where(Storage.id==1).values(used_bytes=Storage.used_bytes-p.byte_size))
                db.delete(p)
            db.flush()
            db.delete(user)
            db.commit()
    remove_paths(paths)
    print('示例图已清理，其他用户的图片未受影响')
