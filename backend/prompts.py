"""
prompts.py: prompts used by LSDatasheet.
All the prompts are here so they are easy to change.
"""

# Sentence the LLM has to say when the answer is not in the chunks.
# We keep it always in English so we can detect it easily.
NOT_FOUND = "OH NO! I could not find this information in the document."

# Rules for the assistant
SYSTEM_PROMPT = f"""You are LSDatasheet, an assistant that helps engineering students with datasheets.

Rules:
1. Answer ONLY with information from the CONTEXT. Do not use your own knowledge.
2. Cite the page of each fact, like (p. 12).
3. Be clear and short, but give all the important details (values, units, register names).
4. ONLY if the answer is not in the CONTEXT, reply with exactly this sentence and nothing else:
{NOT_FOUND}
5. Answer in the language the user asks for. The sentence of rule 4 is always in English."""


# Prompts used by summarizer.py

# MAP step: summarize one part of the document
SECTION_SUMMARY_PROMPT = """Here is a part of a technical document (pages {first_page} to {last_page}):

{text}

In 1 or 2 sentences, say what topics this part covers. Do not add anything that is not in the text."""

# REDUCE step: combine all the small summaries into the welcome message
# REDUCE step: one sentence saying what the document is about
# (the "Welcome to LSDatasheet!" part is added in summarizer.py, so it's always the same)
WELCOME_PROMPT = """These are summaries of the different parts of a technical document, in order:

{summaries}

In {language}, write ONE sentence that says what the document is (datasheet, paper, manual...)
and its main topics. Start with "This document". Write only that sentence."""




def format_context(chunks):
    # Put each chunk with its page number, separated by a blank line
    parts = []
    for chunk in chunks:
        parts.append(f"[Page {chunk.page}]\n{chunk.text}")
    return "\n\n".join(parts)


def build_rag_messages(question, chunks, language=None):
    # language = "Spanish", "Catalan"... (comes from the app)
    # if it's None, the model answers in the language of the question
    context = format_context(chunks)

    # small models work better if we say the language explicitly
    if language is None:
        lang_rule = "Answer in the same language as the question."
    else:
        lang_rule = f"Answer in {language}."

    # we repeat the important rules next to the question because small models forget them
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


def is_abstention(answer):
    # The model didn't know the answer if it STARTS with NOT_FOUND.
    # We don't just check "NOT_FOUND in answer" because sometimes the model
    # answers correctly and then adds the sentence at the end by mistake.
    return answer.strip().startswith(NOT_FOUND)


def clean_answer(answer):
    # If the model added NOT_FOUND after a real answer, we remove it
    if is_abstention(answer):
        return NOT_FOUND
    return answer.replace(NOT_FOUND, "").strip()


if __name__ == "__main__":
    # Test: python -m backend.prompts
    from backend.llm import generate
    from backend.schemas import Chunk

    model = "qwen2.5:3b"

    # fake chunks to test without the vector database
    chunk1 = Chunk(text="The PIC18F4321 has 8 Kbytes of Flash program memory and 512 bytes of RAM.",
                   page=3, chunk_id="c1", doc_id="test")
    chunk2 = Chunk(text="Timer0 can be configured as an 8-bit or 16-bit timer/counter.",
                   page=127, chunk_id="c2", doc_id="test")
    chunks = [chunk1, chunk2]

    # (question, language)
    tests = [
        ("How much Flash memory does it have?", None),       # should answer, p. 3
        ("What is the maximum operating voltage?", None),    # should say NOT_FOUND
        ("¿Cuánta memoria Flash tiene?", None),              # should answer in Spanish
        ("¿Cuánta memoria Flash tiene?", "Spanish"),         # should answer in Spanish
        ("¿Cuál es el voltaje máximo?", "Spanish"),          # should say NOT_FOUND in English
    ]

    # first call is slow because the model loads, so we do one before testing
    generate([{"role": "user", "content": "hi"}], model=model)

    for question, language in tests:
        messages = build_rag_messages(question, chunks, language)
        answer, seconds = generate(messages, model=model)
        print("\nQuestion:", question, "| language:", language)
        print("Raw answer:", answer)
        print("Clean answer:", clean_answer(answer))
        print("Abstained:", is_abstention(answer), "| time:", round(seconds, 2), "s")