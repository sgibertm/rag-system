# llm.py: connects to the local LLM (Ollama).
# All the other files call the LLM through this file, so to change
# the model (experiment 3) we only have to change LLM_MODEL in config.py.

import time
import ollama

from backend import config

# Errors
class LLMError(Exception):
    # Our own error for when the LLM fails (the app shows its message to the user)
    pass


def ollama_error(error, model):
    # Turns the Ollama errors into clear messages
    if isinstance(error, ConnectionError):
        return LLMError("Cannot connect to Ollama. Open the Ollama app and try again.")
    if error.status_code == 404:
        return LLMError(f"Model '{model}' is not downloaded. Run: ollama pull {model}")
    return LLMError(f"Ollama returned an error: {error.error}")


# Generation
def generate(messages, model=config.LLM_MODEL, temperature=config.TEMPERATURE):
    # messages = [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    # Returns the whole answer and the seconds it took (used by the evaluation)
    start = time.perf_counter()  # better than time.time() to measure durations

    # Only the call to Ollama is inside the try, so a bug in our code
    # shows the real error and not "the LLM failed"
    try:
        response = ollama.chat(model=model, messages=messages, options={"temperature": temperature})
    except (ConnectionError, ollama.ResponseError) as e:
        raise ollama_error(e, model) from e

    seconds = time.perf_counter() - start
    answer = response["message"]["content"].strip()
    return answer, seconds


def generate_stream(messages, model=config.LLM_MODEL, temperature=config.TEMPERATURE):
    # Same as generate(), but returns the answer piece by piece (used by the app)
    # It's a generator: Ollama is called when we start reading it
    try:
        stream = ollama.chat(model=model, messages=messages,
                             options={"temperature": temperature}, stream=True)
        for part in stream:
            yield part["message"]["content"]
    except (ConnectionError, ollama.ResponseError) as e:
        raise ollama_error(e, model) from e


# Quick Test: python -m backend.llm
# Two calls: the first is slow (the model is loading), the second is the real time
if __name__ == "__main__":
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer in one sentence."},
        {"role": "user", "content": "What is the capital of France?"},
    ]

    answer, seconds = generate(messages)
    print("Call 1:", round(seconds, 2), "s =====>", answer)

    answer, seconds = generate(messages)
    print("Call 2:", round(seconds, 2), "s =====>", answer)