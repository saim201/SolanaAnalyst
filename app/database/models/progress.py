from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from datetime import datetime, timezone
from app.database.config import Base


class AnalysisProgress(Base):
    """Store real-time progress updates for analysis jobs"""
    __tablename__ = 'analysis_progress'

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), nullable=False, index=True)
    step = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # 'running', 'completed', 'error'
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('idx_progress_job_id', 'job_id'),
        Index('idx_progress_timestamp', 'timestamp'),
    )
