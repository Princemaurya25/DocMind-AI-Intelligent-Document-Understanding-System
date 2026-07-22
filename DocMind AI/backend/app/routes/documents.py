import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.database import get_db
from backend.app.models import User, Document, AuditLog
from backend.app.schemas import DocumentResponse
from backend.app.auth import get_current_user
from backend.app.config import settings
from backend.app.services.ai_pipeline import ai_service
from backend.app.services.duplicate_detector import duplicate_detector
from backend.app.services.summary_service import summary_service
from backend.app.utils.exporters import export_to_csv, export_to_excel, export_to_pdf

router = APIRouter(prefix="/documents", tags=["Documents"])

def log_audit_action(db: Session, user_id: int, action: str, details: str, request: Request):
    ip_addr = request.client.host if request.client else "unknown"
    db.add(AuditLog(user_id=user_id, action=action, details=details, ip_address=ip_addr))
    db.commit()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    lang: str = Query("en", regex="^(en|hi)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file type extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload PNG, JPG, JPEG, or PDF files."
        )
        
    # Read file bytes to calculate hash and search for duplicates
    file_bytes = await file.read()
    file_hash = duplicate_detector.calculate_hash(file_bytes)
    
    # Save file to upload directory
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)
        
    # Create preliminary pending database entry
    db_doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        doc_type="Analyzing...",
        extracted_data={},
        confidence_score=0.0,
        status="processing",
        file_hash=file_hash,
        is_fake=False,
        blur_score=0.0,
        summary=""
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    try:
        # Core AI Processing Pipeline
        ai_results = ai_service.process_document(file_path, file.filename)
        
        # Check duplicate content (near-duplicate) in the user's workspace
        is_dup, dup_reason = duplicate_detector.check_duplicate(
            db, file_hash, ai_results["doc_type"], ai_results["extracted_data"], current_user.id
        )
        if is_dup:
            # Update status to failed or processed but with duplicate warning
            db_doc.status = "processed"
            db_doc.doc_type = ai_results["doc_type"]
            db_doc.extracted_data = ai_results["extracted_data"]
            db_doc.confidence_score = ai_results["confidence_score"]
            db_doc.blur_score = ai_results["blur_score"]
            db_doc.is_fake = ai_results["is_fake"]
            db_doc.summary = f"WARNING: Duplicate document detected. {dup_reason}"
            db.commit()
            
            log_audit_action(db, current_user.id, "DOC_UPLOAD_DUPLICATE", f"Duplicate uploaded: {file.filename}. Reason: {dup_reason}", request)
            return db_doc
            
        # Generate summary (English or Hindi)
        summary = summary_service.generate_summary(
            ai_results["doc_type"],
            ai_results["extracted_data"],
            lang=lang
        )
        
        # Update database document values
        db_doc.doc_type = ai_results["doc_type"]
        db_doc.extracted_data = ai_results["extracted_data"]
        db_doc.confidence_score = ai_results["confidence_score"]
        db_doc.status = "processed"
        db_doc.is_fake = ai_results["is_fake"]
        db_doc.blur_score = ai_results["blur_score"]
        db_doc.summary = summary
        db.commit()
        db.refresh(db_doc)
        
        log_audit_action(db, current_user.id, "DOC_UPLOAD", f"Successfully processed document: {file.filename} as {db_doc.doc_type}", request)
        return db_doc
        
    except Exception as e:
        db_doc.status = "failed"
        db_doc.summary = f"AI pipeline processing failed: {str(e)}"
        db.commit()
        log_audit_action(db, current_user.id, "DOC_UPLOAD_FAILED", f"Processing failed for {file.filename}: {str(e)}", request)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    search: Optional[str] = None,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document)
    
    # Enforce Role-Based Access: standard users only view their own docs
    if current_user.role != "admin":
        query = query.filter(Document.user_id == current_user.id)
        
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if status:
        query = query.filter(Document.status == status)
        
    if search:
        query = query.filter(Document.filename.ilike(f"%{search}%"))
        
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Document.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Document.created_at <= end_dt)
        except ValueError:
            pass
            
    return query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # User ownership RBAC check
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
        
    return doc


@router.get("/{doc_id}/ocr-text")
def get_ocr_text(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Compile extracted data dictionary back to text representation for raw download
    text_content = f"DocMind AI OCR text dump\n"
    text_content += f"Document: {doc.filename}\n"
    text_content += f"Type: {doc.doc_type}\n"
    text_content += f"Confidence Score: {doc.confidence_score * 100:.2f}%\n"
    text_content += "---------------------------------------\n"
    if doc.extracted_data:
        for k, v in doc.extracted_data.items():
            text_content += f"{k}: {v}\n"
    else:
        text_content += "No readable OCR fields extracted.\n"
        
    # Return as plain text file stream
    return StreamingResponse(
        iter([text_content]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=ocr_{doc.id}.txt"}
    )


@router.get("/{doc_id}/export")
def export_document_data(
    doc_id: int,
    format: str = Query("pdf", regex="^(pdf|csv|xlsx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if doc.status != "processed":
        raise HTTPException(status_code=400, detail="Cannot export unprocessed document")

    extracted = doc.extracted_data or {}
    
    if format == "csv":
        stream = export_to_csv(extracted, doc.filename)
        media = "text/csv"
        ext = "csv"
    elif format == "xlsx":
        stream = export_to_excel(extracted, doc.filename)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        stream = export_to_pdf(extracted, doc.filename, doc.doc_type, doc.confidence_score, doc.summary or "")
        media = "application/pdf"
        ext = "pdf"
        
    filename = f"exported_{doc_id}.{ext}"
    return StreamingResponse(
        stream,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role != "admin" and doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")
        
    # Delete file from local storage
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
            
    db.delete(doc)
    db.commit()
    
    log_audit_action(db, current_user.id, "DOC_DELETE", f"Deleted document: {doc.filename}", request)
    return None


@router.get("/enhanced/{filename}")
def get_enhanced_image(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    # Serve enhanced image file from enhanced directory
    enhanced_path = os.path.join(settings.UPLOAD_DIR, "enhanced", filename)
    if not os.path.exists(enhanced_path):
         raise HTTPException(status_code=404, detail="Enhanced image file not found")
    return FileResponse(enhanced_path)


@router.get("/crops/{filename}")
def get_cropped_image(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    # Serve cropped face image files
    crop_path = os.path.join(settings.UPLOAD_DIR, "crops", filename)
    if not os.path.exists(crop_path):
         raise HTTPException(status_code=404, detail="Crop file not found")
    return FileResponse(crop_path)
