
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.database.models.progress import AnalysisProgress
from app.database.config import get_db_session


class ProgressStore:

    def add_progress(self, job_id: str, step: str, status: str, message: str):
        db = get_db_session()
        try:
            progress = AnalysisProgress(
                job_id=job_id,
                step=step,
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc)
            )
            db.add(progress)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error adding progress: {e}")
        finally:
            db.close()

    def get_progress(self, job_id: str) -> List[dict]:
        db = get_db_session()
        try:
            progress_records = db.query(AnalysisProgress).filter(
                AnalysisProgress.job_id == job_id
            ).order_by(AnalysisProgress.timestamp.asc()).all()

            return [
                {
                    "step": record.step,
                    "status": record.status,
                    "message": record.message,
                    "timestamp": record.timestamp.isoformat()
                }
                for record in progress_records
            ]
        except Exception as e:
            print(f"Error getting progress: {e}")
            return []
        finally:
            db.close()

    def clear_progress(self, job_id: str):
        db = get_db_session()
        try:
            db.query(AnalysisProgress).filter(
                AnalysisProgress.job_id == job_id
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error clearing progress: {e}")
        finally:
            db.close()

    def cleanup_old_progress(self, days: int = 1):
        db = get_db_session()
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            db.query(AnalysisProgress).filter(
                AnalysisProgress.timestamp < cutoff_date
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error cleaning up old progress: {e}")
        finally:
            db.close()


progress_store = ProgressStore()
