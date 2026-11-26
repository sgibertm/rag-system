"""
llm.py: connects to the local LLM (Ollama).
All the other files call the LLM through this file, so to change
the model (Experiment 3) we only have to change one parameter.
"""
import time
import ollama


class LLMError(Exception):
    # Our own error for when the LLM fails
    pass


def generate(messages, model, temperature=0.1):
    # messages = [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    # returns the answer and the seconds it took

    # perf_counter is better than time.time() to measure how long something takes
    start = time.perf_counter()

    # only the call to Ollama is inside the try, so if we have a bug
    # in our code we see the real error and not "the LLM failed"
    try:
        response = ollama.chat(model=model, messages=messages, options={"temperature": temperature})
    except ConnectionError as e:
        # Ollama app is closed
        raise LLMError("Cannot connect to Ollama. Open the Ollama app and try again.") from e
    except ollama.ResponseError as e:
        # 404 = the model is not downloaded
        if e.status_code == 404:
            raise LLMError(f"Model '{model}' is not downloaded. Run: ollama pull {model}") from e
        # any other error from Ollama
        raise LLMError(f"Ollama returned an error: {e.error}") from e

    seconds = time.perf_counter() - start
    answer = response["message"]["content"].strip()
    return answer, seconds


def generate_stream(messages, model, temperature=0.1):
    # Same as generate(), but returns the answer piece by piece (streaming),
    # so the app can show the text while the LLM is writing it.
    # It's a generator: the call to Ollama happens when we start reading it.
    try:
        stream = ollama.chat(model=model, messages=messages,
                             options={"temperature": temperature}, stream=True)
        for part in stream:
            yield part["message"]["content"]
    except ConnectionError as e:
        raise LLMError("Cannot connect to Ollama. Open the Ollama app and try again.") from e
    except ollama.ResponseError as e:
        if e.status_code == 404:
            raise LLMError(f"Model '{model}' is not downloaded. Run: ollama pull {model}") from e
        raise LLMError(f"Ollama returned an error: {e.error}") from e


if __name__ == "__main__":
    # Test: python -m backend.llm
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer in one sentence."},
        {"role": "user", "content": "What is the capital of France?"},
    ]

    # we call it twice: the first time is slow because the model is loading,
    # the second time is the real response time
    answer, seconds = generate(messages, model="qwen2.5:3b")
    print("Call 1:", round(seconds, 2), "s ->", answer)

    answer, seconds = generate(messages, model="qwen2.5:3b")
    print("Call 2:", round(seconds, 2), "s ->", answer)