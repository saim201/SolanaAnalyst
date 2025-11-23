import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.trading_agents import TradingGraph

if __name__ == "__main__":
    print("\n🚀 Starting Trading Agent System...\n")

    graph = TradingGraph()
    result = graph.run()

    print("\n" + "="*80)
    print("📊 FINAL DECISION")
    print("="*80)
    print(f"Decision: {result['decision'].upper()}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Action: {result['action']:.2f}")
    print(f"Reasoning: {result['reasoning']}")
    print("="*80)
