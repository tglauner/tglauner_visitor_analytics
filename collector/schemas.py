from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    ts: str
    uid: str
    session_id: str
    event_name: str
    path: Optional[str] = None
    title: Optional[str] = None
    referrer: Optional[str] = None
    href: Optional[str] = None
    target_domain: Optional[str] = None
    target_type: Optional[str] = None
    button_id: Optional[str] = None
    course_slug: Optional[str] = None
    coupon: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    viewport: Optional[Dict[str, Any]] = None
    percent: Optional[int] = None
    time_on_page_ms: Optional[int] = None
    app_id: Optional[str] = None
    page_url: Optional[str] = None
    auth_state: Optional[Literal["anonymous", "authenticated"]] = None


class Batch(BaseModel):
    events: List[Event] = Field(default_factory=list)
