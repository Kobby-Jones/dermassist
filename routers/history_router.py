import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import AnalysisRecord, User
from schemas import ConditionScore, HistoryRecord, HistoryResponse

router = APIRouter(prefix="/api", tags=["History"])


@router.get("/history", response_model=HistoryResponse)
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current_user.id)
        .order_by(AnalysisRecord.created_at.desc())
        .all()
    )

    history = []
    for r in records:
        scores_raw = json.loads(r.all_scores) if r.all_scores else []
        history.append(
            HistoryRecord(
                id=r.id,
                predicted_condition=r.predicted_condition,
                confidence=r.confidence,
                all_scores=[ConditionScore(**s) for s in scores_raw],
                created_at=r.created_at,
            )
        )

    return HistoryResponse(records=history, total=len(history))


@router.delete("/history/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(AnalysisRecord)
        .filter(
            AnalysisRecord.id == record_id,
            AnalysisRecord.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    db.delete(record)
    db.commit()
