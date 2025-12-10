"""
Portfolio Management Agent - Tracks positions, calculates performance metrics.
Monitors entry/exit prices, profit/loss, and portfolio health.
"""
import json
from datetime import datetime
from app.agents.base import BaseAgent, AgentState
from app.agents.llm import llm
from app.database.config import get_db_session
from app.database.models import PortfolioState, TraderAnalyst


PORTFOLIO_PROMPT = """You are a portfolio performance analyst.

PORTFOLIO SNAPSHOT:
Total Balance: ${total_balance}
Cash Available: ${cash}
SOL Holdings: {sol_held}
Current Price: ${price}
ROI: {roi}%

RECENT TRADES:
{recent_trades}

PERFORMANCE METRICS:
Win Rate: {win_rate}%
Avg Win: ${avg_win}
Avg Loss: ${avg_loss}
Profit Factor: {profit_factor}

Analyze portfolio health and provide insights. Return ONLY valid JSON:

{{
    "portfolio_health": "excellent|good|fair|poor",
    "net_worth": number,
    "buying_power": number,
    "portfolio_concentration": "low|moderate|high",
    "recommendation": "increase_size|maintain|reduce_size",
    "performance_summary": "Your analysis",
    "risk_assessment": "Your assessment"
}}"""


class PortfolioAgent(BaseAgent):
    """Agent that manages and analyzes portfolio performance"""

    def __init__(self):
        super().__init__(
            model="claude-3-5-haiku-20241022",
            temperature=0.2
        )

    def calculate_portfolio_metrics(self):
        """Calculate key portfolio performance metrics"""
        db = get_db_session()

        # Get latest portfolio state
        portfolio = db.query(PortfolioState).order_by(PortfolioState.timestamp.desc()).first()

        # Get recent trades
        trades = db.query(TraderAnalyst).order_by(TraderAnalyst.timestamp.desc()).limit(20).all()
        db.close()

        if not portfolio:
            return None

        # Calculate metrics
        total_balance = portfolio.net_worth
        cash = portfolio.cash
        sol_held = portfolio.sol_held
        roi = portfolio.roi
        price = portfolio.sol_price

        # Trade statistics
        winning_trades = [t for t in trades if t.action > 0.3]  # Positive action = profit
        losing_trades = [t for t in trades if t.action < -0.3]
        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0

        return {
            'total_balance': total_balance,
            'cash': cash,
            'sol_held': sol_held,
            'roi': roi,
            'price': price,
            'trades': trades,
            'win_rate': win_rate,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }

    def execute(self, state: AgentState) -> AgentState:
        """
        Analyze portfolio and provide insights.

        Args:
            state: Current trading state

        Returns:
            State with portfolio analysis
        """
        try:
            metrics = self.calculate_portfolio_metrics()

            if not metrics:
                state['portfolio'] = {
                    "portfolio_health": "unknown",
                    "performance_summary": "No portfolio data available",
                    "risk_assessment": "Unable to assess"
                }
                state['portfolio_analysis'] = json.dumps(state['portfolio'])
                return state

            # Build prompt
            recent_trades_text = "\n".join([
                f"- [{t.timestamp.strftime('%m-%d')}] {t.decision.upper()} "
                f"(confidence: {t.confidence:.0%}, action: {t.action:+.2f})"
                for t in metrics['trades'][:10]
            ]) if metrics['trades'] else "No trades yet"

            portfolio_prompt = PORTFOLIO_PROMPT.format(
                total_balance=f"{metrics['total_balance']:.2f}",
                cash=f"{metrics['cash']:.2f}",
                sol_held=f"{metrics['sol_held']:.2f}",
                price=f"{metrics['price']:.2f}",
                roi=f"{metrics['roi']:.2f}",
                recent_trades=recent_trades_text,
                win_rate=f"{metrics['win_rate']:.1f}",
                avg_win="N/A",
                avg_loss="N/A",
                profit_factor=f"{metrics['winning_trades'] / max(1, metrics['losing_trades']):.2f}"
            )

            response = llm(
                portfolio_prompt,
                model=self.model,
                temperature=self.temperature,
                max_tokens=400
            )

            # Parse response
            try:
                clean_response = response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.startswith("```"):
                    clean_response = clean_response[3:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]

                portfolio_data = json.loads(clean_response)
                state['portfolio'] = portfolio_data
                state['portfolio_analysis'] = json.dumps(portfolio_data)

            except (json.JSONDecodeError, ValueError):
                state['portfolio'] = {
                    "portfolio_health": "fair",
                    "performance_summary": "Portfolio tracking active",
                    "risk_assessment": "Monitor ongoing"
                }
                state['portfolio_analysis'] = json.dumps(state['portfolio'])

        except Exception as e:
            state['portfolio'] = {
                "portfolio_health": "unknown",
                "performance_summary": f"Analysis error: {str(e)[:100]}",
                "risk_assessment": "Unable to assess"
            }
            state['portfolio_analysis'] = json.dumps(state['portfolio'])

        return state
