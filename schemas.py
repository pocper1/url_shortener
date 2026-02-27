from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class URLBase(BaseModel):
    original_url: HttpUrl

class URLCreate(URLBase):
    expires_in_days: Optional[int] = None

class URLInfo(URLBase):
    id: int
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime]
    clicks: int

    class Config:
        orm_mode = True

class ClickAnalyticsBase(BaseModel):
    id: int
    clicked_at: datetime
    user_agent: Optional[str]
    referer: Optional[str]
    
    class Config:
        orm_mode = True

class URLStats(URLInfo):
    analytics: list[ClickAnalyticsBase] = []
