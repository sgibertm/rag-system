"""
prompts.py: All prompt templates used by LSDatasheet.
Keeping them in one file makes them easy to tune (and to edit live in the interview).
"""

# Exact sentence the LLM must use when the context does not contain the answer.
# The pipeline and the evaluation detect abstentions by looking for this string.
NOT_FOUND = "I could not find this information in the document."

SYSTEM_PROMPT = f"""
TODO: write the rules for the assistant:
- who it is (an assistant that helps students with datasheets)
- answer ONLY using the provided context
- cite the pages it used, e.g. (p. 12)
- if the answer is not in the context, reply exactly: {NOT_FOUND}
- answer in the same language as the question
"""


def format_context(chunks) -> str:
    """Turn retrieved chunks into a text block, each one labelled with its page."""
    # TODO: for each chunk, build "[Page X]\n<text>" and join them with blank lines
    return "\n\n".join(f"[Page {chunk.page}]\n{chunk.text}" 
                       for chunk in chunks)


def build_rag_messages(question: str, chunks) -> list[dict]:
    """Build the list of messages for llm.generate()."""
    # TODO: return [system message, user message containing the context + the question]
    context = format_context(chunks)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\nQuestion:\n{question}"}
    ]