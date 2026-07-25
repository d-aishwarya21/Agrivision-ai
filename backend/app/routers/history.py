from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app import models

router = APIRouter(tags=["history"])


@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    records = (
        db.query(models.DiagnosticHistory)
        .filter(models.DiagnosticHistory.user_id == current_user.id)
        .order_by(models.DiagnosticHistory.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "predicted_disease": r.predicted_disease,
            "severity_score": r.severity_score,
            "humidity_at_time": r.humidity_at_time,
            "leaf_wetness_at_time": r.leaf_wetness_at_time,
            "is_physically_sound": r.is_physically_sound,
            "ai_explanation": r.ai_explanation,
            "created_at": r.created_at,
        }
        for r in records
    ]