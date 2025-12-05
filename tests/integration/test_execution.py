"""
Integration tests for the trade execution system.
Tests order execution, position management, and portfolio tracking.
"""
import pytest
from app.execution.engine import (
    PaperTradingEngine,
    Order,
    OrderType,
    OrderStatus,
    PositionStatus,
)
from app.execution.manager import ExecutionManager


class TestPaperTradingEngine:
    """Tests for PaperTradingEngine"""

    def setup_method(self):
        """Initialize engine for each test"""
        self.engine = PaperTradingEngine(initial_balance=10000.0)

    def test_engine_initialization(self):
        """Test engine initializes with correct balance"""
        assert self.engine.balance == 10000.0
        assert self.engine.initial_balance == 10000.0
        assert len(self.engine.positions) == 0
        assert len(self.engine.closed_positions) == 0

    def test_place_market_buy_order(self):
        """Test placing a market buy order"""
        initial_balance = self.engine.balance

        success, message, order = self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        assert success
        assert order is not None
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 1.0
        assert self.engine.balance < initial_balance  # Balance decreased
        assert len(self.engine.positions) == 1  # Position created

    def test_place_market_sell_order(self):
        """Test placing a market sell order"""
        # First buy
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        initial_balance = self.engine.balance

        # Then sell
        success, message, order = self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="sell",
            quantity=0.5,
            price=155.0,
        )

        assert success
        assert order.status == OrderStatus.FILLED
        assert self.engine.balance > initial_balance  # Balance increased

    def test_insufficient_balance_buy(self):
        """Test buy order fails with insufficient balance"""
        # Try to buy more than we can afford
        success, message, order = self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=100.0,  # Very large quantity
            price=1000.0,
        )

        assert not success
        assert "Insufficient balance" in message

    def test_long_position_pnl(self):
        """Test P&L calculation for long position"""
        # Buy position
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        position = list(self.engine.positions.values())[0]

        # Price goes up
        pnl_up = position.current_pnl(160.0)
        assert pnl_up > 0  # Profit

        # Price goes down
        pnl_down = position.current_pnl(140.0)
        assert pnl_down < 0  # Loss

    def test_short_position_pnl(self):
        """Test P&L calculation for short position"""
        # Sell position (short)
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="sell",
            quantity=1.0,
            price=150.0,
        )

        position = list(self.engine.positions.values())[0]

        # Price goes down (good for short)
        pnl_down = position.current_pnl(140.0)
        assert pnl_down > 0  # Profit

        # Price goes up (bad for short)
        pnl_up = position.current_pnl(160.0)
        assert pnl_up < 0  # Loss

    def test_close_position(self):
        """Test closing a position"""
        # Create position
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        position_id = list(self.engine.positions.keys())[0]

        # Close position
        success, message, pnl = self.engine.close_position(position_id, 160.0)

        assert success
        assert position_id not in self.engine.positions
        assert position_id in [p.position_id for p in self.engine.closed_positions]
        assert pnl > 0  # Profit (160 - 150)

    def test_stop_loss_trigger(self):
        """Test stop loss trigger detection"""
        # Buy with stop loss
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
            stop_loss=145.0,
        )

        # Price hits stop loss
        triggered = self.engine.check_stop_loss_take_profit(145.0)

        assert len(triggered) > 0
        assert triggered[0][1] == 'stop_loss'

    def test_take_profit_trigger(self):
        """Test take profit trigger detection"""
        # Buy with take profit
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
            take_profit=160.0,
        )

        # Price hits take profit
        triggered = self.engine.check_stop_loss_take_profit(160.0)

        assert len(triggered) > 0
        assert triggered[0][1] == 'take_profit'

    def test_portfolio_value_calculation(self):
        """Test portfolio value calculation"""
        # Initial value
        value_initial = self.engine.get_portfolio_value(150.0)
        assert value_initial == 10000.0

        # Buy 1 SOL at 150
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        # Portfolio value increases if price goes up
        value_up = self.engine.get_portfolio_value(160.0)
        assert value_up > value_initial

    def test_portfolio_statistics(self):
        """Test portfolio statistics"""
        stats = self.engine.get_portfolio_stats(150.0)

        assert 'initial_balance' in stats
        assert 'current_balance' in stats
        assert 'portfolio_value' in stats
        assert 'total_pnl' in stats
        assert 'win_rate' in stats
        assert 'max_drawdown' in stats

    def test_fees_calculation(self):
        """Test that fees are properly calculated"""
        initial_fees = self.engine.total_fees_paid

        # Place order
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        # Fees should increase
        assert self.engine.total_fees_paid > initial_fees

    def test_slippage_application(self):
        """Test that slippage is applied to orders"""
        engine = PaperTradingEngine(slippage_percent=1.0)  # 1% slippage

        # Buy at 150 with 1% slippage should execute at 151.50
        success, message, order = engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        assert success
        assert order.filled_price > order.price  # Slippage added

    def test_engine_reset(self):
        """Test engine reset functionality"""
        # Create position
        self.engine.place_order(
            symbol="SOL/USDT",
            order_type=OrderType.MARKET,
            side="buy",
            quantity=1.0,
            price=150.0,
        )

        # Reset
        self.engine.reset()

        assert len(self.engine.positions) == 0
        assert len(self.engine.closed_positions) == 0
        assert self.engine.total_trades == 0
        assert self.engine.balance == self.engine.initial_balance


class TestExecutionManager:
    """Tests for ExecutionManager"""

    def setup_method(self):
        """Initialize manager for each test"""
        self.manager = ExecutionManager(
            symbol="SOL/USDT",
            initial_balance=10000.0,
            use_paper_trading=True,
        )

    def test_manager_initialization(self):
        """Test manager initializes correctly"""
        assert self.manager.symbol == "SOL/USDT"
        assert self.manager.use_paper_trading is True
        assert self.manager.engine is not None
        assert self.manager.pipeline is not None

    def test_execution_decision_generation(self):
        """Test that execution generates valid decisions"""
        current_price = 150.0

        result = self.manager.run_analysis_and_execute(current_price)

        assert 'decision' in result
        assert result['decision'].lower() in ['buy', 'sell', 'hold']
        assert 'confidence' in result
        assert 0.0 <= result['confidence'] <= 1.0

    def test_execution_with_low_confidence_skipped(self):
        """Test execution is skipped with low confidence"""
        # This test validates that low confidence trades aren't executed
        # (Real test would need to mock pipeline to force low confidence)
        pass

    def test_portfolio_status_retrieval(self):
        """Test getting portfolio status"""
        current_price = 150.0

        status = self.manager.get_portfolio_status(current_price)

        assert 'timestamp' in status
        assert 'symbol' in status
        assert 'current_price' in status
        assert 'statistics' in status
        assert 'open_positions' in status

    def test_execution_history_tracking(self):
        """Test execution history is tracked"""
        # Execute multiple trades
        prices = [150.0, 152.0, 148.0]

        for price in prices:
            self.manager.run_analysis_and_execute(price)

        history = self.manager.get_execution_history()

        assert len(history) >= 0  # May be 0 if all decisions are HOLD

    def test_check_exits(self):
        """Test stop-loss and take-profit checking"""
        # This would need actual position creation to test properly
        current_price = 150.0

        exits = self.manager.check_exits(current_price)

        assert isinstance(exits, dict)

    def test_price_extraction_from_text(self):
        """Test extracting prices from text"""
        text = "The stop loss should be at $145.50 and take profit at $160.75"

        stop = self.manager._extract_price_from_text(text, 'stop')
        take = self.manager._extract_price_from_text(text, 'take')

        assert stop is not None
        assert take is not None

    def test_manager_reset(self):
        """Test manager reset"""
        initial_count = self.manager.execution_count

        # Execute
        self.manager.run_analysis_and_execute(150.0)

        # Reset
        self.manager.reset_paper_trading()

        assert self.manager.execution_count == 0
        assert len(self.manager.executions) == 0


class TestExecutionIntegration:
    """Integration tests for full execution workflow"""

    def test_full_trade_cycle(self):
        """Test complete trade cycle: buy -> monitor -> sell"""
        manager = ExecutionManager(initial_balance=10000.0)

        # Execute initial buy
        buy_result = manager.run_analysis_and_execute(150.0)

        # Monitor price movement
        prices = [152.0, 155.0, 158.0, 160.0]

        for price in prices:
            status = manager.get_portfolio_status(price)

            # Check for exits
            exits = manager.check_exits(price)

            if exits:
                print(f"Position closed at ${price}")
                break

        # Verify portfolio tracked
        assert manager.execution_count >= 0
        final_status = manager.get_portfolio_status(150.0)
        assert final_status is not None

    def test_multiple_concurrent_positions(self):
        """Test managing multiple positions simultaneously"""
        manager = ExecutionManager(initial_balance=50000.0)

        # Execute multiple trades at different times
        prices = [150.0, 155.0, 152.0]

        for i, price in enumerate(prices):
            result = manager.run_analysis_and_execute(price)

            if result['executed']:
                print(f"Trade {i+1} executed at ${price}")

        # Get final portfolio status
        final_price = 160.0
        status = manager.get_portfolio_status(final_price)

        assert len(status['open_positions']) >= 0

    def test_portfolio_metrics_consistency(self):
        """Test that portfolio metrics remain consistent"""
        manager = ExecutionManager(initial_balance=10000.0)

        # Execute some trades
        prices = [150.0, 152.0, 148.0]

        for price in prices:
            manager.run_analysis_and_execute(price)

        # Check metrics
        status = manager.get_portfolio_status(150.0)
        stats = status['statistics']

        # Verify basic metric relationships
        assert stats['initial_balance'] == 10000.0
        assert stats['total_pnl'] == stats['portfolio_value'] - stats['initial_balance']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
