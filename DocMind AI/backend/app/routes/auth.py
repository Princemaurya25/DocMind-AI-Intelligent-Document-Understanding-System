from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from backend.app.database import get_db
from backend.app.models import User, AuditLog
from backend.app.schemas import UserCreate, UserResponse, Token
from backend.app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def log_audit_action(db: Session, user_id: int | None, action: str, details: str, request: Request):
    """
    Helper function to write an action to the AuditLog.
    """
    ip_addr = request.client.host if request.client else "unknown"
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_addr
    )
    db.add(audit_entry)
    db.commit()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email address already exists in the system."
        )
    
    hashed_pw = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        role=user_in.role if user_in.role in ["admin", "user"] else "user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Audit log registration
    log_audit_action(db, db_user.id, "SIGNUP", f"Registered new user: {db_user.email} with role: {db_user.role}", request)
    return db_user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Create an audit log for a failed login attempt if username existed
        user_id = user.id if user else None
        log_audit_action(db, user_id, "LOGIN_FAILED", f"Failed login attempt for email: {form_data.username}", request)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is deactivated")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # Audit log login
    log_audit_action(db, user.id, "LOGIN", f"User logged in successfully", request)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
