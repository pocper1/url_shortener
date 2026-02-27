from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
import database.models as models
from database.session import get_db, SessionLocal
import schemas
from nanoid import generate
from datetime import datetime, timedelta

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

def create_short_code():
    return generate(size=7)

def record_click_background(url_id: int, user_agent: str, referer: str):
    db = SessionLocal()
    try:
        click_log = models.ClickAnalytics(
            url_id=url_id,
            user_agent=user_agent,
            referer=referer
        )
        db.add(click_log)
        db.commit()
    finally:
        db.close()

@router.post("/api/shorten", response_model=schemas.URLInfo)
@limiter.limit("100/minute")
def create_short_url(request: Request, url: schemas.URLCreate, db: Session = Depends(get_db)):
    short_code = create_short_code()
    
    while db.query(models.URL).filter(models.URL.short_code == short_code).first():
        short_code = create_short_code()
        
    expires_at = None
    if url.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=url.expires_in_days)
        
    db_url = models.URL(
        original_url=str(url.original_url),
        short_code=short_code,
        expires_at=expires_at
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return db_url

@router.get("/api/stats/{short_code}", response_model=schemas.URLStats)
def get_url_stats(short_code: str, db: Session = Depends(get_db)):
    db_url = db.query(models.URL).filter(models.URL.short_code == short_code).first()
    if not db_url:
        raise HTTPException(status_code=404, detail="URL not found")
    return db_url

@router.get("/{short_code}")
def redirect_to_url(short_code: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_url = db.query(models.URL).filter(models.URL.short_code == short_code).first()
    if not db_url:
        raise HTTPException(status_code=404, detail="URL not found")
        
    if db_url.expires_at and datetime.utcnow() > db_url.expires_at:
        raise HTTPException(status_code=410, detail="This URL has expired")
        
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    
    db_url.clicks += 1
    db.commit()
    
    background_tasks.add_task(record_click_background, db_url.id, user_agent, referer)
    
    return RedirectResponse(db_url.original_url, status_code=302)
