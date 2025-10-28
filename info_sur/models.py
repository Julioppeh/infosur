"""SQLAlchemy models for Info Sur."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.mutable import MutableDict

from .database import Base


def utc_now():
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class Article(Base):
    __tablename__ = "articles"

    id: int = Column(Integer, primary_key=True)
    slug: str = Column(String(255), nullable=False)
    timestamp: str = Column(String(14), nullable=False, index=True)
    prompt: str = Column(Text, nullable=False)
    satire_level: int = Column(Integer, nullable=False, default=50)
    image_prompt_primary: Optional[str] = Column(Text, nullable=True)
    image_prompt_secondary: Optional[str] = Column(Text, nullable=True)
    article_data: Dict[str, Any] = Column(MutableDict.as_mutable(JSON), nullable=False)
    image_data: Dict[str, Any] = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    created_at: datetime = Column(DateTime, default=utc_now, nullable=False)
    updated_at: datetime = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class TemplateRevision(Base):
    __tablename__ = "template_revisions"

    id: int = Column(Integer, primary_key=True)
    template_html: str = Column(Text, nullable=False)
    created_at: datetime = Column(DateTime, default=utc_now, nullable=False)

    @classmethod
    def latest(cls, session) -> "TemplateRevision":
        return session.query(cls).order_by(cls.created_at.desc()).first()
