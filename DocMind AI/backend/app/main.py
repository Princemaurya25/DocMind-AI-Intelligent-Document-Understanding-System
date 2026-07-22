import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User
from backend.app.auth import get_password_hash
from backend.app.routes import auth, documents, analytics, audit

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent Document Understanding System REST APIs",
    version="1.0.0"
)

# CORS Configuration for local frontend development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under standard prefix /api
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(audit.router, prefix="/api")

# Serve upload directories statically so that UI can render images & cropped outputs
# Note: In production this would be handled by Nginx or S3
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "ai_fallback_mode": settings.AI_FALLBACK_MODE
    }

# Database table creation and seed data initialization on startup
@app.on_event("startup")
def on_startup():
    # Create tables in the target DB (Postgres or SQLite)
    Base.metadata.create_all(bind=engine)
    
    # Seed Database
    db = SessionLocal()
    try:
        # 1. Seed Admin User
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not admin:
            hashed_admin_pw = get_password_hash(settings.ADMIN_PASSWORD)
            new_admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=hashed_admin_pw,
                full_name="System Administrator",
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            print(f"[*] Seeded Administrator account: {settings.ADMIN_EMAIL}")

        # 2. Seed Standard Demo User
        demo_user_email = "user@docmind.ai"
        demo_user_pw = "User@DocMind123"
        demo_user = db.query(User).filter(User.email == demo_user_email).first()
        if not demo_user:
            hashed_user_pw = get_password_hash(demo_user_pw)
            new_user = User(
                email=demo_user_email,
                hashed_password=hashed_user_pw,
                full_name="Rajesh Kumar",
                role="user"
            )
            db.add(new_user)
            db.commit()
            print(f"[*] Seeded Standard Demo account: {demo_user_email}")
            
    except Exception as e:
        print(f"[-] Startup Database seeding failed: {e}")
    finally:
        db.close()
