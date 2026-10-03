import io
import warnings
from threading import BoundedSemaphore
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from app.core.config import settings

processing_slot = BoundedSemaphore(1)

def process_image(raw):
    if not processing_slot.acquire(timeout=15):
        raise HTTPException(429, '图片处理繁忙，请稍后重试')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise HTTPException(415, '仅支持 JPG、PNG 和 WebP')
                if source.width * source.height > settings.max_pixels:
                    raise HTTPException(413, '图片像素过多，请先缩小图片')
                source.seek(0)
                image = ImageOps.exif_transpose(source)
                alpha = image.mode in {'RGBA', 'LA'} or 'transparency' in source.info
                image = image.convert('RGBA' if alpha else 'RGB')
                image.info.clear()
                extension = 'png' if alpha else 'jpg'
                full = io.BytesIO()
                image.save(full, format='PNG' if alpha else 'JPEG', **({} if alpha else {'quality': 90, 'optimize': True}))
                dimensions = image.size
                image.thumbnail((720, 720), Image.Resampling.LANCZOS)
                thumb = io.BytesIO()
                image.save(thumb, format='WEBP', quality=82)
                return full.getvalue(), thumb.getvalue(), extension, dimensions
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(415, '图片无法读取或格式不安全') from None
    finally:
        processing_slot.release()

def image_paths(picture_id, extension):
    return settings.storage_dir / f'{picture_id}.{extension}', settings.storage_dir / f'{picture_id}.thumb.webp'

def remove_paths(paths):
    for path in paths:
        path.unlink(missing_ok=True)
