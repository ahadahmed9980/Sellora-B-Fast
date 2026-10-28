import asyncio
import io
import warnings
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET


# cloudinary config
cloudinary.config(
    ccloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)
max_file_size = 5* 1024 * 1024
max_image_pixel = 25_000_000
max_dimension = 1200

allowed_format = { 'JPEG','PNG', 'WEBP'}
allowed_content_type = {
    'image/jpeg',
    'image/png',
    'image/webp'
}

def process_and_upload(image_bytes:bytes)->dict:
    with warnings.catch_warnings():
        warnings.simplefilter(
            'error',
            Image.DecompressionBombWarning
        )
        # verify file:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.format not in allowed_format:
                raise HTTPException(status_code= 400, detail='Unsported image format')

            if image.width * image.height > max_image_pixel:
                raise HTTPException(status_code=400 , detail='Image dimession are too large')
            image.verify()

            # now reopen and process the image after verify it 
            






