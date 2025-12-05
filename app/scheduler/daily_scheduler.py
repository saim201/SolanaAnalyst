"""
Daily scheduler for automatic data refresh
Uses APScheduler to run cron job at 00:00 UTC
"""
import sys
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.refresh_manager import RefreshManager

scheduler = BackgroundScheduler()


@scheduler.scheduled_job('cron', hour=0, minute=0, id='daily_data_refresh')
def scheduled_daily_refresh():
    print(f"\n⏰ SCHEDULED DAILY REFRESH TRIGGERED")
    print(f"Timestamp: {datetime.now().isoformat()}")
    try:
        RefreshManager.refresh_all_data(days=1)
        print("✅ Scheduled refresh completed successfully")
    except Exception as e:
        print(f"❌ Scheduled refresh failed: {str(e)}")


def start_scheduler():
    try:
        if not scheduler.running:
            scheduler.start()
            print("✅ Daily scheduler started (runs at 00:00 UTC)")
            return True
    except Exception as e:
        print(f"❌ Failed to start scheduler: {str(e)}")
        return False


def stop_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown()
            print("✅ Daily scheduler stopped")
            return True
    except Exception as e:
        print(f"❌ Failed to stop scheduler: {str(e)}")
        return False
