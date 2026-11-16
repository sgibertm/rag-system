"""
llm.py: Thin wrapper around the local LLM served by Ollama.

The rest of the backend only talks to the LLM through this file,
so switching models (Experiment 3) means changing one parameter.
"""
import time

import ollama


class LLMError(Exception):
    """Raised when the local LLM cannot be reached or fails."""


def generate(messages: list[dict], model: str, temperature: float = 0.1) -> tuple[str, float]:
    """
    Send a list of chat messages to the local LLM and return its reply.

    Args:
        messages: chat history, e.g.
            [{"role": "system", "content": "..."},
             {"role": "user", "content": "..."}]
        model: name of an Ollama model that has been pulled, e.g. "qwen2.5:3b".
        temperature: 0 = deterministic and factual, higher = more creative.

    Returns:
        (answer_text, seconds_taken)

    Raises:
        LLMError: if Ollama is not running, the model is missing, or the call fails.
    """
    # perf_counter() is a monotonic, high-resolution clock made for measuring durations
    start = time.perf_counter()

    # Only the call to Ollama goes inside the try, so bugs in our own code
    # are not hidden behind a misleading "LLM failed" message.
    try:
        response = ollama.chat(
            model=model,
            messages=messages,
            options={"temperature": temperature},
        )
    except ConnectionError as e:
        # The Ollama server (the app) is not running
        raise LLMError(
            "Cannot connect to Ollama. Open the Ollama app and try again."
        ) from e
    except ollama.ResponseError as e:
        # The server answered with an error
        if e.status_code == 404:
            raise LLMError(
                f"Model '{model}' is not downloaded. Run: ollama pull {model}"
            ) from e
        raise LLMError(f"Ollama returned an error: {e.error}") from e

    seconds = time.perf_counter() - start
    answer_text = response["message"]["content"].strip()
    return answer_text, seconds


if __name__ == "__main__":
    # Manual test: python -m backend.llm   (run from the project root)
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer in one sentence."},
        {"role": "user", "content": "What is the capital of France?"},
    ]

    # Two calls: the first one includes loading the model into memory,
    # the second one shows the real response time (this matters for the latency metric).
    for attempt in (1, 2):
        answer, seconds = generate(test_messages, model="qwen2.5:3b", temperature=0.1)
        print(f"[call {attempt}] {seconds:.2f}s -> {answer}")