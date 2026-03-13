import imghdr
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth import get_current_user
from clip_service import classify
from database import get_db
from models import AnalysisRecord, User
from schemas import AnalyzeResponse, ConditionScore

router = APIRouter(prefix="/api", tags=["Analysis"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/heif", "image/webp", "image/heic"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

MAGIC_TYPE_MAP = {
    "png":  "image/png",
    "jpeg": "image/jpeg",
    "jpg":  "image/jpeg",
    "webp": "image/webp",
    "heif": "image/heif",
}


def _sniff_content_type(data: bytes) -> str | None:
    """Detect image type from magic bytes using imghdr."""
    detected = imghdr.what(None, h=data)
    return MAGIC_TYPE_MAP.get(detected or "", None)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Read image bytes first so we can sniff type if needed
    image_bytes = await file.read()

    if len(image_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be smaller than 10 MB.",
        )

    # Determine content type — fall back to magic-byte sniffing for octet-stream
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        sniffed = _sniff_content_type(image_bytes)
        if sniffed:
            content_type = sniffed
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported file type: {file.content_type}. Use JPEG, PNG, HEIF or WebP.",
            )

    # Run CLIP classification
    result = classify(image_bytes)

    # Persist anonymised record (no raw image stored)
    record = AnalysisRecord(
        user_id=current_user.id,
        predicted_condition=result["predicted_condition"],
        confidence=result["confidence"],
        all_scores=result["all_scores_json"],
    )
    db.add(record)
    db.commit()

    # Build response
    return AnalyzeResponse(
        predicted_condition=result["predicted_condition"],
        confidence=result["confidence"],
        all_scores=[ConditionScore(**s) for s in result["all_scores"]],
        analysis_time_seconds=result["analysis_time_seconds"],
        disclaimer=result["disclaimer"],
    )