from typing import Callable, Optional
from datetime import datetime


class ProgressTracker:
    """
    Progress tracker for real-time analysis pipeline monitoring.
    Tracks analysis pipeline progress and emits status updates via callback.
    Works with PostgreSQL-backed progress storage for Lambda compatibility.
    """

    def __init__(self, callback: Optional[Callable[[str, str, str], None]] = None):
        """
        Initialize progress tracker.

        Args:
            callback: Function to call when progress updates (step, status, message)
        """
        self.callback = callback
        self.steps = [
            "refresh_data",
            "technical_agent",
            "sentiment_agent",
            "reflection_agent",
            "trader_agent",
            "complete"
        ]
        self.current_step = 0
        self.start_time = datetime.now()

    def emit(self, step: str, status: str, message: str):
        """
        Emit a progress update.

        Args:
            step: Current step name
            status: Status (started, completed, error)
            message: Human-readable message
        """
        if self.callback:
            self.callback(step, status, message)

    def start_refresh(self):
        """Start data refresh step"""
        self.emit("refresh_data", "started", "Fetching latest market data from Binance and news sources...")

    def complete_refresh(self):
        """Complete data refresh step"""
        self.emit("refresh_data", "completed", "Market data refreshed successfully")

    def start_technical(self):
        """Start technical agent"""
        self.emit("technical_agent", "started", "Running Technical Analysis Agent...")

    def complete_technical(self):
        """Complete technical agent"""
        self.emit("technical_agent", "completed", "Technical analysis completed")

    def start_sentiment(self):
        """Start sentiment agent"""
        self.emit("sentiment_agent", "started", "Running Sentiment Analysis Agent (CFGI + News)...")

    def complete_sentiment(self):
        """Complete sentiment agent"""
        self.emit("sentiment_agent", "completed", "Sentiment analysis completed")

    # Backward compatibility aliases
    def start_news(self):
        """Deprecated: Use start_sentiment() instead"""
        self.start_sentiment()

    def complete_news(self):
        """Deprecated: Use complete_sentiment() instead"""
        self.complete_sentiment()

    def start_reflection(self):
        """Start reflection agent"""
        self.emit("reflection_agent", "started", "Running Reflection Agent...")

    def complete_reflection(self):
        """Complete reflection agent"""
        self.emit("reflection_agent", "completed", "Reflection analysis completed")

    def start_trader(self):
        """Start trader agent"""
        self.emit("trader_agent", "started", "Running Trader Decision Agent...")

    def complete_trader(self):
        """Complete trader agent"""
        self.emit("trader_agent", "completed", "Final trading decision generated")

    def complete_all(self):
        """Mark entire pipeline as complete"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.emit("complete", "completed", f"Analysis complete in {elapsed:.1f}s")

    def error(self, step: str, error_message: str):
        """Report an error"""
        self.emit(step, "error", f"Error: {error_message}")
