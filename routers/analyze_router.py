import imghdr
import json
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from model_service import classify
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
    detected = imghdr.what(None, h=data)
    return MAGIC_TYPE_MAP.get(detected or "", None)


# ── Stats schema ──────────────────────────────────────────────────────────────

class ConditionBreakdown(BaseModel):
    condition: str
    count: int


class StatsResponse(BaseModel):
    total_scans: int
    this_month: int
    avg_confidence: float
    breakdown: List[ConditionBreakdown]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    from sqlalchemy import func

    records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current_user.id)
        .all()
    )

    total = len(records)
    now = datetime.now(timezone.utc)
    this_month = sum(
        1 for r in records
        if r.created_at.year == now.year and r.created_at.month == now.month
    )
    avg_conf = (
        round(sum(r.confidence for r in records) / total, 4) if total > 0 else 0.0
    )

    # Count per condition
    counts: dict[str, int] = {}
    for r in records:
        counts[r.predicted_condition] = counts.get(r.predicted_condition, 0) + 1

    breakdown = [
        ConditionBreakdown(condition=k, count=v)
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
    ]

    return StatsResponse(
        total_scans=total,
        this_month=this_month,
        avg_confidence=avg_conf,
        breakdown=breakdown,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_bytes = await file.read()

    if len(image_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be smaller than 10 MB.",
        )

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

    result = classify(image_bytes)

    record = AnalysisRecord(
        user_id=current_user.id,
        predicted_condition=result["predicted_condition"],
        confidence=result["confidence"],
        all_scores=result["all_scores_json"],
    )
    db.add(record)
    db.commit()

    return AnalyzeResponse(
        predicted_condition=result["predicted_condition"],
        confidence=result["confidence"],
        all_scores=[ConditionScore(**s) for s in result["all_scores"]],
        analysis_time_seconds=result["analysis_time_seconds"],
        description=result["description"],
        disclaimer=result["disclaimer"],
    )
