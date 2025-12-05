"""
Trade Execution Examples
Demonstrates how to use the execution system.
"""
from app.execution.manager import ExecutionManager
from app.execution.engine import OrderType


def example_1_basic_execution():
    """
    Example 1: Basic trade execution
    Shows how to initialize and execute a simple trade.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Trade Execution")
    print("="*80)

    # Initialize execution manager
    manager = ExecutionManager(
        symbol="SOL/USDT",
        initial_balance=10000.0,
        use_paper_trading=True,
    )

    # Current market price
    current_price = 150.0

    # Run analysis and execute
    result = manager.run_analysis_and_execute(current_price)

    print(f"Execution Result: {result}")
    print(f"Executed: {result['executed']}")
    print(f"Decision: {result['decision']}")
    print(f"Confidence: {result['confidence']:.2f}")

    if result['executed']:
        print(f"Execution ID: {result['execution_id']}")
        print(f"Message: {result['message']}")
        print(f"Portfolio Value: ${result['portfolio_value']:.2f}")


def example_2_multiple_executions():
    """
    Example 2: Multiple executions with price changes
    Shows portfolio progression through multiple trades.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Multiple Executions with Price Changes")
    print("="*80)

    manager = ExecutionManager(
        symbol="SOL/USDT",
        initial_balance=10000.0,
        use_paper_trading=True,
    )

    prices = [150.0, 155.0, 148.0, 160.0, 158.0]

    for i, price in enumerate(prices, 1):
        print(f"\n--- Trade Cycle {i} (Price: ${price}) ---")

        result = manager.run_analysis_and_execute(price)

        if result['executed']:
            print(f"✅ Trade Executed")
            print(f"   Decision: {result['decision']}")
            print(f"   Portfolio Value: ${result['portfolio_value']:.2f}")
        else:
            print(f"⏭️  Trade Skipped: {result['reason']}")

        # Check for stop-loss/take-profit
        exits = manager.check_exits(price)
        if exits:
            print(f"📍 Positions Closed: {len(exits)}")
            for pos_id, exit_data in exits.items():
                print(f"   {exit_data['trigger'].upper()}: P&L ${exit_data['pnl']:.2f}")

        # Print portfolio status
        status = manager.get_portfolio_status(price)
        print(f"   Open Positions: {len(status['open_positions'])}")
        print(f"   Win Rate: {status['statistics']['win_rate']:.1f}%")


def example_3_portfolio_tracking():
    """
    Example 3: Detailed portfolio tracking
    Shows how to monitor portfolio metrics.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Portfolio Tracking")
    print("="*80)

    manager = ExecutionManager(
        symbol="SOL/USDT",
        initial_balance=10000.0,
        use_paper_trading=True,
    )

    # Execute a trade
    current_price = 150.0
    result = manager.run_analysis_and_execute(current_price)

    if result['executed']:
        print(f"\nTrade Executed at ${current_price}")

        # Simulate price movements
        prices = [152.0, 148.0, 155.0, 160.0]

        for price in prices:
            status = manager.get_portfolio_status(price)
            stats = status['statistics']

            print(f"\n--- Price: ${price} ---")
            print(f"Portfolio Value: ${stats['portfolio_value']:.2f}")
            print(f"Total P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_percent']:.2f}%)")
            print(f"Cash Balance: ${stats['current_balance']:.2f}")
            print(f"Fees Paid: ${stats['total_fees_paid']:.2f}")
            print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")

            if status['open_positions']:
                print(f"Open Positions ({len(status['open_positions'])}):")
                for pos in status['open_positions']:
                    print(
                        f"  {pos['symbol']}: "
                        f"{pos['quantity']:.4f} @ ${pos['entry_price']:.2f}, "
                        f"P&L: ${pos['current_pnl']:.2f} ({pos['current_pnl_percent']:.2f}%)"
                    )


def example_4_execution_history():
    """
    Example 4: Viewing execution history
    Shows how to access execution records.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Execution History")
    print("="*80)

    manager = ExecutionManager(
        symbol="SOL/USDT",
        initial_balance=10000.0,
        use_paper_trading=True,
    )

    # Execute multiple trades
    prices = [150.0, 155.0, 148.0]
    for price in prices:
        manager.run_analysis_and_execute(price)

    # Get execution history
    history = manager.get_execution_history()

    print(f"\nTotal Executions: {len(history)}")
    print("\nExecution History:")
    print("-" * 80)

    for execution in history:
        print(f"ID: {execution['execution_id']}")
        print(f"  Time: {execution['timestamp']}")
        print(f"  Decision: {execution['decision'].upper()}")
        print(f"  Confidence: {execution['confidence']:.2f}")
        print(f"  Quantity: {execution['quantity']:.4f}")
        print(f"  Entry Price: ${execution['entry_price']:.2f}")
        if execution['stop_loss']:
            print(f"  Stop Loss: ${execution['stop_loss']:.2f}")
        if execution['take_profit']:
            print(f"  Take Profit: ${execution['take_profit']:.2f}")
        print()


def example_5_advanced_execution():
    """
    Example 5: Advanced execution with manual order placement
    Shows direct order placement without pipeline.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Direct Order Placement")
    print("="*80)

    manager = ExecutionManager(
        symbol="SOL/USDT",
        initial_balance=10000.0,
        use_paper_trading=True,
    )

    current_price = 150.0

    # Manually place a market order
    print(f"\nPlacing BUY order for 0.5 SOL @ ${current_price}")

    success, message, order = manager.engine.place_order(
        symbol="SOL/USDT",
        order_type=OrderType.MARKET,
        side="buy",
        quantity=0.5,
        price=current_price,
        stop_loss=145.0,  # 5% below entry
        take_profit=160.0,  # 10% above entry
    )

    if success:
        print(f"✅ {message}")
        print(f"Order Details:")
        print(f"  Order ID: {order.order_id}")
        print(f"  Status: {order.status.value}")
        print(f"  Filled Price: ${order.filled_price:.2f}")

        # Get portfolio status
        status = manager.get_portfolio_status(current_price)
        print(f"\nPortfolio Status:")
        print(f"  Cash Balance: ${status['statistics']['current_balance']:.2f}")
        print(f"  Portfolio Value: ${status['statistics']['portfolio_value']:.2f}")
    else:
        print(f"❌ {message}")


if __name__ == "__main__":
    """Run all examples"""
    try:
        example_1_basic_execution()
        example_2_multiple_executions()
        example_3_portfolio_tracking()
        example_4_execution_history()
        example_5_advanced_execution()

        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
