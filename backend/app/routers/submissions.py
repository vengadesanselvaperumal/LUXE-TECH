import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import TrendSubmission, get_db
from app.schemas.common import ApiResponse
from app.services.submission_service import normalize_social_source_url
from app.services.supabase_service import supabase_service
from app.utils.rate_limit import rate_limit_dependency
from app.utils.security import get_current_user, get_privileged_user
from app.utils.validation import validate_image_upload

router = APIRouter(prefix="/submissions", tags=["submissions"])


class ReviewSubmissionRequest(BaseModel):
    status: str = Field(pattern="^(reviewed|accepted|rejected)$")
    review_note: Optional[str] = Field(None, max_length=2000)


def _submission_response(submission: TrendSubmission, image_url: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": submission.id,
        "platform": submission.platform,
        "source_url": submission.source_url,
        "observation": submission.observation,
        "product_type": submission.product_type,
        "category": submission.category,
        "color": submission.color,
        "material": submission.material,
        "silhouette": submission.silhouette,
        "observed_at": submission.observed_at.isoformat() if submission.observed_at else None,
        "explanation": submission.explanation,
        "image_url": image_url,
        "status": submission.status,
        "review_note": submission.review_note,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "evidence_type": "user_submitted_observation",
        "verification_state": "user_submitted_unverified",
        "limitations": [
            "User-reported source; the linked post is not fetched or independently verified.",
            "Submission volume does not measure consumer demand, sales, search volume, or reach.",
        ],
    }


async def _private_image_url(submission: TrendSubmission) -> Optional[str]:
    if not submission.image_storage_path:
        return None
    if supabase_service.is_configured:
        return await supabase_service.create_signed_url("user-uploads", submission.image_storage_path)
    return f"/api/images/local/user-uploads/{submission.image_storage_path}"


@router.post(
    "",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency(max_requests=5, window_seconds=60, scope="trend_submission"))],
)
async def create_submission(
    platform: str = Form(..., min_length=1, max_length=32),
    source_url: str = Form(..., min_length=1, max_length=2048),
    observation: str = Form(..., min_length=5, max_length=500),
    product_type: str = Form(..., min_length=1, max_length=120),
    category: Optional[str] = Form(None, max_length=80),
    color: Optional[str] = Form(None, max_length=80),
    material: Optional[str] = Form(None, max_length=120),
    silhouette: Optional[str] = Form(None, max_length=120),
    observed_at: Optional[str] = Form(None, max_length=64),
    explanation: Optional[str] = Form(None, max_length=2000),
    rights_confirmed: bool = Form(False),
    file: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    platform = platform.strip().lower()
    try:
        normalized_url = normalize_social_source_url(platform, source_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if not observation.strip() or not product_type.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Observation and product type are required.")

    duplicate = db.query(TrendSubmission).filter(
        TrendSubmission.normalized_source_url == normalized_url
    ).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This source post has already been submitted.")

    observed_datetime = None
    if observed_at:
        try:
            observed_datetime = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Enter a valid observation date.") from exc
        if observed_datetime.tzinfo is None:
            observed_datetime = observed_datetime.replace(tzinfo=timezone.utc)

    image_path = None
    image_content = None
    image_content_type = None
    if file is not None:
        if not rights_confirmed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Confirm that you have the rights to submit the uploaded image.",
            )
        image_content, _, _, safe_filename = await validate_image_upload(file)
        extension = safe_filename.rsplit(".", 1)[-1].lower()
        image_path = f"{current_user['id']}/submissions/{uuid.uuid4()}.{extension}"
        image_content_type = file.content_type or "application/octet-stream"

    submission = TrendSubmission(
        id=str(uuid.uuid4()),
        user_id=current_user["id"],
        platform=platform,
        source_url=source_url.strip(),
        normalized_source_url=normalized_url,
        observation=observation.strip(),
        product_type=product_type.strip(),
        category=category.strip() or None if category else None,
        color=color.strip() or None if color else None,
        material=material.strip() or None if material else None,
        silhouette=silhouette.strip() or None if silhouette else None,
        observed_at=observed_datetime,
        explanation=explanation.strip() or None if explanation else None,
        image_storage_path=image_path,
        rights_confirmed=rights_confirmed,
        status="pending",
    )
    db.add(submission)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This source post has already been submitted.") from exc
    try:
        if image_path and image_content is not None:
            await supabase_service.upload_file(
                bucket="user-uploads",
                path=image_path,
                content=image_content,
                content_type=image_content_type or "application/octet-stream",
            )
        db.commit()
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        if image_path:
            try:
                await supabase_service.delete_file("user-uploads", image_path)
            except RuntimeError as cleanup_error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Duplicate submission was rejected, but uploaded image cleanup failed.",
                ) from cleanup_error
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This source post has already been submitted.") from exc
    db.refresh(submission)
    return ApiResponse.ok(_submission_response(submission))


@router.get("/mine", response_model=ApiResponse[List[Dict[str, Any]]])
async def list_my_submissions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submissions = db.query(TrendSubmission).filter(
        TrendSubmission.user_id == current_user["id"]
    ).order_by(TrendSubmission.submitted_at.desc()).limit(100).all()
    results = []
    for submission in submissions:
        results.append(_submission_response(submission, await _private_image_url(submission)))
    return ApiResponse.ok(results)


@router.patch("/{submission_id}/review", response_model=ApiResponse[Dict[str, Any]])
def review_submission(
    submission_id: str,
    request: ReviewSubmissionRequest,
    _reviewer: Dict[str, Any] = Depends(get_privileged_user),
    db: Session = Depends(get_db),
):
    submission = db.query(TrendSubmission).filter(TrendSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    submission.status = request.status
    submission.review_note = request.review_note.strip() if request.review_note else None
    db.commit()
    db.refresh(submission)
    return ApiResponse.ok(_submission_response(submission))
