import hashlib
from sqlalchemy.orm import Session
from backend.app.models import Document

class DuplicateDetector:
    @staticmethod
    def calculate_hash(file_bytes: bytes) -> str:
        """
        Computes SHA-256 hash of file content.
        """
        sha256 = hashlib.sha256()
        sha256.update(file_bytes)
        return sha256.hexdigest()

    @staticmethod
    def check_duplicate(db: Session, file_hash: str, doc_type: str, extracted_data: dict, current_user_id: int) -> tuple[bool, str | None]:
        """
        Scans DB for identical file hashes or matching primary key fields
        (e.g., same Aadhaar Number or same PAN Number).
        Returns (is_duplicate, description_reason)
        """
        # 1. Exact match by file hash
        hash_match = db.query(Document).filter(
            Document.file_hash == file_hash,
            Document.user_id == current_user_id
        ).first()
        
        if hash_match:
            return True, f"Exact file duplicate of '{hash_match.filename}' processed on {hash_match.created_at.strftime('%Y-%m-%d %H:%M')}"

        # 2. Content key identification match
        if not extracted_data:
            return False, None

        # Check Aadhaar number duplicates
        if doc_type == "Aadhaar Card" and "aadhaar_number" in extracted_data:
            aadhaar_num = extracted_data["aadhaar_number"]
            # search for existing docs with same aadhaar_number
            matches = db.query(Document).filter(
                Document.doc_type == "Aadhaar Card",
                Document.user_id == current_user_id,
                Document.status == "processed"
            ).all()
            for m in matches:
                if m.extracted_data and m.extracted_data.get("aadhaar_number") == aadhaar_num:
                    return True, f"Content duplicate: Aadhaar number {aadhaar_num} already exists in '{m.filename}'"

        # Check PAN number duplicates
        elif doc_type == "PAN Card" and "pan_number" in extracted_data:
            pan_num = extracted_data["pan_number"]
            matches = db.query(Document).filter(
                Document.doc_type == "PAN Card",
                Document.user_id == current_user_id,
                Document.status == "processed"
            ).all()
            for m in matches:
                if m.extracted_data and m.extracted_data.get("pan_number") == pan_num:
                    return True, f"Content duplicate: PAN card {pan_num} already exists in '{m.filename}'"

        # Check Invoice duplicates
        elif doc_type == "Invoice" and "invoice_number" in extracted_data:
            inv_num = extracted_data["invoice_number"]
            matches = db.query(Document).filter(
                Document.doc_type == "Invoice",
                Document.user_id == current_user_id,
                Document.status == "processed"
            ).all()
            for m in matches:
                if m.extracted_data and m.extracted_data.get("invoice_number") == inv_num:
                    return True, f"Content duplicate: Invoice Number {inv_num} already exists in '{m.filename}'"

        return False, None

duplicate_detector = DuplicateDetector()
