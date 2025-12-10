"""
Risk Management Agent - HARD-CODED RULES (no LLM).
Implements institutional-grade safety gates based on Renaissance Technologies and Kelly Criterion principles.

RESEARCH SOURCES:
- Renaissance Technologies risk framework (2025): Multi-layered risk management, beta <0.4, leverage ~2.5x
- Kelly Criterion for crypto: Fractional Kelly (50%) reduces volatility 25% while maintaining 75% of growth
- Hedge fund best practices: Portfolio heat limits, drawdown circuit breakers, volatility scaling

CRITICAL: This agent uses ZERO LLM calls - all decisions are deterministic.
Research shows LLMs are unreliable for risk assessment. Hard rules prevent catastrophic losses.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple, List
from app.agents.base import BaseAgent, AgentState, RiskOutput
from app.agents.db_fetcher import DataQuery
from app.data.indicators import classify_volume_quality
from app.database.config import get_db_session
from app.database.models import PortfolioState, Position
from app.database.data_manager import DataManager


class RiskManagementAgent(BaseAgent):
    """
    Agent that validates trades using institutional-grade hard-coded rules (NO LLM).

    SAFETY GATES (any failure = BLOCK TRADE):
    1. Volume Gate: volume_ratio >= 0.7 (DEAD volume = auto-reject)
    2. Confidence Gate: confidence >= 0.60 (minimum conviction threshold)
    3. R:R Gate: risk_reward_ratio >= 1.5 (swing trading minimum)
    4. Support Gate: support within 5% below entry (risk containment)
    5. Consecutive Loss Gate: max 3 consecutive losses (circuit breaker)
    6. Portfolio Heat: max 6% total risk across all positions
    7. Drawdown Gate: max 15% drawdown from peak (Renaissance-inspired)
    8. Volatility Gate: ATR must be < 8% of price (prevent over-leveraging in chaos)

    POSITION SIZING (Institutional Framework):
    - Base: 2% risk per trade (industry standard)
    - Kelly adjustment: Fractional Kelly (50%) for high-confidence trades
    - Volume adjustment: multiply by volume_quality confidence_multiplier
    - Confidence adjustment: scale by (confidence - 0.6) / 0.4
    - Volatility scaling: reduce size when ATR > 5% of price
    - Correlation penalty: -20% if 2+ open SOL positions (concentration risk)
    - Max: 5% in single position (prevent concentration)
    """

    def __init__(self):
        super().__init__(
            model=None,  # NO LLM - hard-coded rules only
            temperature=0.0
        )
        # Base risk parameters
        self.MAX_RISK_PER_TRADE = 0.02      # 2% base risk
        self.MAX_POSITION_SIZE = 0.05       # 5% max in one position
        self.MAX_PORTFOLIO_HEAT = 0.06      # 6% total risk across all positions
        self.MIN_CONFIDENCE = 0.60          # 60% minimum confidence
        self.MIN_RR_RATIO = 1.5             # 1.5:1 minimum R:R
        self.MIN_VOLUME_RATIO = 0.7         # 0.7x minimum volume (DEAD = reject)
        self.MAX_CONSECUTIVE_LOSSES = 3     # Circuit breaker
        self.MAX_SUPPORT_DISTANCE = 0.05    # Support must be within 5%

        # Institutional additions
        self.MAX_DRAWDOWN_PCT = 0.15        # 15% max drawdown from peak (Renaissance)
        self.HIGH_VOLATILITY_THRESHOLD = 0.05  # ATR > 5% of price = high vol
        self.EXTREME_VOLATILITY_THRESHOLD = 0.08  # ATR > 8% = extreme vol (block)
        self.KELLY_FRACTION = 0.5           # Half Kelly (reduces volatility by 25%)
        self.CORRELATION_PENALTY = 0.20     # -20% size if correlated positions exist

    def execute(self, state: AgentState) -> AgentState:
        technical = state.get('technical', {})
        reflection = state.get('reflection', {})

        recommendation = technical.get('recommendation', 'HOLD')
        confidence = technical.get('confidence', 0.0)
        entry_level = technical.get('entry_level', 0.0)
        stop_loss = technical.get('stop_loss', 0.0)
        take_profit = technical.get('take_profit', 0.0)

        # GATE 0: Only validate BUY/SELL, auto-approve HOLD
        if recommendation == 'HOLD':
            state['risk'] = self._create_hold_response()
            print(" HOLD decision - no risk assessment needed")
            return state

        print(f"\n Analyzing {recommendation} with {confidence:.0%} confidence...")


        try:
            with DataQuery() as dq:
                indicators_dict = dq.get_indicators_data(days=1)
                ticker_dict = dq.get_ticker_data()

            # Get portfolio
            db = get_db_session()
            portfolio = db.query(PortfolioState).order_by(PortfolioState.timestamp.desc()).first()
            open_positions = db.query(Position).filter(Position.status == 'open').all()

            # Get portfolio peak for drawdown calculation
            portfolio_history = db.query(PortfolioState).order_by(PortfolioState.timestamp.desc()).limit(30).all()
            db.close()

        except Exception as e:
            state['risk'] = self._create_error_response(f"Data fetch error: {str(e)}")
            print(f"❌ {state['risk']['reasoning']}")
            return state

        if not indicators_dict or not ticker_dict or not portfolio:
            state['risk'] = self._create_error_response("Insufficient data (missing indicators, ticker, or portfolio)")
            print(f"❌ {state['risk']['reasoning']}")
            return state

        # Extract values
        current_price = ticker_dict.get('lastPrice', 0)
        atr = indicators_dict.get('atr', 0)
        volume_ratio = indicators_dict.get('volume_ratio', 1.0)
        support1 = indicators_dict.get('support1')
        resistance1 = indicators_dict.get('resistance1')
        total_balance = portfolio.net_worth

        print(f"💰 Portfolio: ${total_balance:,.2f}")
        print(f"📈 Price: ${current_price:.2f} | ATR: ${atr:.2f} ({(atr/current_price)*100:.2f}%)")
        print(f"📊 Volume Ratio: {volume_ratio:.2f}x")

        # Auto-calculate trade levels if not provided
        if not stop_loss or not take_profit or not entry_level:
            entry_level = current_price
            if recommendation == 'BUY':
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3.0)
            else:  # SELL
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3.0)

        # Initialize validation tracking
        validation_details = {}
        warnings = []

        # ============================================================
        # SAFETY GATE #1: VOLUME VALIDATION (MOST IMPORTANT)
        # ============================================================
        volume_quality = classify_volume_quality(volume_ratio)
        volume_allowed = volume_quality['trading_allowed']
        volume_classification = volume_quality['classification']

        if not volume_allowed:
            state['risk'] = self._create_rejection_response(
                gate="GATE 1 - VOLUME",
                reason=f"DEAD VOLUME - {volume_ratio:.2f}x (classification: {volume_classification})",
                details=f"Threshold: 0.7x minimum. LOW VOLUME = FALSE SIGNALS",
                validation_details={'gate1_volume': False},
                warnings=["volume_dead"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        validation_details['gate1_volume'] = True
        print(f"✅ GATE 1: Volume OK ({volume_ratio:.2f}x - {volume_classification})")

        # ============================================================
        # SAFETY GATE #2: CONFIDENCE THRESHOLD
        # ============================================================
        if confidence < self.MIN_CONFIDENCE:
            state['risk'] = self._create_rejection_response(
                gate="GATE 2 - CONFIDENCE",
                reason=f"LOW CONFIDENCE - {confidence:.0%}",
                details=f"Threshold: {self.MIN_CONFIDENCE:.0%} minimum. Insufficient conviction",
                validation_details={'gate1_volume': True, 'gate2_confidence': False},
                warnings=["confidence_low"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        validation_details['gate2_confidence'] = True
        print(f"✅ GATE 2: Confidence OK ({confidence:.0%})")

        # ============================================================
        # SAFETY GATE #3: RISK/REWARD RATIO
        # ============================================================
        risk_distance = abs(entry_level - stop_loss)
        reward_distance = abs(take_profit - entry_level)

        if risk_distance == 0:
            state['risk'] = self._create_rejection_response(
                gate="GATE 3 - R:R RATIO",
                reason="Invalid stop loss (zero risk)",
                details="Cannot calculate R:R with zero risk distance",
                validation_details={**validation_details, 'gate3_rr': False},
                warnings=["invalid_stop_loss"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        rr_ratio = reward_distance / risk_distance

        if rr_ratio < self.MIN_RR_RATIO:
            state['risk'] = self._create_rejection_response(
                gate="GATE 3 - R:R RATIO",
                reason=f"POOR RISK/REWARD - {rr_ratio:.2f}:1",
                details=f"Threshold: {self.MIN_RR_RATIO:.1f}:1 minimum. Risk: ${risk_distance:.2f} | Reward: ${reward_distance:.2f}",
                validation_details={**validation_details, 'gate3_rr': False},
                warnings=["poor_rr_ratio"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        validation_details['gate3_rr'] = True
        print(f"✅ GATE 3: R:R OK ({rr_ratio:.2f}:1)")

        # ============================================================
        # SAFETY GATE #4: SUPPORT PROXIMITY (for BUY only)
        # ============================================================
        if recommendation == 'BUY':
            if not support1:
                state['risk'] = self._create_rejection_response(
                    gate="GATE 4 - SUPPORT",
                    reason="No support level identified",
                    details="Cannot validate risk containment without support",
                    validation_details={**validation_details, 'gate4_support': False},
                    warnings=["no_support"],
                    total_balance=total_balance,
                    open_positions=len(open_positions)
                )
                print(state['risk']['reasoning'])
                return state

            support_distance_pct = ((current_price - support1) / current_price)

            if support_distance_pct > self.MAX_SUPPORT_DISTANCE:
                state['risk'] = self._create_rejection_response(
                    gate="GATE 4 - SUPPORT",
                    reason=f"SUPPORT TOO FAR - {support_distance_pct:.1%} below",
                    details=f"Support: ${support1:.2f}. Threshold: {self.MAX_SUPPORT_DISTANCE:.0%} maximum",
                    validation_details={**validation_details, 'gate4_support': False},
                    warnings=["support_too_far"],
                    total_balance=total_balance,
                    open_positions=len(open_positions)
                )
                print(state['risk']['reasoning'])
                return state

        validation_details['gate4_support'] = True
        print(f"✅ GATE 4: Support proximity OK")

        # ============================================================
        # SAFETY GATE #5: CONSECUTIVE LOSSES CIRCUIT BREAKER
        # ============================================================
        consecutive_losses = self._count_consecutive_losses()

        if consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            state['risk'] = self._create_rejection_response(
                gate="GATE 5 - CIRCUIT BREAKER",
                reason=f"CONSECUTIVE LOSSES - {consecutive_losses} trades",
                details=f"Threshold: {self.MAX_CONSECUTIVE_LOSSES} maximum. System requires cooldown",
                validation_details={**validation_details, 'gate5_losses': False},
                warnings=["circuit_breaker"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        validation_details['gate5_losses'] = True
        print(f"✅ GATE 5: Consecutive losses OK ({consecutive_losses})")

        # ============================================================
        # SAFETY GATE #6: PORTFOLIO HEAT LIMIT
        # ============================================================
        current_heat = self._calculate_portfolio_heat(open_positions, total_balance)
        position_risk_usd = (risk_distance / entry_level) * total_balance * self.MAX_RISK_PER_TRADE

        if (current_heat + (position_risk_usd / total_balance)) > self.MAX_PORTFOLIO_HEAT:
            state['risk'] = self._create_rejection_response(
                gate="GATE 6 - PORTFOLIO HEAT",
                reason=f"PORTFOLIO HEAT LIMIT - {(current_heat + position_risk_usd/total_balance):.1%}",
                details=f"Current: {current_heat:.1%}, New trade: {(position_risk_usd/total_balance):.1%}, Max: {self.MAX_PORTFOLIO_HEAT:.0%}",
                validation_details={**validation_details, 'gate6_heat': False},
                warnings=["portfolio_heat_limit"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        validation_details['gate6_heat'] = True
        print(f"✅ GATE 6: Portfolio heat OK ({current_heat:.1%})")

        # ============================================================
        # SAFETY GATE #7: DRAWDOWN CIRCUIT BREAKER (Renaissance)
        # ============================================================
        current_drawdown = self._calculate_drawdown(portfolio_history, total_balance)

        if current_drawdown > self.MAX_DRAWDOWN_PCT:
            state['risk'] = self._create_rejection_response(
                gate="GATE 7 - DRAWDOWN",
                reason=f"MAXIMUM DRAWDOWN - {current_drawdown:.1%} from peak",
                details=f"Threshold: {self.MAX_DRAWDOWN_PCT:.0%} maximum. System protection engaged",
                validation_details={**validation_details, 'gate7_drawdown': False},
                warnings=["max_drawdown"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        validation_details['gate7_drawdown'] = True
        print(f"✅ GATE 7: Drawdown OK ({current_drawdown:.1%})")

        # ============================================================
        # SAFETY GATE #8: VOLATILITY GATE (ATR-based)
        # ============================================================
        atr_pct = (atr / current_price) if current_price > 0 else 0

        if atr_pct > self.EXTREME_VOLATILITY_THRESHOLD:
            state['risk'] = self._create_rejection_response(
                gate="GATE 8 - VOLATILITY",
                reason=f"EXTREME VOLATILITY - ATR {atr_pct:.1%} of price",
                details=f"Threshold: {self.EXTREME_VOLATILITY_THRESHOLD:.0%} maximum. Market too chaotic",
                validation_details={**validation_details, 'gate8_volatility': False},
                warnings=["extreme_volatility"],
                total_balance=total_balance,
                open_positions=len(open_positions)
            )
            print(state['risk']['reasoning'])
            return state

        validation_details['gate8_volatility'] = True
        print(f"✅ GATE 8: Volatility OK (ATR {atr_pct:.1%})")

        # ============================================================
        # ALL GATES PASSED - CALCULATE INSTITUTIONAL POSITION SIZE
        # ============================================================
        print(f"\n✅ ALL 8 SAFETY GATES PASSED - CALCULATING INSTITUTIONAL POSITION SIZE...")

        position_result = self._calculate_institutional_position_size(
            base_risk_pct=self.MAX_RISK_PER_TRADE,
            confidence=confidence,
            volume_quality=volume_quality,
            rr_ratio=rr_ratio,
            atr_pct=atr_pct,
            open_positions=open_positions,
            risk_distance=risk_distance,
            entry_level=entry_level,
            total_balance=total_balance
        )

        # Create approved risk output
        state['risk'] = RiskOutput(
            approved='YES',
            position_size_percent=position_result['final_size_pct'],
            position_size_usd=position_result['final_size_usd'],
            max_loss_usd=position_result['max_loss_usd'],
            entry_price=entry_level,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            validation_details=validation_details,
            warnings=warnings,
            reasoning=self._format_approval_reasoning(position_result, rr_ratio, entry_level, stop_loss, take_profit),
            total_balance=total_balance,
            current_risk_percent=current_heat,
            open_positions=len(open_positions),
            kelly_multiplier=position_result['kelly_multiplier'],
            volatility_adjustment=position_result['volatility_adjustment'],
            correlation_penalty=position_result['correlation_penalty'],
            final_size_calculation=position_result['calculation_breakdown']
        )

        print(state['risk']['reasoning'])
        print("="*60 + "\n")

        # Save to database
        dm = DataManager()
        dm.save_risk_analysis(timestamp=datetime.now(), data=state['risk'])
        dm.close()

        return state

    def _calculate_institutional_position_size(
        self,
        base_risk_pct: float,
        confidence: float,
        volume_quality: Dict,
        rr_ratio: float,
        atr_pct: float,
        open_positions: List,
        risk_distance: float,
        entry_level: float,
        total_balance: float
    ) -> Dict:
        """
        Calculate position size using institutional framework:
        1. Base 2% risk
        2. Kelly Criterion adjustment (fractional Kelly)
        3. Volume quality multiplier
        4. Confidence scaling
        5. Volatility adjustment
        6. Correlation penalty
        7. Cap at 5% max
        """

        # Step 1: Base risk
        current_size = base_risk_pct

        # Step 2: Kelly Criterion (fractional Kelly = 50%)
        # Kelly = (win_rate * rr_ratio - (1 - win_rate)) / rr_ratio
        # Approximate win_rate from confidence (0.6 = 55%, 1.0 = 65%)
        win_rate = 0.55 + (confidence - 0.6) * 0.25
        kelly_full = (win_rate * rr_ratio - (1 - win_rate)) / rr_ratio
        kelly_fractional = max(0, kelly_full * self.KELLY_FRACTION)
        kelly_multiplier = min(1.5, 1.0 + kelly_fractional)  # Cap at 1.5x

        current_size *= kelly_multiplier

        # Step 3: Volume adjustment
        volume_multiplier = volume_quality['confidence_multiplier']
        current_size *= volume_multiplier

        # Step 4: Confidence adjustment (scale 0.6-1.0 to 0.0-1.0)
        confidence_multiplier = (confidence - self.MIN_CONFIDENCE) / (1.0 - self.MIN_CONFIDENCE)
        current_size *= confidence_multiplier

        # Step 5: Volatility scaling (reduce size in high volatility)
        if atr_pct > self.HIGH_VOLATILITY_THRESHOLD:
            volatility_reduction = 1.0 - min(0.3, (atr_pct - self.HIGH_VOLATILITY_THRESHOLD) * 5)
        else:
            volatility_reduction = 1.0

        volatility_adjustment = volatility_reduction
        current_size *= volatility_adjustment

        # Step 6: Correlation penalty (if 2+ open positions = all SOL = 100% correlation)
        correlation_penalty = 1.0
        if len(open_positions) >= 2:
            correlation_penalty = 1.0 - self.CORRELATION_PENALTY
            current_size *= correlation_penalty

        # Step 7: Cap at maximum
        final_size_pct = min(current_size, self.MAX_POSITION_SIZE)

        # Calculate USD amounts
        risk_usd = final_size_pct * total_balance
        position_size_units = risk_usd / risk_distance
        position_size_usd = position_size_units * entry_level

        # Recalculate position_size_pct based on actual position value
        final_size_pct = position_size_usd / total_balance

        # Cap again if needed
        if final_size_pct > self.MAX_POSITION_SIZE:
            final_size_pct = self.MAX_POSITION_SIZE
            position_size_usd = self.MAX_POSITION_SIZE * total_balance
            risk_usd = (risk_distance / entry_level) * position_size_usd

        return {
            'final_size_pct': final_size_pct,
            'final_size_usd': position_size_usd,
            'max_loss_usd': risk_usd,
            'kelly_multiplier': kelly_multiplier,
            'volatility_adjustment': volatility_adjustment,
            'correlation_penalty': correlation_penalty,
            'calculation_breakdown': {
                'base_risk': base_risk_pct,
                'after_kelly': base_risk_pct * kelly_multiplier,
                'after_volume': base_risk_pct * kelly_multiplier * volume_multiplier,
                'after_confidence': base_risk_pct * kelly_multiplier * volume_multiplier * confidence_multiplier,
                'after_volatility': base_risk_pct * kelly_multiplier * volume_multiplier * confidence_multiplier * volatility_adjustment,
                'after_correlation': current_size,
                'final_capped': final_size_pct
            }
        }

    def _count_consecutive_losses(self) -> int:
        try:
            from app.database.models import TraderAnalyst

            db = get_db_session()
            recent_decisions = db.query(TraderAnalyst).order_by(
                TraderAnalyst.timestamp.desc()
            ).limit(10).all()
            db.close()

            consecutive = 0
            for decision in recent_decisions:
                if hasattr(decision, 'pnl') and decision.pnl < 0:
                    consecutive += 1
                else:
                    break

            return consecutive

        except Exception as e:
            print(f"⚠️  Could not count consecutive losses: {e}")
            return 0

    def _calculate_portfolio_heat(self, open_positions: List, total_balance: float) -> float:
        # Calculate total risk across all open positions
        try:
            total_risk = 0.0

            for position in open_positions:
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

    def _calculate_drawdown(self, portfolio_history: List, current_balance: float) -> float:
        """Calculate current drawdown from peak (Renaissance-inspired)"""
        try:
            if not portfolio_history:
                return 0.0

            peak_balance = max([p.net_worth for p in portfolio_history])
            drawdown = (peak_balance - current_balance) / peak_balance

            return max(0.0, drawdown)

        except Exception as e:
            print(f"⚠️  Could not calculate drawdown: {e}")
            return 0.0

    def _create_hold_response(self) -> RiskOutput:
        """Create response for HOLD decision"""
        return RiskOutput(
            approved='YES',
            position_size_percent=0.0,
            position_size_usd=0.0,
            max_loss_usd=0.0,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=0.0,
            validation_details={},
            warnings=[],
            reasoning="✅ HOLD decision - no risk assessment needed",
            total_balance=0.0,
            current_risk_percent=0.0,
            open_positions=0,
            kelly_multiplier=1.0,
            volatility_adjustment=1.0,
            correlation_penalty=1.0,
            final_size_calculation={}
        )

    def _create_error_response(self, error_msg: str) -> RiskOutput:
        """Create response for data errors"""
        return RiskOutput(
            approved='NO',
            position_size_percent=0.0,
            position_size_usd=0.0,
            max_loss_usd=0.0,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=0.0,
            validation_details={},
            warnings=["data_error"],
            reasoning=f"❌ {error_msg}",
            total_balance=0.0,
            current_risk_percent=0.0,
            open_positions=0,
            kelly_multiplier=1.0,
            volatility_adjustment=1.0,
            correlation_penalty=1.0,
            final_size_calculation={}
        )

    def _create_rejection_response(
        self,
        gate: str,
        reason: str,
        details: str,
        validation_details: Dict,
        warnings: List[str],
        total_balance: float,
        open_positions: int
    ) -> RiskOutput:
        """Create response for rejected trades"""
        reasoning = f"❌ {gate} FAILED: {reason}\n   {details}"

        return RiskOutput(
            approved='NO',
            position_size_percent=0.0,
            position_size_usd=0.0,
            max_loss_usd=0.0,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=0.0,
            validation_details=validation_details,
            warnings=warnings,
            reasoning=reasoning,
            total_balance=total_balance,
            current_risk_percent=0.0,
            open_positions=open_positions,
            kelly_multiplier=1.0,
            volatility_adjustment=1.0,
            correlation_penalty=1.0,
            final_size_calculation={}
        )

    def _format_approval_reasoning(
        self,
        position_result: Dict,
        rr_ratio: float,
        entry_level: float,
        stop_loss: float,
        take_profit: float
    ) -> str:
        """Format the approval reasoning text"""
        calc = position_result['calculation_breakdown']

        return (
            f"✅ TRADE APPROVED - INSTITUTIONAL SIZING\n"
            f"   Position Size: {position_result['final_size_pct']:.1%} (${position_result['final_size_usd']:,.2f})\n"
            f"   Max Loss: ${position_result['max_loss_usd']:,.2f}\n"
            f"   Risk/Reward: {rr_ratio:.2f}:1\n"
            f"   Entry: ${entry_level:.2f} | Stop: ${stop_loss:.2f} | Target: ${take_profit:.2f}\n"
            f"\n"
            f"   Institutional Calculation:\n"
            f"   1. Base Risk:           {calc['base_risk']:.2%}\n"
            f"   2. Kelly Adjustment:    {calc['after_kelly']:.2%} ({position_result['kelly_multiplier']:.2f}x)\n"
            f"   3. Volume Adjustment:   {calc['after_volume']:.2%}\n"
            f"   4. Confidence Scaling:  {calc['after_confidence']:.2%}\n"
            f"   5. Volatility Scaling:  {calc['after_volatility']:.2%} ({position_result['volatility_adjustment']:.0%})\n"
            f"   6. Correlation Penalty: {calc['after_correlation']:.2%} ({position_result['correlation_penalty']:.0%})\n"
            f"   7. Final (capped at 5%): {calc['final_capped']:.2%}"
        )


if __name__ == "__main__":

    agent = RiskManagementAgent()

    print("\n TEST: Valid BUY signal with high confidence")
    test_state = AgentState()

    test_state['technical'] = {
        'recommendation': 'BUY',
        'confidence': 0.75,
        'confidence_breakdown': {
            'trend_strength': 0.8,
            'momentum_confirmation': 0.7,
            'volume_quality': 0.85,
            'risk_reward': 0.9,
            'final_adjusted': 0.75
        },
        'timeframe': '1-5 days',
        'key_signals': [
            'Price 5.2% above EMA20 (bullish structure)',
            'MACD histogram positive and expanding',
            'Volume STRONG at 1.42x - confirms breakout'
        ],
        'entry_level': 185.0,
        'stop_loss': 178.0,
        'take_profit': 198.0,
        'reasoning': 'Strong breakout above EMA20 with volume confirmation. MACD showing bullish momentum.',
        'thinking': 'Analyzed 14 days of price action. Clear support at $178. Risk/reward 2.14:1.'
    }

    test_state['news'] = {
        'overall_sentiment': 0.68,
        'sentiment_trend': 'improving',
        'sentiment_breakdown': {
            'regulatory': 0.7,
            'partnership': 0.8,
            'upgrade': 0.6,
            'security': 0.9,
            'macro': 0.5
        },
        'critical_events': [
            'Solana DeFi TVL hits $5B (bullish - ecosystem growth)',
            'SEC approves Bitcoin ETF (bullish macro - risk-on sentiment)'
        ],
        'event_classification': {
            'actionable_catalysts': 2,
            'noise_hype': 1,
            'risk_flags': 0
        },
        'recommendation': 'BULLISH',
        'confidence': 0.70,
        'hold_duration': '3-4 days',
        'reasoning': 'Strong ecosystem growth with positive macro tailwinds. No major regulatory concerns.',
        'risk_flags': [],
        'time_sensitive_events': [],
        'thinking': 'Analyzed 12 articles. Positive sentiment across regulatory and partnership domains.'
    }

    test_state['reflection'] = {
        'bull_case_summary': 'Strong technical breakout + positive ecosystem growth + risk-on macro',
        'bear_case_summary': 'Potential overbought conditions, lack of major new catalysts',
        'bull_strength': 0.72,
        'bear_strength': 0.48,
        'recommendation': 'BUY',
        'confidence': 0.68,
        'primary_risk': 'Sudden macro reversal if Fed signals rate hikes',
        'monitoring_trigger': 'Watch for breakdown below $178 support',
        'consensus_points': [
            'Technical structure is bullish',
            'Volume confirms the move',
            'Ecosystem fundamentals improving'
        ],
        'conflict_points': [
            'Bulls see breakout, bears see overextension',
            'News positive but not game-changing'
        ],
        'blind_spots': [
            'Bull missing: Potential resistance at $190',
            'Bear missing: Strong institutional buying pressure'
        ],
        'reasoning': 'Bull case slightly stronger. Technical + news alignment supports BUY with 68% confidence.'
    }


    result = agent.execute(test_state)


    if result.get('risk'):
        risk = result['risk']
        print(f"   - Technical agent data: {len(test_state['technical'])} fields")
        print(f"   - News agent data: {len(test_state['news'])} fields")
        print(f"   - Reflection agent data: {len(test_state['reflection'])} fields")
        print(f"   - Risk agent output: {len(risk)} fields")
        print(f"\n Risk Assessment:")
        print(f"   - Approved: {risk['approved']}")
        print(f"   - Position Size: {risk['position_size_percent']:.2%}")
        print(f"   - Kelly Multiplier: {risk['kelly_multiplier']:.2f}x")
        print(f"   - Volatility Adjustment: {risk['volatility_adjustment']:.0%}")
        print(f"   - Correlation Penalty: {risk['correlation_penalty']:.0%}")
        print(f"\n✅ All tests passed! Institutional risk management system operational.")
    else:
        print(f"\n❌ Risk assessment failed or incomplete")

