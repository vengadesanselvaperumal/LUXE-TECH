import io
import re
from typing import Tuple
from fastapi import HTTPException, UploadFile, status
from PIL import Image

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def sanitize_filename(filename: str) -> str:
    # Strip paths
    clean = filename.replace("\\", "/").split("/")[-1]
    # Keep alphanumeric, dot, hyphen, underscore
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", clean)
    return clean or "upload.jpg"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def validate_image_upload(file: UploadFile) -> Tuple[bytes, int, int, str]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    safe_name = sanitize_filename(file.filename)
    extension = "." + safe_name.split(".")[-1].lower() if "." in safe_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{extension}'. Allowed: {list(ALLOWED_EXTENSIONS)}"
        )

    content_type = file.content_type or ""
    if content_type and content_type.lower() not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{content_type}'. Must be JPEG, PNG, or WebP."
        )

    # Bounded chunked reading to prevent memory exhaustion DoS.
    # Note: Application-level bounded chunk reads guard server memory, but reverse
    # proxies (e.g. Nginx client_max_body_size, cloud load balancers) are required as
    # the outer perimeter to reject oversized requests before they reach Python ASGI workers.
    chunk_size = 64 * 1024  # 64 KB
    total_bytes = 0
    chunks = []
    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_IMAGE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"File exceeds maximum size limit of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB."
                )
            chunks.append(chunk)
    finally:
        await file.close()

    content = b"".join(chunks)

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # Validate image format and dimensions via Pillow
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()  # Verify integrity
        # Reopen to read dimensions since verify closes certain metadata
        image = Image.open(io.BytesIO(content))
        width, height = image.size
        if width < 10 or height < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image dimensions too small (minimum 10x10)."
            )
        if width > 10000 or height > 10000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image dimensions too large (maximum 10,000x10,000)."
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted image file: {str(exc)}"
        )

    return content, width, height, safe_name
