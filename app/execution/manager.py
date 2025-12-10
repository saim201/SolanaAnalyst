"""
Trade Execution Manager
Integrates the agent pipeline with trade execution.

Responsibilities:
- Execute agent decisions
- Manage position lifecycle
- Handle stop-loss and take-profit
- Track execution history
- Generate execution reports
"""
from datetime import datetime
from typing import Dict, Optional, Tuple
import json

from app.agents.pipeline import TradingGraph
from app.execution.engine import PaperTradingEngine, OrderType
from app.database.config import get_db_session
from app.database.models import TraderAnalyst, Position as PositionModel


class ExecutionManager:
    """
    Manages the complete trade execution lifecycle.

    Flow:
    1. Agent pipeline generates decision
    2. Validate decision and risk parameters
    3. Place order via trading engine
    4. Monitor position for exit triggers
    5. Log execution and results
    """

    def __init__(
        self,
        symbol: str = "SOL/USDT",
        initial_balance: float = 10000.0,
        use_paper_trading: bool = True,
    ):
        """
        Initialize execution manager.

        Args:
            symbol: Trading symbol
            initial_balance: Paper trading account balance
            use_paper_trading: Use paper trading mode
        """
        self.symbol = symbol
        self.use_paper_trading = use_paper_trading

        # Initialize trading engine
        self.engine = PaperTradingEngine(initial_balance=initial_balance)

        # Initialize agent pipeline
        self.pipeline = TradingGraph()

        # Execution history
        self.executions: Dict[str, Dict] = {}
        self.execution_count = 0

    def run_analysis_and_execute(
        self,
        current_price: float,
    ) -> Dict:
        """
        Run complete analysis pipeline and execute if signal is strong.

        Args:
            current_price: Current market price

        Returns:
            Execution result dictionary
        """
        # Step 1: Run agent pipeline
        analysis_result = self.pipeline.run()

        # Step 2: Check if we should execute
        decision = analysis_result['decision'].lower()
        confidence = analysis_result['confidence']
        action = analysis_result['action']
        risk_approved = analysis_result['risk_approved']
        position_size = analysis_result['position_size']

        # Step 3: Validate execution criteria
        if not self._should_execute(decision, confidence, risk_approved):
            return {
                'executed': False,
                'reason': f"Decision '{decision}' with confidence {confidence:.2f} not strong enough",
                'decision': decision,
                'confidence': confidence,
                'analysis': analysis_result,
            }

        # Step 4: Execute trade
        execution_result = self._execute_trade(
            decision=decision,
            confidence=confidence,
            action=action,
            position_size=position_size,
            current_price=current_price,
            analysis_result=analysis_result,
        )

        return execution_result

    def _should_execute(self, decision: str, confidence: float, risk_approved: bool) -> bool:
        """
        Determine if trade should be executed.

        Args:
            decision: BUY, SELL, or HOLD
            confidence: Confidence score (0-1)
            risk_approved: Risk management approval

        Returns:
            True if trade should execute, False otherwise
        """
        if decision == 'hold':
            return False

        # Minimum confidence threshold
        if confidence < 0.55:
            return False

        # Must be risk approved
        if not risk_approved:
            return False

        return True

    def _execute_trade(
        self,
        decision: str,
        confidence: float,
        action: float,
        position_size: float,
        current_price: float,
        analysis_result: Dict,
    ) -> Dict:
        """
        Execute a trade based on agent decision.

        Args:
            decision: BUY or SELL
            confidence: Confidence score
            action: Action value (-1 to 1)
            position_size: Position size percentage
            current_price: Current market price
            analysis_result: Full analysis from pipeline

        Returns:
            Execution result
        """
        self.execution_count += 1
        execution_id = f"EXEC_{self.execution_count:04d}"

        # Calculate position quantity
        available_balance = self.engine.balance
        position_value = available_balance * position_size
        quantity = position_value / current_price

        # Extract stop loss and take profit
        risk_reasoning = analysis_result['risk_reasoning']
        stop_loss = self._extract_price_from_text(risk_reasoning, 'stop')
        take_profit = self._extract_price_from_text(risk_reasoning, 'take')

        # Place order
        success, message, order = self.engine.place_order(
            symbol=self.symbol,
            order_type=OrderType.MARKET,
            side='buy' if decision == 'buy' else 'sell',
            quantity=quantity,
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            notes=f"Signal confidence: {confidence:.2f}, Agent decision: {decision}",
        )

        if not success:
            return {
                'executed': False,
                'reason': message,
                'execution_id': execution_id,
                'decision': decision,
                'confidence': confidence,
            }

        # Log execution
        execution_data = {
            'execution_id': execution_id,
            'timestamp': datetime.now().isoformat(),
            'decision': decision,
            'confidence': confidence,
            'action': action,
            'position_size': position_size,
            'quantity': quantity,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'order': order.to_dict() if order else None,
            'analysis': analysis_result,
            'status': 'executed',
        }

        self.executions[execution_id] = execution_data

        # Save to database
        self._save_execution_to_db(execution_data)

        return {
            'executed': True,
            'execution_id': execution_id,
            'message': f"Trade executed: {decision.upper()} {quantity:.4f} {self.symbol} @ ${current_price:.2f}",
            'order': order.to_dict() if order else None,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'portfolio_value': self.engine.get_portfolio_value(current_price),
        }

    def check_exits(self, current_price: float) -> Dict:
        """
        Check for and execute stop-loss and take-profit orders.

        Args:
            current_price: Current market price

        Returns:
            Dictionary of triggered exits
        """
        triggered = self.engine.check_stop_loss_take_profit(current_price)
        exits = {}

        for pos_id, trigger_type in triggered:
            success, message, pnl = self.engine.close_position(pos_id, current_price)

            if success:
                exits[pos_id] = {
                    'trigger': trigger_type,
                    'exit_price': current_price,
                    'pnl': pnl,
                    'message': message,
                }

        return exits

    def get_portfolio_status(self, current_price: float) -> Dict:
        """
        Get current portfolio status.

        Args:
            current_price: Current market price

        Returns:
            Portfolio status dictionary
        """
        stats = self.engine.get_portfolio_stats(current_price)

        # Add open positions
        open_positions = [
            pos.to_dict(current_price) for pos in self.engine.positions.values()
        ]

        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'current_price': current_price,
            'statistics': stats,
            'open_positions': open_positions,
            'execution_count': self.execution_count,
            'recent_executions': self._get_recent_executions(limit=5),
        }

    def _get_recent_executions(self, limit: int = 5) -> list:
        """Get recent executions"""
        execution_ids = list(self.executions.keys())[-limit:]
        return [
            {
                'execution_id': exec_id,
                'decision': self.executions[exec_id]['decision'],
                'confidence': self.executions[exec_id]['confidence'],
                'timestamp': self.executions[exec_id]['timestamp'],
            }
            for exec_id in execution_ids
        ]

    def _extract_price_from_text(self, text: str, price_type: str) -> Optional[float]:
        """
        Extract price from text (e.g., "Stop loss at $50.25").

        Args:
            text: Text to parse
            price_type: 'stop' or 'take'

        Returns:
            Extracted price or None
        """
        if not text:
            return None

        try:
            # Look for patterns like "$50.25" or "50.25"
            import re

            if price_type == 'stop':
                pattern = r'stop.*?\$?([\d.]+)'
            else:
                pattern = r'take.*?\$?([\d.]+)'

            match = re.search(pattern, text.lower())
            if match:
                return float(match.group(1))
        except (ValueError, AttributeError):
            pass

        return None

    def _save_execution_to_db(self, execution_data: Dict):
        """
        Save execution to database.

        Args:
            execution_data: Execution data to save
        """
        try:
            db = get_db_session()

            trade_decision = TraderAnalyst(
                timestamp=datetime.now(),
                decision=execution_data['decision'],
                confidence=execution_data['confidence'],
                reasoning=json.dumps(execution_data['analysis'])
            )

            db.add(trade_decision)
            db.commit()
            db.close()

        except Exception as e:
            print(f"Error saving execution to database: {e}")

    def get_execution_history(self) -> list:
        """Get all execution history"""
        return [
            {
                'execution_id': exec_id,
                'timestamp': data['timestamp'],
                'decision': data['decision'],
                'confidence': data['confidence'],
                'quantity': data['quantity'],
                'entry_price': data['entry_price'],
                'stop_loss': data['stop_loss'],
                'take_profit': data['take_profit'],
            }
            for exec_id, data in self.executions.items()
        ]

    def reset_paper_trading(self):
        """Reset paper trading engine"""
        self.engine.reset()
        self.execution_count = 0
        self.executions.clear()
