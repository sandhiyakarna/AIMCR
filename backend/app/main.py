from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.seeder import seed_database

# Import routers
from app.api import auth, cases, evidence, analysis, timeline, copilot, reports, audit, users, acquisition, incidents

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create database tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed database with demonstration data
    db = SessionLocal()
    try:
        seed_database(db)
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()
        
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS Policy — origins loaded from config (env-configurable, no wildcard in production)
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(cases.router, prefix=f"{settings.API_V1_STR}/cases", tags=["Case Management"])
app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["Incident Management"])
app.include_router(evidence.router, prefix=f"{settings.API_V1_STR}/evidence", tags=["Evidence Management"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}/analyze", tags=["AI & Graph Analysis"])
app.include_router(timeline.router, prefix=f"{settings.API_V1_STR}/timeline", tags=["Timeline & Reconstruction"])
app.include_router(copilot.router, prefix=f"{settings.API_V1_STR}/copilot", tags=["AI Investigation Copilot"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/report", tags=["PDF Reporting"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Audit Log Trail"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["User Management"])
app.include_router(acquisition.router, prefix=f"{settings.API_V1_STR}/acquisition", tags=["Evidence Acquisition"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_prefix": settings.API_V1_STR
    }
