import io

import cloudinary
import cloudinary.uploader
from PIL import Image
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
MAX_FILE_SIZE = 5 * 1024 * 1024
max_image_pixel = 25_000_000
MAX_DIMENSION = 1200

allowed_format = {"JPEG", "PNG", "WEBP"}
allowed_content_type = {"image/jpeg", "image/png", "image/webp"}


def _process_and_upload(image_bytes: bytes) -> dict:
    """Image ko resize, compress aur upload karta hai."""
    try:
        # 1. Image open karein
        image = Image.open(io.BytesIO(image_bytes))

        # 2. Resize karein agar 1200px se badi ho
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

        # 3. Format set karein (PNG transparency support ke sath)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        # 4. WebP mein compress karein
        output = io.BytesIO()
        image.save(output, format="WEBP", quality=80)
        output.seek(0)

        # 5. Cloudinary par upload karein
        result = cloudinary.uploader.upload(
            output,
            folder="sellora/products",
            resource_type="image",
        )

        return {
            "image_url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image process ya upload nahi ho saki.",
        )


async def upload_image(image: UploadFile) -> dict:
    """FastAPI endpoint se aane wali image ko check aur handle karta hai."""
    # 1. Type check
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Sirf image files allowed hain.")

    # 2. File read karein
    image_bytes = await image.read()

    # 3. Size check (5 MB limit)
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail="Image 5 MB se bari nahi honi chahiye."
        )

    # 4. Background thread mein process aur upload karein
    return await run_in_threadpool(_process_and_upload, image_bytes)
