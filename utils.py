import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY')
client = Anthropic(api_key=api_key)

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from typing import Literal

Model = Literal["claude-sonnet-4-5-20250929", "claude-3-5-haiku-20241022"]

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def get_chat(prompt, model, temperature=0.0, max_tokens=4096, debug=False):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    if debug:
        print(f"Model: {model}")
        print(f"Stop reason: {response.stop_reason}")

    return response.content[0].text

# Alias for cleaner imports
llm = get_chat


if __name__ == "__main__":
    if api_key:
        print(f"API Key configured: ...{api_key[-4:]}")
    else:
        print("Warning: ANTHROPIC_API_KEY not set in .env file")

    response = get_chat("You are a poetic assistant, skilled in explaining complex programming concepts with creative flair. Compose a poem that explains the concept of recursion in programming.", "claude-sonnet-4-5-20250929", debug=True)
    print(response)
