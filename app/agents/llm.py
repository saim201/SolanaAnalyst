import sys
import os
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_random_exponential
from typing import Literal

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # ✅ FIXED
client = Anthropic(api_key=ANTHROPIC_API_KEY)
Model = Literal["claude-sonnet-4-5-20250929", "claude-3-5-haiku-20241022"]

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def llm(prompt, model, temperature=0.0, max_tokens=4096, debug=False):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}]
    )
    if debug:
        print(f"Model: {model}")
        print(f"Stop reason: {response.stop_reason}")
    return response.content[0].text