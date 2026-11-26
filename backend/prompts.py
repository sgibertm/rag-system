# prompts.py: all the prompts used by LSDatasheet, in one place so they are easy to change.

# Sentence the LLM has to say when the answer is not in the chunks.
# It's always in English so we can detect it easily.
NOT_FOUND = "OH NO! I could not find this information in the document."


# Assistant Rules
SYSTEM_PROMPT = f"""You are LSDatasheet, an assistant that helps engineering students with datasheets.

Rules:
1. Answer ONLY with information from the CONTEXT. Do not use your own knowledge.
2. Cite the page of each fact, like (p. 12).
3. Be clear and short, but give all the important details (values, units, register names).
4. ONLY if the answer is not in the CONTEXT, reply with exactly this sentence and nothing else:
{NOT_FOUND}
5. Answer in the language the user asks for. The sentence of rule 4 is always in English."""


# Answer Styles (selected in the app sidebar)
STYLES = {
    "Concise": "Answer in 1 to 3 sentences with only the key facts.",
    "Descriptive": "Answer with a complete explanation, step by step.",
    "Practical examples": "Answer and add a short practical example of how to use it.",
}


# Summary Prompts (used by summarizer.py)
# Map step: summarize one part of the document
SECTION_SUMMARY_PROMPT = """Here is a part of a technical document (pages {first_page} to {last_page}):

{text}

In 1 or 2 sentences, say what topics this part covers. Do not add anything that is not in the text."""

# Reduce step: one sentence saying what the document is about
# ("Welcome to LSDatasheet!" is added in summarizer.py, so it's always the same)
WELCOME_PROMPT = """These are summaries of the different parts of a technical document, in order:

{summaries}

In {language}, write ONE sentence that says what the document is (datasheet, paper, manual...)
and its main topics. Start with "This document". Write only that sentence."""


# Building the Messages
def format_context(chunks):
    # Each chunk with its page number, separated by a blank line
    parts = []
    for chunk in chunks:
        parts.append(f"[Page {chunk.page}]\n{chunk.text}")
    return "\n\n".join(parts)


def build_rag_messages(question, chunks, language=None, style=None):
    # language = "Spanish", "Catalan"... (None = same language as the question)
    # style = a key of STYLES (None = only the default rules)
    context = format_context(chunks)

    # Small models work better if we say the language explicitly
    if language is None:
        lang_rule = "Answer in the same language as the question."
    else:
        lang_rule = f"Answer in {language}."

    if style in STYLES:
        lang_rule = lang_rule + " " + STYLES[style]

    # The important rules are repeated next to the question because small models forget them
    user_message = f"""CONTEXT:
{context}

QUESTION: {question}

{lang_rule} Use only the context and cite pages like (p. 12).
ONLY if the answer is not in the context, reply with just: {NOT_FOUND}
If you can answer, do NOT write that sentence."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    return messages


# Abstention ("I don't know") Detection
def is_abstention(answer):
    # The model didn't know the answer if it STARTS with NOT_FOUND.
    # Not just "NOT_FOUND in answer": sometimes the model answers correctly
    # and then adds the sentence at the end by mistake.
    return answer.strip().startswith(NOT_FOUND)


def clean_answer(answer):
    # If the model added NOT_FOUND after a real answer, we remove it
    if is_abstention(answer):
        return NOT_FOUND
    return answer.replace(NOT_FOUND, "").strip()


# Quick Test: python -m backend.prompts
if __name__ == "__main__":
    from backend.llm import generate
    from backend.schemas import Chunk

    # Fake chunks to test without the vector database
    chunk1 = Chunk(text="The PIC18F4321 has 8 Kbytes of Flash program memory and 512 bytes of RAM.",
                   page=3, chunk_id="c1", doc_id="test")
    chunk2 = Chunk(text="Timer0 can be configured as an 8-bit or 16-bit timer/counter.",
                   page=127, chunk_id="c2", doc_id="test")
    chunks = [chunk1, chunk2]

    # (question, language, style)
    tests = [
        ("How much Flash memory does it have?", None, None),           # should answer, p. 3
        ("What is the maximum operating voltage?", None, None),        # should say NOT_FOUND
        ("¿Cuánta memoria Flash tiene?", None, None),                  # should answer in Spanish
        ("¿Cuánta memoria Flash tiene?", "Spanish", None),             # should answer in Spanish
        ("¿Cuál es el voltaje máximo?", "Spanish", None),              # should say NOT_FOUND in English
        ("How can Timer0 be configured?", None, "Practical examples"), # should add an example
    ]

    # The first call is slow because the model loads, so we do one before testing
    generate([{"role": "user", "content": "hi"}])

    for question, language, style in tests:
        messages = build_rag_messages(question, chunks, language, style)
        answer, seconds = generate(messages)
        print("\nQuestion:", question, "| language:", language, "| style:", style)
        print("Raw answer:", answer)
        print("Clean answer:", clean_answer(answer))
        print("Abstained:", is_abstention(answer), "| time:", round(seconds, 2), "s")