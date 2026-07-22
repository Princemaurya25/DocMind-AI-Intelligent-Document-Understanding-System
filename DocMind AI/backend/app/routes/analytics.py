from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import Counter
import datetime

from backend.app.database import get_db
from backend.app.models import User, Document
from backend.app.schemas import StatsDashboardResponse, MonthlyVolume
from backend.app.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/stats", response_model=StatsDashboardResponse)
def get_dashboard_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document)
    
    # Non-admin users can only view statistics for their own uploads
    if current_user.role != "admin":
        query = query.filter(Document.user_id == current_user.id)
        
    all_docs = query.all()
    
    total = len(all_docs)
    processed = sum(1 for d in all_docs if d.status == "processed")
    failed = sum(1 for d in all_docs if d.status == "failed")
    
    # Calculate Average Confidence
    processed_confs = [d.confidence_score for d in all_docs if d.status == "processed"]
    avg_conf = sum(processed_confs) / len(processed_confs) if processed_confs else 0.0
    
    # Counting Flags
    fake_count = sum(1 for d in all_docs if d.is_fake)
    # Threshold for blur warning: Laplacians variance < 100
    blur_count = sum(1 for d in all_docs if d.blur_score > 0 and d.blur_score < 100.0)
    
    # Document Type Distribution
    type_counts = Counter(d.doc_type for d in all_docs)
    
    # Standard document types we want to represent in the chart
    standard_types = [
        "Aadhaar Card", "PAN Card", "Passport", "Driving License", 
        "Bank Statement", "Salary Slip", "Invoice", "Utility Bill", "Cheque"
    ]
    distribution = {t: type_counts.get(t, 0) for t in standard_types}
    # Add any other dynamic ones
    for k, v in type_counts.items():
        if k not in distribution:
            distribution[k] = v

    # Processing History over the last 6 months
    history = []
    today = datetime.date.today()
    for i in range(5, -1, -1):
        # Subtracting months
        month_offset = today.month - i
        year_offset = today.year
        if month_offset <= 0:
            month_offset += 12
            year_offset -= 1
            
        month_start = datetime.datetime(year_offset, month_offset, 1)
        if month_offset == 12:
            month_end = datetime.datetime(year_offset + 1, 1, 1)
        else:
            month_end = datetime.datetime(year_offset, month_offset + 1, 1)
            
        count = sum(1 for d in all_docs if month_start <= d.created_at < month_end)
        month_label = month_start.strftime("%b %Y")
        history.append(MonthlyVolume(label=month_label, count=count))

    return {
        "total_documents": total,
        "processed_documents": processed,
        "failed_documents": failed,
        "average_confidence": avg_conf,
        "fake_count": fake_count,
        "blur_count": blur_count,
        "doc_type_distribution": distribution,
        "processing_history": history
    }
