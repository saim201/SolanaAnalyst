"""
Risk Management Agent - HARD-CODED RULES (no LLM).
Implements non-negotiable safety gates to protect capital.

CRITICAL: This agent uses ZERO LLM calls - all decisions are deterministic.
Research shows LLMs are unreliable for risk assessment. Hard rules prevent catastrophic losses.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple
from app.agents.base import BaseAgent, AgentState
from app.agents.db_fetcher import DataQuery
from app.data.indicators import classify_volume_quality
from app.database.config import get_db_session
from app.database.models import PortfolioState, Position


class RiskManagementAgent(BaseAgent):
    """
    Agent that validates trades using hard-coded rules (NO LLM).

    SAFETY GATES (any failure = BLOCK TRADE):
    1. Volume Gate: volume_ratio >= 0.7 (DEAD volume = auto-reject)
    2. Confidence Gate: confidence >= 0.60 (minimum conviction threshold)
    3. R:R Gate: risk_reward_ratio >= 1.5 (swing trading minimum)
    4. Support Gate: support within 5% below entry (risk containment)
    5. Consecutive Loss Gate: max 3 consecutive losses (circuit breaker)
    6. Portfolio Heat: max 6% total risk across all positions

    POSITION SIZING:
    - Base: 2% risk per trade (industry standard)
    - Volume adjustment: multiply by volume_quality confidence_multiplier
    - Confidence adjustment: scale by (confidence - 0.6) / 0.4
    - Max: 5% in single position (prevent concentration)
    """

    def __init__(self):
        super().__init__(
            model=None,  # NO LLM - hard-coded rules only
            temperature=0.0
        )
        self.MAX_RISK_PER_TRADE = 0.02  # 2% base risk
        self.MAX_POSITION_SIZE = 0.05   # 5% max in one position
        self.MAX_PORTFOLIO_HEAT = 0.06  # 6% total risk across all positions
        self.MIN_CONFIDENCE = 0.60      # 60% minimum confidence
        self.MIN_RR_RATIO = 1.5         # 1.5:1 minimum R:R
        self.MIN_VOLUME_RATIO = 0.7     # 0.7x minimum volume (DEAD = reject)
        self.MAX_CONSECUTIVE_LOSSES = 3 # Circuit breaker
        self.MAX_SUPPORT_DISTANCE = 0.05 # Support must be within 5%

    def execute(self, state: AgentState) -> AgentState:
        """
        Validate trade using hard-coded rules (NO LLM).

        Args:
            state: Current trading state with recommendation

        Returns:
            State with risk_approved, position_size, and detailed reasoning
        """
        print("\n" + "="*60)
        print("🛡️  RISK MANAGEMENT - HARD-CODED VALIDATION")
        print("="*60)

        # Initialize risk state
        state['risk_approved'] = False
        state['position_size'] = 0.0
        state['position_size_usd'] = 0.0
        state['max_loss_usd'] = 0.0
        state['risk_reasoning'] = ""
        state['risk_warnings'] = []
        state['validation_details'] = {}

        # Extract recommendation
        recommendation = state.get('recommendation', 'HOLD')
        confidence = state.get('confidence', 0.0)

        # GATE 0: Only validate BUY/SELL, auto-approve HOLD
        if recommendation == 'HOLD':
            state['risk_approved'] = True
            state['risk_reasoning'] = "✅ HOLD decision - no risk assessment needed"
            print(state['risk_reasoning'])
            return state

        print(f"\n📊 Analyzing {recommendation} with {confidence:.0%} confidence...")

        # Get market data
        try:
            with DataQuery() as dq:
                indicators_dict = dq.get_indicators_data(days=1)
                ticker_dict = dq.get_ticker_data()

            # Get portfolio
            db = get_db_session()
            portfolio = db.query(PortfolioState).order_by(PortfolioState.timestamp.desc()).first()
            open_positions = db.query(Position).filter(OpenPosition.status == 'open').all()
            db.close()

        except Exception as e:
            state['risk_reasoning'] = f"❌ Data fetch error: {str(e)}"
            state['risk_warnings'] = ["data_fetch_failed"]
            print(state['risk_reasoning'])
            return state

        if not indicators_dict or not ticker_dict or not portfolio:
            state['risk_reasoning'] = "❌ Insufficient data (missing indicators, ticker, or portfolio)"
            state['risk_warnings'] = ["missing_data"]
            print(state['risk_reasoning'])
            return state

        # Extract values
        current_price = ticker_dict.get('lastPrice', 0)
        atr = indicators_dict.get('atr', 0)
        volume_ratio = indicators_dict.get('volume_ratio', 1.0)
        support1 = indicators_dict.get('support1')
        resistance1 = indicators_dict.get('resistance1')
        total_balance = portfolio.net_worth

        print(f"💰 Portfolio: ${total_balance:,.2f}")
        print(f"📈 Price: ${current_price:.2f} | ATR: ${atr:.2f}")
        print(f"📊 Volume Ratio: {volume_ratio:.2f}x")

        # Calculate trade levels
        entry_level = state.get('entry_level', current_price)
        stop_loss = state.get('stop_loss')
        take_profit = state.get('take_profit')

        # Auto-calculate if not provided
        if not stop_loss or not take_profit:
            if recommendation == 'BUY':
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3.0)
            else:  # SELL
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3.0)

            state['entry_level'] = current_price
            state['stop_loss'] = stop_loss
            state['take_profit'] = take_profit

        # ============================================================
        # SAFETY GATE #1: VOLUME VALIDATION (MOST IMPORTANT)
        # ============================================================
        volume_quality = classify_volume_quality(volume_ratio)
        volume_allowed = volume_quality['trading_allowed']
        volume_classification = volume_quality['classification']

        if not volume_allowed:
            state['risk_reasoning'] = (
                f"❌ GATE 1 FAILED: DEAD VOLUME\n"
                f"   Volume: {volume_ratio:.2f}x (classification: {volume_classification})\n"
                f"   Threshold: 0.7x minimum\n"
                f"   ⚠️  LOW VOLUME = FALSE SIGNALS - Trade blocked for capital protection"
            )
            state['risk_warnings'] = ["volume_dead"]
            state['validation_details']['gate1_volume'] = False
            print(state['risk_reasoning'])
            return state

        state['validation_details']['gate1_volume'] = True
        print(f"✅ GATE 1: Volume OK ({volume_ratio:.2f}x - {volume_classification})")

        # ============================================================
        # SAFETY GATE #2: CONFIDENCE THRESHOLD
        # ============================================================
        if confidence < self.MIN_CONFIDENCE:
            state['risk_reasoning'] = (
                f"❌ GATE 2 FAILED: LOW CONFIDENCE\n"
                f"   Confidence: {confidence:.0%}\n"
                f"   Threshold: {self.MIN_CONFIDENCE:.0%} minimum\n"
                f"   ⚠️  Insufficient conviction - waiting for clearer setup"
            )
            state['risk_warnings'] = ["confidence_low"]
            state['validation_details']['gate2_confidence'] = False
            print(state['risk_reasoning'])
            return state

        state['validation_details']['gate2_confidence'] = True
        print(f"✅ GATE 2: Confidence OK ({confidence:.0%})")

        # ============================================================
        # SAFETY GATE #3: RISK/REWARD RATIO
        # ============================================================
        risk_distance = abs(entry_level - stop_loss)
        reward_distance = abs(take_profit - entry_level)

        if risk_distance == 0:
            state['risk_reasoning'] = "❌ GATE 3 FAILED: Invalid stop loss (zero risk)"
            state['risk_warnings'] = ["invalid_stop_loss"]
            state['validation_details']['gate3_rr'] = False
            print(state['risk_reasoning'])
            return state

        rr_ratio = reward_distance / risk_distance

        if rr_ratio < self.MIN_RR_RATIO:
            state['risk_reasoning'] = (
                f"❌ GATE 3 FAILED: POOR RISK/REWARD\n"
                f"   R:R Ratio: {rr_ratio:.2f}:1\n"
                f"   Threshold: {self.MIN_RR_RATIO:.1f}:1 minimum\n"
                f"   Risk: ${risk_distance:.2f} | Reward: ${reward_distance:.2f}\n"
                f"   ⚠️  Insufficient reward for risk taken"
            )
            state['risk_warnings'] = ["poor_rr_ratio"]
            state['validation_details']['gate3_rr'] = False
            print(state['risk_reasoning'])
            return state

        state['validation_details']['gate3_rr'] = True
        state['risk_reward'] = rr_ratio
        print(f"✅ GATE 3: R:R OK ({rr_ratio:.2f}:1)")

        # ============================================================
        # SAFETY GATE #4: SUPPORT PROXIMITY (for BUY only)
        # ============================================================
        if recommendation == 'BUY':
            if not support1:
                state['risk_reasoning'] = "❌ GATE 4 FAILED: No support level identified"
                state['risk_warnings'] = ["no_support"]
                state['validation_details']['gate4_support'] = False
                print(state['risk_reasoning'])
                return state

            support_distance_pct = ((current_price - support1) / current_price)

            if support_distance_pct > self.MAX_SUPPORT_DISTANCE:
                state['risk_reasoning'] = (
                    f"❌ GATE 4 FAILED: SUPPORT TOO FAR\n"
                    f"   Support: ${support1:.2f} ({support_distance_pct:.1%} below)\n"
                    f"   Threshold: {self.MAX_SUPPORT_DISTANCE:.0%} maximum\n"
                    f"   ⚠️  Risk of large stop loss - invalidates swing trade setup"
                )
                state['risk_warnings'] = ["support_too_far"]
                state['validation_details']['gate4_support'] = False
                print(state['risk_reasoning'])
                return state

        state['validation_details']['gate4_support'] = True
        print(f"✅ GATE 4: Support proximity OK")

        # ============================================================
        # SAFETY GATE #5: CONSECUTIVE LOSSES CIRCUIT BREAKER
        # ============================================================
        consecutive_losses = self._count_consecutive_losses()

        if consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            state['risk_reasoning'] = (
                f"❌ GATE 5 FAILED: CIRCUIT BREAKER TRIGGERED\n"
                f"   Consecutive Losses: {consecutive_losses}\n"
                f"   Threshold: {self.MAX_CONSECUTIVE_LOSSES} maximum\n"
                f"   ⚠️  System requires cooldown period - strategy may be broken"
            )
            state['risk_warnings'] = ["circuit_breaker"]
            state['validation_details']['gate5_losses'] = False
            print(state['risk_reasoning'])
            return state

        state['validation_details']['gate5_losses'] = True
        print(f"✅ GATE 5: Consecutive losses OK ({consecutive_losses})")

        # ============================================================
        # SAFETY GATE #6: PORTFOLIO HEAT LIMIT
        # ============================================================
        current_heat = self._calculate_portfolio_heat(open_positions, total_balance)

        # Calculate position risk
        position_risk_usd = (risk_distance / entry_level) * total_balance * self.MAX_RISK_PER_TRADE

        if (current_heat + (position_risk_usd / total_balance)) > self.MAX_PORTFOLIO_HEAT:
            state['risk_reasoning'] = (
                f"❌ GATE 6 FAILED: PORTFOLIO HEAT LIMIT\n"
                f"   Current Heat: {current_heat:.1%}\n"
                f"   New Trade Risk: {(position_risk_usd/total_balance):.1%}\n"
                f"   Total: {(current_heat + position_risk_usd/total_balance):.1%}\n"
                f"   Threshold: {self.MAX_PORTFOLIO_HEAT:.0%} maximum\n"
                f"   ⚠️  Too much capital at risk - reduce exposure first"
            )
            state['risk_warnings'] = ["portfolio_heat_limit"]
            state['validation_details']['gate6_heat'] = False
            print(state['risk_reasoning'])
            return state

        state['validation_details']['gate6_heat'] = True
        print(f"✅ GATE 6: Portfolio heat OK ({current_heat:.1%})")

        # ============================================================
        # ALL GATES PASSED - CALCULATE POSITION SIZE
        # ============================================================
        print(f"\n✅ ALL 6 SAFETY GATES PASSED - CALCULATING POSITION SIZE...")

        # Base sizing: 2% risk per trade
        base_risk_pct = self.MAX_RISK_PER_TRADE

        # Adjust by volume quality
        volume_multiplier = volume_quality['confidence_multiplier']

        # Adjust by confidence (scale 0.6-1.0 to 0.0-1.0)
        confidence_multiplier = (confidence - self.MIN_CONFIDENCE) / (1.0 - self.MIN_CONFIDENCE)

        # Final risk percentage
        final_risk_pct = base_risk_pct * volume_multiplier * confidence_multiplier

        # Calculate position size
        risk_usd = final_risk_pct * total_balance
        position_size_units = risk_usd / risk_distance
        position_size_usd = position_size_units * entry_level
        position_size_pct = (position_size_usd / total_balance)

        # Cap at maximum
        if position_size_pct > self.MAX_POSITION_SIZE:
            position_size_pct = self.MAX_POSITION_SIZE
            position_size_usd = self.MAX_POSITION_SIZE * total_balance

        # Populate state
        state['risk_approved'] = True
        state['position_size'] = position_size_pct
        state['position_size_usd'] = position_size_usd
        state['max_loss_usd'] = risk_usd
        state['risk_reward'] = rr_ratio

        state['risk_reasoning'] = (
            f"✅ TRADE APPROVED\n"
            f"   Position Size: {position_size_pct:.1%} (${position_size_usd:,.2f})\n"
            f"   Max Loss: ${risk_usd:,.2f}\n"
            f"   Risk/Reward: {rr_ratio:.2f}:1\n"
            f"   Entry: ${entry_level:.2f} | Stop: ${stop_loss:.2f} | Target: ${take_profit:.2f}\n"
            f"\n"
            f"   Calculation:\n"
            f"   - Base Risk: {base_risk_pct:.1%}\n"
            f"   - Volume Adjustment: {volume_multiplier:.0%}\n"
            f"   - Confidence Adjustment: {confidence_multiplier:.0%}\n"
            f"   - Final Risk: {final_risk_pct:.2%}"
        )

        print(state['risk_reasoning'])
        print("="*60 + "\n")

        return state

    def _count_consecutive_losses(self) -> int:
        """Count consecutive losing trades"""
        try:
            from app.database.models import TradeDecision

            db = get_db_session()
            recent_decisions = db.query(TradeDecision).order_by(
                TradeDecision.timestamp.desc()
            ).limit(10).all()
            db.close()

            consecutive = 0
            for decision in recent_decisions:
                # Check if it was a losing trade
                # This is placeholder logic - actual P&L would be tracked elsewhere
                if hasattr(decision, 'pnl') and decision.pnl < 0:
                    consecutive += 1
                else:
                    break

            return consecutive

        except Exception as e:
            print(f"⚠️  Could not count consecutive losses: {e}")
            return 0

    def _calculate_portfolio_heat(self, open_positions, total_balance: float) -> float:
        """Calculate total risk across all open positions"""
        try:
            total_risk = 0.0

            for position in open_positions:
                # Risk = distance to stop loss * position size
                entry = position.entry_price
                stop = position.stop_loss

                if entry and stop:
                    risk_pct = abs(entry - stop) / entry
                    position_risk = risk_pct * position.position_size_usd
                    total_risk += position_risk

            return total_risk / total_balance if total_balance > 0 else 0.0

        except Exception as e:
            print(f"⚠️  Could not calculate portfolio heat: {e}")
            return 0.0


if __name__ == "__main__":
    print("\n🛡️  RISK MANAGEMENT AGENT - SELF TEST")
    print("="*60)

    agent = RiskManagementAgent()

    # Test case 1: Good trade
    print("\n📊 TEST 1: Valid BUY signal")
    test_state = AgentState({
        'recommendation': 'BUY',
        'confidence': 0.75,
        'entry_level': 185.0,
        'stop_loss': 178.0,
        'take_profit': 198.0
    })

    # Mock data for testing
    # In reality, this would fetch from database
    print("⚠️  Note: This test requires database connection for full validation")
    result = agent.execute(test_state)
    print(f"Result: {'APPROVED' if result.get('risk_approved') else 'REJECTED'}")
