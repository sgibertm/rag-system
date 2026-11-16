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
    Send a list of chat messages to the local LLM.

    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    Returns: (answer_text, seconds_taken)
    """
# TODO 1: start the timer
    start_time = time.time()
# TODO 2: call ollama.chat(...) with model, messages and temperature in options
    try:
        response = ollama.chat(model=model, messages=messages, options={"temperature": temperature})
        answer_text = response.text
    except Exception as e:
        raise LLMError(f"Failed to generate response from the local LLM: {e}")
# TODO 3: if anything goes wrong (Ollama closed, model not pulled), raise LLMError
#         with a message that tells the user what to do

# TODO 4: stop the timer and return the text and the time
    end_time = time.time()
    seconds_taken = end_time - start_time
    return answer_text, seconds_taken


if __name__ == "__main__":
# TODO 5: quick manual test: a system message + a user question, print answer and time
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    answer, time_taken = generate(messages, model="llama3", temperature=0.1)
    print(f"Answer: {answer}")
    print(f"Time taken: {time_taken:.2f} seconds")