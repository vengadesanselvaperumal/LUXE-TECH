import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import ImageRecord, Trend, get_db
from app.schemas.common import ApiResponse
from app.services.gemini_service import gemini_service
from app.services.supabase_service import LOCAL_STORAGE_DIR, PUBLIC_BUCKETS, supabase_service
from app.services.vision_engine import vision_engine
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import PRIVILEGED_ROLES, get_current_user, get_optional_user
from app.utils.validation import validate_image_upload

router = APIRouter(prefix="/images", tags=["images"])


@router.post(
    "/analyze",
    response_model=ApiResponse[Dict[str, Any]],
    dependencies=[Depends(rate_limit_dependency(max_requests=10, window_seconds=60, scope="image_analyze"))]
)
async def analyze_image(
    file: UploadFile = File(...),
    trend_id: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validation (file size, format, dimensions, executable prevention)
    content, width, height, safe_filename = await validate_image_upload(file)

    # 2. Local OpenCV Feature Extraction (Color extraction with K-Means, contrast, brightness, edge density)
    vision_features = vision_engine.extract_features_from_bytes(content)

    # 3. Gemini Vision analysis (or local fashion interpretation)
    mime_type = file.content_type or "image/jpeg"
    ai_analysis = await gemini_service.analyze_image(
        image_bytes=content,
        mime_type=mime_type,
        vision_features=vision_features
    )

    # 4. Upload image to storage
    user_id = current_user.get("id", "anonymous")
    user_role = current_user.get("role", "user")

    # Catalog imagery associated with shared trends by privileged users routes to public trend-images;
    # Personal exploratory uploads (including unprivileged uploads or uploads without valid trend) route to user-uploads.
    matched_trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first() if trend_id else None
    is_catalog_upload = bool(matched_trend) and (user_role in PRIVILEGED_ROLES)
    if is_catalog_upload and matched_trend:
        bucket = "trend-images"
        storage_path = f"trends/{matched_trend.slug}/{uuid.uuid4()}_{safe_filename}"
        persisted_trend_id = matched_trend.id
    else:
        bucket = "user-uploads"
        storage_path = f"{user_id}/{uuid.uuid4()}_{safe_filename}"
        persisted_trend_id = None

    file_url = await supabase_service.upload_file(
        bucket=bucket,
        path=storage_path,
        content=content,
        content_type=mime_type
    )

    # 5. Persist image record
    # Note: image_records table does not yet have a dedicated user_id column in the canonical schema proposal;
    # user identity is preserved in storage_path without violating existing schema parity.
    img_record = ImageRecord(
        id=str(uuid.uuid4()),
        trend_id=persisted_trend_id,
        storage_path=storage_path,
        public_url=file_url,
        width=width,
        height=height,
        dominant_colors_json=json.dumps(vision_features.get("dominant_colors", [])),
        contrast=vision_features.get("contrast", 0.0),
        brightness=vision_features.get("brightness", 0.0),
        saturation=vision_features.get("saturation", 0.0),
        edge_density=vision_features.get("edge_density", 0.0),
        data_status=ai_analysis.get("data_status", "demo")
    )
    db.add(img_record)
    db.commit()

    return ApiResponse.ok({
        "image_id": img_record.id,
        "public_url": file_url,
        "signed_url": file_url if bucket == "user-uploads" else None,
        "bucket": bucket,
        "storage_path": storage_path,
        "vision_metrics": {
            "width": width,
            "height": height,
            "contrast": vision_features.get("contrast"),
            "brightness": vision_features.get("brightness"),
            "saturation": vision_features.get("saturation"),
            "edge_density": vision_features.get("edge_density"),
            "dominant_colors": vision_features.get("dominant_colors", []),
            "data_status": "derived",
        },
        "image_analysis": ai_analysis.get("image_analysis", {}),
        "trend_interpretation": ai_analysis.get("trend_interpretation", ""),
        "possible_categories": ai_analysis.get("possible_categories", []),
        "data_status": ai_analysis.get("data_status", "demo"),
        "storage_backend": "supabase" if not file_url.startswith("/api/images/local/") else "local",
    })


@router.get("/local/{bucket}/{filepath:path}")
async def serve_local_image(
    bucket: str,
    filepath: str,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    storage_root = LOCAL_STORAGE_DIR.resolve()
    bucket_root = (storage_root / bucket).resolve()
    file_path = (bucket_root / filepath).resolve()

    if not file_path.is_relative_to(bucket_root):
        raise HTTPException(status_code=400, detail="Invalid image path.")

    # Access control: Private buckets require authentication and ownership or privileged role
    if bucket not in PUBLIC_BUCKETS:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access private assets."
            )
        user_id = user.get("id")
        user_role = user.get("role", "user")
        normalized_rel_path = str(file_path.relative_to(bucket_root)).replace("\\", "/")
        if user_role not in PRIVILEGED_ROLES and not normalized_rel_path.startswith(f"{user_id}/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this asset."
            )

    if not file_path.exists():
        alt_root = (Path("uploads") / bucket / filepath).resolve()
        alt_backend = (Path("backend/uploads") / bucket / filepath).resolve()
        if alt_root.exists() and alt_root.is_relative_to(Path("uploads").resolve()):
            file_path = alt_root
        elif alt_backend.exists() and alt_backend.is_relative_to(Path("backend/uploads").resolve()):
            file_path = alt_backend
        else:
            raise HTTPException(status_code=404, detail="Image file not found.")

    return FileResponse(path=file_path)


@router.get("", response_model=ApiResponse[List[Dict[str, Any]]])
async def list_images(
    trend_id: Optional[str] = Query(None, description="Filter catalog images by trend ID or slug"),
    mine: bool = Query(False, description="Filter to current user's uploaded images"),
    limit: int = Query(50, ge=1, le=100),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    query = db.query(ImageRecord)
    if trend_id:
        trend = db.query(Trend).filter((Trend.id == trend_id) | (Trend.slug == trend_id)).first()
        if not trend:
            return ApiResponse.fail(code="TREND_NOT_FOUND", message=f"Trend '{trend_id}' not found.", status_code=404)
        query = query.filter(ImageRecord.trend_id == trend.id)
    elif mine:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view personal image uploads."
            )
        user_id = user.get("id")
        query = query.filter(ImageRecord.storage_path.like(f"{user_id}/%"))
    else:
        # Default behavior:
        if user and user.get("role") in PRIVILEGED_ROLES:
            pass  # Privileged users can view all images
        elif user:
            user_id = user.get("id")
            query = query.filter(
                (ImageRecord.trend_id.isnot(None)) | (ImageRecord.storage_path.like(f"{user_id}/%"))
            )
        else:
            # Unauthenticated: public catalog images only
            query = query.filter(ImageRecord.trend_id.isnot(None))

    records = query.order_by(ImageRecord.created_at.desc()).limit(limit).all()

    items = []
    for img in records:
        url = img.public_url
        is_private = not img.trend_id and not img.storage_path.startswith("trends/")
        if is_private and user and supabase_service.is_configured and not url.startswith("/api/images/local/"):
            url = await supabase_service.create_signed_url("user-uploads", img.storage_path)
        items.append({
            "id": img.id,
            "trend_id": img.trend_id,
            "storage_path": img.storage_path,
            "url": url,
            "width": img.width,
            "height": img.height,
            "dominant_colors": img.dominant_colors,
            "contrast": img.contrast,
            "brightness": img.brightness,
            "saturation": img.saturation,
            "edge_density": img.edge_density,
            "data_status": img.data_status,
            "created_at": img.created_at.isoformat() if img.created_at else None,
        })

    return ApiResponse.ok(items)


@router.get("/{image_id}", response_model=ApiResponse[Dict[str, Any]])
async def get_image(
    image_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    img = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image record not found.")

    is_catalog = bool(img.trend_id) or img.storage_path.startswith("trends/")
    if not is_catalog:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view private image."
            )
        user_id = user.get("id")
        user_role = user.get("role", "user")
        if user_role not in PRIVILEGED_ROLES and not img.storage_path.startswith(f"{user_id}/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this image."
            )

    url = img.public_url
    if not is_catalog and supabase_service.is_configured and not url.startswith("/api/images/local/"):
        url = await supabase_service.create_signed_url("user-uploads", img.storage_path)

    return ApiResponse.ok({
        "id": img.id,
        "trend_id": img.trend_id,
        "storage_path": img.storage_path,
        "url": url,
        "width": img.width,
        "height": img.height,
        "dominant_colors": img.dominant_colors,
        "contrast": img.contrast,
        "brightness": img.brightness,
        "saturation": img.saturation,
        "edge_density": img.edge_density,
        "data_status": img.data_status,
        "created_at": img.created_at.isoformat() if img.created_at else None,
    })


@router.delete("/{image_id}", response_model=ApiResponse[Dict[str, Any]])
def delete_image(
    image_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    img = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image record not found.")

    is_catalog = bool(img.trend_id) or img.storage_path.startswith("trends/")
    user_id = current_user.get("id")
    user_role = current_user.get("role", "user")

    if is_catalog and user_role not in PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="Privileged role required to delete catalog imagery.")
    elif not is_catalog and user_role not in PRIVILEGED_ROLES and not img.storage_path.startswith(f"{user_id}/"):
        raise HTTPException(status_code=403, detail="Access denied: You do not own this image.")

    db.delete(img)
    db.commit()
    return ApiResponse.ok({"deleted": True, "id": image_id})
