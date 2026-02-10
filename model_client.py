"""
model_client.py — Talks to the AI model (Ollama or OpenRouter)
Owner: Member N210770

This file is the ONLY file that communicates with the AI model.
Everyone else calls functions from here to get code generated.
"""

import requests
import json
import time
import config


def generate_code(prompt: str, model: str = None, temperature: float = None) -> str:
    """
    Send a prompt to the AI model and get generated code back.

    Args:
        prompt: The text prompt describing what code to write
        model: Which model to use (defaults to config.MODEL_NAME)
        temperature: Creativity level (defaults to config.TEMPERATURE)

    Returns:
        A string containing the generated code
    """
    if config.USE_OPENROUTER:
        return _generate_openrouter(prompt, model, temperature)
    else:
        return _generate_ollama(prompt, model, temperature)


def generate_multiple(prompt: str, n: int = None) -> list:
    """
    Generate multiple different code solutions for the same prompt.
    This is needed because MURPHY compares multiple attempts.

    Args:
        prompt: The text prompt
        n: How many solutions to generate (defaults to config.NUM_GENERATIONS)

    Returns:
        A list of code strings
    """
    if n is None:
        n = config.NUM_GENERATIONS

    results = []
    for i in range(n):
        try:
            code = generate_code(prompt)
            results.append(code)
        except Exception as e:
            print(f"  [model_client] Generation {i+1}/{n} failed: {e}")
            results.append("")  # Empty string for failed generation
    return results


# ─────────────────────────────────────────────
# INTERNAL: Ollama backend
# ─────────────────────────────────────────────

def _generate_ollama(prompt: str, model: str = None, temperature: float = None) -> str:
    """Call the local Ollama server."""
    model = model or config.MODEL_NAME
    temperature = temperature if temperature is not None else config.TEMPERATURE

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": config.MAX_TOKENS,
        }
    }

    try:
        response = requests.post(
            config.OLLAMA_URL,
            json=payload,
            timeout=config.TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        return _extract_code(result.get("response", ""))

    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Cannot connect to Ollama. Make sure it is running.\n"
            "Start it with: ollama serve\n"
            "Then in another terminal: ollama pull " + model
        )
    except requests.exceptions.Timeout:
        raise TimeoutError(
            f"Ollama took more than {config.TIMEOUT}s to respond. "
            "The model might be too large for your machine."
        )
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


# ─────────────────────────────────────────────
# INTERNAL: OpenRouter backend (fallback)
# ─────────────────────────────────────────────

def _generate_openrouter(prompt: str, model: str = None, temperature: float = None) -> str:
    """Call OpenRouter API (cloud-based, needs API key)."""
    model = model or config.OPENROUTER_MODEL
    temperature = temperature if temperature is not None else config.TEMPERATURE

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert Python programmer. Generate only Python code. No explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": config.MAX_TOKENS,
    }

    try:
        response = requests.post(
            config.OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=config.TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return _extract_code(content)

    except Exception as e:
        raise RuntimeError(f"OpenRouter error: {e}")


# ─────────────────────────────────────────────
# INTERNAL: Code extraction helper
# ─────────────────────────────────────────────

def _extract_code(text: str) -> str:
    """
    Extract Python code from model response.
    Models often wrap code in ```python ... ``` blocks.
    This function strips that wrapper.
    """
    text = text.strip()

    # If response has ```python ... ``` blocks, extract the code inside
    if "```python" in text:
        parts = text.split("```python")
        if len(parts) > 1:
            code_part = parts[1]
            if "```" in code_part:
                code_part = code_part.split("```")[0]
            return code_part.strip()

    # If response has ``` ... ``` blocks (without python tag)
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            return parts[1].strip()

    # Otherwise return as-is (model gave raw code)
    return text


# ─────────────────────────────────────────────
# QUICK TEST (run this file directly to test)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Testing model_client.py")
    print("=" * 50)

    # Test 1: Single generation
    print("\nTest 1: Single code generation")
    print("-" * 30)
    try:
        prompt = "Write a Python function called add(a, b) that returns the sum of two numbers."
        code = generate_code(prompt)
        print(f"Generated code:\n{code}")
        print("✅ Single generation works!")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Multiple generations
    print("\nTest 2: Multiple code generations")
    print("-" * 30)
    try:
        codes = generate_multiple(
            "Write a Python function called multiply(a, b) that returns a * b.",
            n=2
        )
        for i, code in enumerate(codes):
            print(f"\n--- Generation {i+1} ---")
            print(code[:200] if len(code) > 200 else code)
        print(f"\n✅ Generated {len(codes)} solutions!")
    except Exception as e:
        print(f"❌ Error: {e}")
