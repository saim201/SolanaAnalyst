# reflection_helpers.py

from typing import Dict, Any, Optional, List, Tuple


def get_nested(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    keys = path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default

    return current if current is not None else default


def calculate_alignment_score(
    tech_recommendation: str,
    tech_confidence: float,
    sentiment_signal: str,
    sentiment_confidence: float
) -> Tuple[str, float]:
    # Normalize recommendations to BULLISH/BEARISH/NEUTRAL
    tech_direction = normalize_direction(tech_recommendation)
    sentiment_direction = normalize_direction(sentiment_signal)

    # Calculate base alignment
    if tech_direction == sentiment_direction:
        # Both agree on direction
        if tech_direction == 'NEUTRAL':
            # Both neutral - partial alignment
            alignment_status = 'PARTIAL'
            alignment_score = 0.6
        else:
            # Both bullish or both bearish - strong alignment
            alignment_status = 'ALIGNED'
            # Score based on confidence similarity
            confidence_diff = abs(tech_confidence - sentiment_confidence)
            alignment_score = 0.95 - (confidence_diff * 0.3)  # Penalty for confidence mismatch
            alignment_score = max(0.85, min(1.0, alignment_score))

    elif tech_direction == 'NEUTRAL' or sentiment_direction == 'NEUTRAL':
        # One is neutral, other is directional - partial
        alignment_status = 'PARTIAL'
        alignment_score = 0.5 + (min(tech_confidence, sentiment_confidence) * 0.2)
        alignment_score = max(0.4, min(0.7, alignment_score))

    else:
        # Opposite directions - conflict
        alignment_status = 'CONFLICTED'
        # Higher confidence in conflict = lower alignment
        avg_confidence = (tech_confidence + sentiment_confidence) / 2
        alignment_score = 0.3 - (avg_confidence * 0.3)
        alignment_score = max(0.0, min(0.3, alignment_score))

    return alignment_status, round(alignment_score, 2)


def normalize_direction(signal: str) -> str:
    signal_upper = signal.upper()

    bullish_signals = ['BUY', 'BULLISH', 'STRONG_BULLISH', 'SLIGHTLY_BULLISH', 'CAUTIOUSLY_BULLISH']
    bearish_signals = ['SELL', 'BEARISH', 'STRONG_BEARISH', 'SLIGHTLY_BEARISH', 'CAUTIOUSLY_BEARISH']

    if any(s in signal_upper for s in bullish_signals):
        return 'BULLISH'
    elif any(s in signal_upper for s in bearish_signals):
        return 'BEARISH'
    else:
        return 'NEUTRAL'


def calculate_bayesian_confidence(
    tech_confidence: float,
    sentiment_confidence: float,
    alignment_score: float,
    risk_level: str,
    volume_ratio: float = 1.0,
    btc_correlation: float = 0.0,
    btc_trend: str = 'NEUTRAL',
    cfgi_score: float = 50.0,
    price_position_14d: float = 0.5,
    additional_adjustments: Optional[List[Tuple[str, float]]] = None
) -> Dict[str, Any]:
    """
    Calculate final confidence using Bayesian weighted fusion.

    Args:
        tech_confidence: Technical agent confidence (0.0-1.0)
        sentiment_confidence: Sentiment agent confidence (0.0-1.0)
        alignment_score: Alignment between agents (0.0-1.0)
        risk_level: LOW, MEDIUM, or HIGH
        volume_ratio: Current volume / average volume
        btc_correlation: SOL-BTC correlation (0.0-1.0)
        btc_trend: BTC trend (BULLISH/BEARISH/NEUTRAL)
        cfgi_score: Fear & Greed Index (0-100)
        price_position_14d: Position in 14d range (0=low, 1=high)
        additional_adjustments: List of (description, value) tuples

    Returns:
        Dict with base_confidence, adjustments, final_confidence, methodology, interpretation
    """
    # Step 1: Start with lower confidence (conservative)
    base_confidence = min(tech_confidence, sentiment_confidence)

    # Step 2: Calculate adjustments
    adjustments = []
    total_adjustment = 0.0

    # Alignment bonus
    if alignment_score >= 0.75:
        bonus = 0.10 + (alignment_score - 0.75) * 0.2  # 0.10 to 0.15
        adjustments.append(f"+{bonus:.2f} alignment bonus (both agree)")
        total_adjustment += bonus
    elif alignment_score < 0.4:
        penalty = -0.15 - (0.4 - alignment_score) * 0.2  # -0.15 to -0.20
        adjustments.append(f"{penalty:.2f} conflict penalty (agents disagree)")
        total_adjustment += penalty

    # Risk penalty
    risk_penalties = {
        'LOW': 0.0,
        'MEDIUM': -0.10,
        'HIGH': -0.18
    }
    risk_penalty = risk_penalties.get(risk_level, -0.10)
    if risk_penalty != 0:
        adjustments.append(f"{risk_penalty:.2f} risk penalty ({risk_level} risk)")
        total_adjustment += risk_penalty

    # Volume penalty (CRITICAL)
    if volume_ratio < 0.7:
        volume_penalty = -0.25
        adjustments.append(f"{volume_penalty:.2f} CRITICAL volume penalty (DEAD <0.7x)")
        total_adjustment += volume_penalty
    elif volume_ratio < 1.0:
        volume_penalty = -0.08
        adjustments.append(f"{volume_penalty:.2f} volume penalty (weak <1.0x)")
        total_adjustment += volume_penalty

    # BTC correlation risk (NEW)
    if btc_correlation > 0.8:
        if btc_trend == 'BEARISH':
            btc_penalty = -0.12
            adjustments.append(f"{btc_penalty:.2f} BTC risk (high correlation + bearish BTC)")
            total_adjustment += btc_penalty
        elif btc_trend == 'BULLISH':
            btc_bonus = 0.05
            adjustments.append(f"+{btc_bonus:.2f} BTC support (high correlation + bullish BTC)")
            total_adjustment += btc_bonus

    # CFGI extreme signals (NEW - contrarian)
    if cfgi_score < 20:  # Extreme fear
        cfgi_bonus = 0.08
        adjustments.append(f"+{cfgi_bonus:.2f} extreme fear bonus (contrarian buy signal)")
        total_adjustment += cfgi_bonus
    elif cfgi_score > 80:  # Extreme greed
        cfgi_penalty = -0.08
        adjustments.append(f"{cfgi_penalty:.2f} extreme greed penalty (contrarian sell signal)")
        total_adjustment += cfgi_penalty

    # Price position risk (NEW)
    if price_position_14d > 0.95:  # Near 14d high
        position_penalty = -0.05
        adjustments.append(f"{position_penalty:.2f} price position risk (near 14d high)")
        total_adjustment += position_penalty
    elif price_position_14d < 0.05:  # Near 14d low
        position_bonus = 0.05
        adjustments.append(f"+{position_bonus:.2f} price position bonus (near 14d low)")
        total_adjustment += position_bonus

    # Additional adjustments
    if additional_adjustments:
        for description, value in additional_adjustments:
            adjustments.append(f"{value:+.2f} {description}")
            total_adjustment += value

    # Step 3: Calculate final confidence
    final_confidence = base_confidence + total_adjustment
    final_confidence = max(0.0, min(1.0, final_confidence))  # Clamp to [0, 1]

    # Step 4: Interpret confidence level
    if final_confidence < 0.4:
        interpretation = "LOW - high uncertainty, consider waiting"
    elif final_confidence < 0.7:
        interpretation = "MODERATE - directional edge exists but execution risk elevated"
    else:
        interpretation = "HIGH - strong conviction, favorable setup"

    return {
        'base_confidence': round(base_confidence, 2),
        'adjustments': adjustments,
        'final_confidence': round(final_confidence, 2),
        'methodology': "Bayesian weighted fusion: start with lower confidence, adjust for alignment and risk",
        'interpretation': interpretation
    }


def assess_risk_level(
    volume_ratio: float,
    alignment_score: float,
    tech_analysis: Dict[str, Any],
    sentiment_data: Dict[str, Any],
    btc_correlation: float = 0.0,
    btc_trend: str = 'NEUTRAL',
    price_position_14d: float = 0.5,
    rsi_divergence_type: str = 'NONE',
    rsi_divergence_strength: float = 0.0
) -> Tuple[str, List[str]]:
    """
    Assess overall risk level based on multiple factors.

    Returns:
        (risk_level, secondary_risks)
    """
    risk_factors = []
    risk_score = 0.0

    # Volume risk (most critical)
    if volume_ratio < 0.7:
        risk_factors.append("DEAD volume (<0.7x) - signals unreliable")
        risk_score += 0.4
    elif volume_ratio < 1.0:
        risk_factors.append("Weak volume (<1.0x) - lacks conviction")
        risk_score += 0.2

    # Alignment risk
    if alignment_score < 0.4:
        risk_factors.append("Agent conflict - technical vs sentiment disagree")
        risk_score += 0.3
    elif alignment_score < 0.7:
        risk_factors.append("Partial alignment - some uncertainty")
        risk_score += 0.15

    # Technical analysis risk
    volume_quality = get_nested(tech_analysis, 'analysis.volume.quality', 'ACCEPTABLE')
    if volume_quality in ['WEAK', 'DEAD']:
        risk_factors.append(f"Technical flags {volume_quality} volume quality")
        risk_score += 0.15

    # Sentiment risk flags
    risk_flags = sentiment_data.get('risk_flags', [])
    if risk_flags:
        risk_factors.extend([f"Sentiment: {flag}" for flag in risk_flags[:2]])
        risk_score += 0.1 * len(risk_flags[:2])

    # BTC correlation risk (NEW)
    if btc_correlation > 0.8 and btc_trend == 'BEARISH':
        risk_factors.append(f"High BTC correlation ({btc_correlation:.2f}) + bearish BTC trend")
        risk_score += 0.25

    # Price position risk (NEW)
    if price_position_14d > 0.95:
        risk_factors.append("Price near 14d high - limited upside, pullback risk")
        risk_score += 0.15
    elif price_position_14d < 0.05:
        risk_factors.append("Price near 14d low - downside momentum risk")
        risk_score += 0.10

    # RSI divergence risk (NEW)
    if rsi_divergence_type == 'BEARISH' and rsi_divergence_strength > 0.5:
        risk_factors.append(f"Bearish RSI divergence (strength: {rsi_divergence_strength:.2f})")
        risk_score += 0.15
    elif rsi_divergence_type == 'BULLISH' and rsi_divergence_strength > 0.5:
        # Bullish divergence reduces risk slightly
        risk_score = max(0, risk_score - 0.05)

    # Determine risk level
    if risk_score >= 0.5:
        risk_level = 'HIGH'
    elif risk_score >= 0.25:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    # Get secondary risks (up to 3 most important)
    secondary_risks = risk_factors[:3] if len(risk_factors) > 1 else risk_factors

    return risk_level, secondary_risks


def format_thinking_phases(phases: Dict[str, str]) -> str:

    formatted = []
    for phase_name, content in phases.items():
        # Convert snake_case to Title Case
        title = phase_name.replace('_', ' ').title()
        formatted.append(f"=== {title} ===\n{content.strip()}")

    return "\n\n".join(formatted)


if __name__ == "__main__":
    # Test get_nested
    tech = {
        'trade_setup': {
            'entry': 184.50,
            'stop_loss': 178.00
        }
    }
    print(get_nested(tech, 'trade_setup.entry'))  # 184.50
    print(get_nested(tech, 'trade_setup.missing', 0.0))  # 0.0

    # Test alignment calculation
    status, score = calculate_alignment_score('BUY', 0.72, 'BULLISH', 0.65)
    print(f"Alignment: {status} ({score})")

    # Test confidence calculation
    result = calculate_bayesian_confidence(
        tech_confidence=0.72,
        sentiment_confidence=0.65,
        alignment_score=0.85,
        risk_level='MEDIUM',
        volume_ratio=0.82
    )
    print(f"Final confidence: {result['final_confidence']}")
    print(f"Adjustments: {result['adjustments']}")
