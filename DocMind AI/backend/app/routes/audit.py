from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from backend.app.database import get_db
from backend.app.models import User, AuditLog
from backend.app.schemas import AuditLogResponse
from backend.app.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit Logs"])

@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns audit logs. Standard users see their own logs; Administrators see all.
    """
    if current_user.role == "admin":
        # Load user relationships to resolve email in the response
        logs = db.query(AuditLog).options(joinedload(AuditLog.user))\
                 .order_by(AuditLog.timestamp.desc()).limit(limit).all()
    else:
        logs = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)\
                 .order_by(AuditLog.timestamp.desc()).limit(limit).all()
                 
    # Map to schemas resolving emails
    response_logs = []
    for log in logs:
        email = log.user.email if log.user else "System / Anonymous"
        response_logs.append({
            "id": log.id,
            "user_id": log.user_id,
            "user_email": email,
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp
        })
        
    return response_logs
