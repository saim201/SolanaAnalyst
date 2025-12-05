"""
Trade Execution Engine
Handles trade execution with paper trading (simulation) support.

Features:
- Paper trading simulation (no real funds)
- Order management (entry, exit, modifications)
- Position tracking and P&L calculation
- Slippage and fee simulation
- Order history and statistics
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import json
import uuid


class OrderType(Enum):
    """Order types"""
    LIMIT = "limit"
    MARKET = "market"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(Enum):
    """Order statuses"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"


class PositionStatus(Enum):
    """Position statuses"""
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class Order:
    """Represents a single order"""
    order_id: str
    symbol: str
    order_type: OrderType
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'created_at': self.created_at.isoformat(),
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'notes': self.notes,
        }


@dataclass
class Position:
    """Represents an open position"""
    position_id: str
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    quantity: float
    entry_time: datetime = field(default_factory=datetime.now)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: PositionStatus = PositionStatus.OPEN

    # Trade metadata
    confidence: float = 0.5
    agent_reasoning: str = ""

    def current_pnl(self, current_price: float) -> float:
        """Calculate current P&L"""
        if self.side == 'long':
            pnl = (current_price - self.entry_price) * self.quantity
        else:  # short
            pnl = (self.entry_price - current_price) * self.quantity
        return float(pnl)

    def current_pnl_percent(self, current_price: float) -> float:
        """Calculate current P&L percentage"""
        if self.entry_price == 0:
            return 0.0
        pnl_percent = (self.current_pnl(current_price) / (self.entry_price * self.quantity)) * 100
        return float(pnl_percent)

    def to_dict(self, current_price: float) -> Dict:
        """Convert to dictionary with P&L"""
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'entry_time': self.entry_time.isoformat(),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'status': self.status.value,
            'current_price': current_price,
            'current_pnl': self.current_pnl(current_price),
            'current_pnl_percent': self.current_pnl_percent(current_price),
            'confidence': self.confidence,
            'agent_reasoning': self.agent_reasoning,
        }


class PaperTradingEngine:
    """
    Paper trading execution engine for backtesting and simulation.

    Features:
    - Simulates order execution with realistic pricing
    - Tracks P&L and portfolio performance
    - Implements slippage and trading fees
    - Maintains order and position history
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        slippage_percent: float = 0.1,
        fee_percent: float = 0.1,
    ):
        """
        Initialize paper trading engine.

        Args:
            initial_balance: Starting account balance in USD
            slippage_percent: Slippage as % of price (default 0.1%)
            fee_percent: Trading fee as % of trade value (default 0.1%)
        """
        self.initial_balance = float(initial_balance)
        self.balance = float(initial_balance)
        self.slippage_percent = slippage_percent
        self.fee_percent = fee_percent

        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []

        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees_paid = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = initial_balance

    def place_order(
        self,
        symbol: str,
        order_type: OrderType,
        side: str,
        quantity: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        notes: str = "",
    ) -> Tuple[bool, str, Optional[Order]]:
        """
        Place a new order.

        Args:
            symbol: Trading symbol (e.g., 'SOL/USDT')
            order_type: Type of order
            side: 'buy' or 'sell'
            quantity: Order quantity
            price: Order price
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            notes: Order notes

        Returns:
            Tuple of (success, message, order)
        """
        if not self._validate_order(side, quantity, price):
            return False, "Invalid order parameters", None

        order_id = str(uuid.uuid4())[:8]
        order = Order(
            order_id=order_id,
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            notes=notes,
        )

        # For market orders, execute immediately
        if order_type == OrderType.MARKET:
            success, msg = self._execute_order(order, stop_loss, take_profit)
            if not success:
                return False, msg, None
        else:
            # Store pending order
            self.orders[order_id] = order

        return True, f"Order {order_id} placed successfully", order

    def _execute_order(
        self,
        order: Order,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """Execute an order and update positions"""
        # Calculate execution price with slippage
        slippage = order.price * (self.slippage_percent / 100)
        if order.side == 'buy':
            execution_price = order.price + slippage
        else:
            execution_price = order.price - slippage

        # Check balance
        required_balance = execution_price * order.quantity
        if order.side == 'buy' and self.balance < required_balance:
            return False, "Insufficient balance"

        # Calculate fees
        fee = required_balance * (self.fee_percent / 100)
        total_cost = required_balance + fee

        if order.side == 'buy' and self.balance < total_cost:
            return False, "Insufficient balance for fees"

        # Update balance
        if order.side == 'buy':
            self.balance -= total_cost
        else:
            self.balance += (required_balance - fee)

        self.total_fees_paid += fee

        # Create or update position
        if order.side == 'buy':
            position = self._create_long_position(
                order.symbol,
                execution_price,
                order.quantity,
                stop_loss,
                take_profit,
            )
        else:
            position = self._create_short_position(
                order.symbol,
                execution_price,
                order.quantity,
                stop_loss,
                take_profit,
            )

        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = execution_price
        order.filled_at = datetime.now()

        # Track order
        self.order_history.append(order)
        self.total_trades += 1

        return True, f"Order executed at {execution_price:.2f}"

    def _create_long_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
    ) -> Position:
        """Create a new long position"""
        position_id = str(uuid.uuid4())[:8]
        position = Position(
            position_id=position_id,
            symbol=symbol,
            side='long',
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.positions[position_id] = position
        return position

    def _create_short_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
    ) -> Position:
        """Create a new short position"""
        position_id = str(uuid.uuid4())[:8]
        position = Position(
            position_id=position_id,
            symbol=symbol,
            side='short',
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.positions[position_id] = position
        return position

    def close_position(
        self,
        position_id: str,
        current_price: float,
    ) -> Tuple[bool, str, Optional[float]]:
        """
        Close a position at current market price.

        Args:
            position_id: ID of position to close
            current_price: Current market price

        Returns:
            Tuple of (success, message, pnl)
        """
        if position_id not in self.positions:
            return False, "Position not found", None

        position = self.positions[position_id]
        pnl = position.current_pnl(current_price)

        # Calculate fees
        close_value = current_price * position.quantity
        fee = close_value * (self.fee_percent / 100)
        self.total_fees_paid += fee

        # Update balance
        if position.side == 'long':
            self.balance += (close_value - fee)
        else:
            self.balance -= (close_value + fee)

        # Update position
        position.status = PositionStatus.CLOSED

        # Track closed position
        self.closed_positions.append(position)
        del self.positions[position_id]

        # Update statistics
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1

        # Update drawdown
        self._update_drawdown()

        return True, f"Position closed with P&L: ${pnl:.2f}", pnl

    def check_stop_loss_take_profit(self, current_price: float) -> List[Tuple[str, str]]:
        """
        Check all positions for stop loss and take profit triggers.

        Args:
            current_price: Current market price

        Returns:
            List of (position_id, action) tuples
        """
        triggered_positions = []

        for pos_id, position in list(self.positions.items()):
            # Check take profit
            if position.take_profit:
                if position.side == 'long' and current_price >= position.take_profit:
                    triggered_positions.append((pos_id, 'take_profit'))
                elif position.side == 'short' and current_price <= position.take_profit:
                    triggered_positions.append((pos_id, 'take_profit'))

            # Check stop loss
            if position.stop_loss:
                if position.side == 'long' and current_price <= position.stop_loss:
                    triggered_positions.append((pos_id, 'stop_loss'))
                elif position.side == 'short' and current_price >= position.stop_loss:
                    triggered_positions.append((pos_id, 'stop_loss'))

        return triggered_positions

    def get_portfolio_value(self, current_price: float) -> float:
        """Get total portfolio value (cash + positions)"""
        positions_value = sum(
            pos.quantity * current_price for pos in self.positions.values()
        )
        return self.balance + positions_value

    def get_portfolio_stats(self, current_price: float) -> Dict:
        """Get comprehensive portfolio statistics"""
        portfolio_value = self.get_portfolio_value(current_price)
        total_pnl = portfolio_value - self.initial_balance
        total_pnl_percent = (total_pnl / self.initial_balance) * 100

        win_rate = 0.0
        total_closed = self.winning_trades + self.losing_trades
        if total_closed > 0:
            win_rate = (self.winning_trades / total_closed) * 100

        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.balance,
            'portfolio_value': portfolio_value,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'open_positions': len(self.positions),
            'closed_positions': len(self.closed_positions),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_fees_paid': self.total_fees_paid,
            'max_drawdown': self.max_drawdown,
        }

    def _validate_order(self, side: str, quantity: float, price: float) -> bool:
        """Validate order parameters"""
        if side not in ['buy', 'sell']:
            return False
        if quantity <= 0 or price <= 0:
            return False
        return True

    def _update_drawdown(self):
        """Update maximum drawdown"""
        if self.balance < self.peak_balance:
            drawdown = ((self.peak_balance - self.balance) / self.peak_balance) * 100
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
        else:
            self.peak_balance = self.balance

    def reset(self):
        """Reset the trading engine"""
        self.balance = self.initial_balance
        self.positions.clear()
        self.closed_positions.clear()
        self.orders.clear()
        self.order_history.clear()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees_paid = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = self.initial_balance
