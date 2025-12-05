# Quick Start Guide

## Installation & Setup

### 1. Initialize Manager
```python
from app.execution.manager import ExecutionManager

manager = ExecutionManager(
    symbol="SOL/USDT",
    initial_balance=10000.0,
    use_paper_trading=True
)
```

### 2. Run Analysis & Execute
```python
# Current market price
current_price = 150.0

# Run pipeline and execute if criteria met
result = manager.run_analysis_and_execute(current_price)

# Check result
if result['executed']:
    print(f"✅ Trade {result['execution_id']} executed")
else:
    print(f"⏭️  Trade skipped: {result['reason']}")
```

### 3. Monitor Position
```python
# Get portfolio status
status = manager.get_portfolio_status(current_price)

# Print metrics
stats = status['statistics']
print(f"Portfolio Value: ${stats['portfolio_value']:.2f}")
print(f"Total P&L: ${stats['total_pnl']:.2f}")
print(f"Win Rate: {stats['win_rate']:.1f}%")

# Check open positions
for pos in status['open_positions']:
    print(f"{pos['symbol']}: {pos['quantity']:.4f} @ ${pos['entry_price']:.2f}")
    print(f"  Current P&L: ${pos['current_pnl']:.2f}")
```

### 4. Check Exits
```python
# New price
new_price = 160.0

# Check for stop-loss and take-profit
exits = manager.check_exits(new_price)

for pos_id, exit_info in exits.items():
    print(f"Position {pos_id} closed")
    print(f"Trigger: {exit_info['trigger']}")
    print(f"P&L: ${exit_info['pnl']:.2f}")
```

---

## Common Tasks

### Get Execution History
```python
history = manager.get_execution_history()

for exec in history:
    print(f"{exec['execution_id']}: {exec['decision']} @ ${exec['entry_price']:.2f}")
```

### Check Portfolio Value at Different Price
```python
prices = [145.0, 150.0, 155.0, 160.0]

for price in prices:
    value = manager.engine.get_portfolio_value(price)
    print(f"At ${price}: Portfolio worth ${value:.2f}")
```

### Manual Order Placement
```python
from app.execution.engine import OrderType

success, msg, order = manager.engine.place_order(
    symbol="SOL/USDT",
    order_type=OrderType.MARKET,
    side="buy",
    quantity=0.5,
    price=150.0,
    stop_loss=145.0,
    take_profit=160.0
)

if success:
    print(f"Order {order.order_id} executed at ${order.filled_price}")
```

### Reset Paper Trading
```python
manager.reset_paper_trading()
# Clears all positions, executions, and resets balance
```

---

## Key Metrics Explained

| Metric | Formula | Example |
|--------|---------|---------|
| **Portfolio Value** | Cash + Position Value | $10,250.75 |
| **Total P&L** | Current Value - Initial | $250.75 |
| **P&L %** | (Total P&L / Initial) × 100 | 2.51% |
| **Win Rate** | Wins / (Wins + Losses) × 100 | 60% |
| **Max Drawdown** | Largest Peak-to-Trough | 5.3% |

---

## Decision Flow

```
Agent Pipeline
       ↓
✓ Decision = BUY/SELL? (not HOLD)
✓ Confidence >= 0.55?
✓ Risk Approved?
✓ Sufficient Balance?
       ↓
   EXECUTE TRADE
       ↓
   Place Order
   Create Position
   Track Portfolio
       ↓
   Monitor Price
       ↓
✓ Stop-Loss Hit? → Close Position
✓ Take-Profit Hit? → Close Position
       ↓
   Log Results
   Save to Database
```

---

## Examples

### Example 1: Single Trade Cycle
```python
manager = ExecutionManager()

# Execute
result = manager.run_analysis_and_execute(150.0)

# Monitor
if result['executed']:
    for price in [151, 152, 155, 160]:
        exits = manager.check_exits(price)
        if exits:
            print(f"Closed at ${price}")
            break
```

### Example 2: Multiple Trades
```python
manager = ExecutionManager(initial_balance=50000.0)

prices = [150, 152, 148, 155, 160]

for price in prices:
    manager.run_analysis_and_execute(price)

final = manager.get_portfolio_status(150.0)
print(f"Final P&L: ${final['statistics']['total_pnl']:.2f}")
```

### Example 3: Full Monitoring Loop
```python
manager = ExecutionManager()

# Trade
manager.run_analysis_and_execute(150.0)

# Monitor with price updates
for hour, price in enumerate([151, 152, 155, 160, 158, 155], 1):
    # Check exits
    exits = manager.check_exits(price)
    if exits:
        print(f"Hour {hour}: Position closed at ${price}")
        break

    # Get status
    status = manager.get_portfolio_status(price)
    print(f"Hour {hour}: ${price} → P&L ${status['statistics']['total_pnl']:.2f}")
```

---

## Troubleshooting

### Trade Not Executing
**Check:**
- Is decision 'buy' or 'sell'?
- Is confidence >= 0.55?
- Is risk approved?
- Do you have enough balance?

### Wrong P&L
**Verify:**
- Entry price correct?
- Current price correct?
- Position side (long/short) correct?
- Check: `position.current_pnl(price)`

### Position Not Closing
**Check:**
- Did you call `check_exits()`?
- Is price at/past stop-loss or take-profit?
- Is position status 'open'?

---

## API Reference

### ExecutionManager

#### Methods

**`run_analysis_and_execute(current_price: float) → Dict`**
- Runs agent pipeline and executes if criteria met
- Returns: `{'executed': bool, ...}`

**`check_exits(current_price: float) → Dict`**
- Checks for and executes stop-loss/take-profit
- Returns: `{position_id: {'trigger': 'stop_loss'|'take_profit', ...}}`

**`get_portfolio_status(current_price: float) → Dict`**
- Gets complete portfolio status with metrics
- Returns: `{'statistics': {...}, 'open_positions': [...]}`

**`get_execution_history() → List`**
- Gets all executions with details
- Returns: `[{'execution_id': ..., 'decision': ..., ...}]`

**`reset_paper_trading()`**
- Resets engine and clears history
- Use: Start fresh simulation

### PaperTradingEngine

#### Methods

**`place_order(...) → Tuple[bool, str, Order]`**
- Places and executes a market order
- Returns: `(success, message, order)`

**`close_position(position_id: str, current_price: float) → Tuple[bool, str, float]`**
- Closes a position and calculates P&L
- Returns: `(success, message, pnl)`

**`check_stop_loss_take_profit(current_price: float) → List`**
- Checks all positions for exit triggers
- Returns: `[(position_id, trigger_type), ...]`

**`get_portfolio_value(current_price: float) → float`**
- Gets total portfolio value
- Returns: `float (cash + positions)`

**`get_portfolio_stats(current_price: float) → Dict`**
- Gets comprehensive statistics
- Returns: `{...metrics...}`

---

## Running Tests

```bash
# All execution tests
pytest tests/integration/test_execution.py -v

# Specific test
pytest tests/integration/test_execution.py::TestPaperTradingEngine -v

# With output
pytest tests/integration/test_execution.py -v -s
```

---

## Running Examples

```bash
# Run all examples
python -m app.execution.examples

# Or import and run specific one
python -c "from app.execution.examples import example_1_basic_execution; example_1_basic_execution()"
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `app/execution/engine.py` | Core trading engine |
| `app/execution/manager.py` | Pipeline integration |
| `app/execution/__init__.py` | Package exports |
| `app/execution/examples.py` | 5 working examples |
| `tests/integration/test_execution.py` | Test suite |
| `EXECUTION_GUIDE.md` | Complete documentation |
| `QUICK_START.md` | This file |

---

## Next Steps

1. **Try Examples**
   ```bash
   python -m app.execution.examples
   ```

2. **Read Full Guide**
   - See: `EXECUTION_GUIDE.md`

3. **Run Tests**
   ```bash
   pytest tests/integration/test_execution.py -v
   ```

4. **Integrate with API**
   - Add execution endpoints to FastAPI
   - Expose portfolio status endpoint
   - Create execution history endpoint

5. **Build Backtesting**
   - Load historical price data
   - Replay through execution engine
   - Analyze strategy performance

---

**Ready to trade! 🚀**
