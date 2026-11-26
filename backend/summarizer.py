# summarizer.py: makes the welcome summary when a document is loaded.
# A long datasheet doesn't fit in the LLM, and the summary has to talk about
# the whole document, not only the first page. So we use map-reduce:
# 1. Split the pages into groups (at most MAX_GROUPS).
# 2. Map: the LLM summarizes each group in 1-2 sentences. We only send the
#    beginning of each group (CHARS_PER_GROUP), where a section usually says
#    what it is about. This keeps it fast and inside the model's context.
# 3. Reduce: the LLM combines all the small summaries into one sentence.
# Like this we do at most 11 LLM calls, even if the PDF has 400 pages.

import math

from backend import config
from backend.llm import generate
from backend.prompts import SECTION_SUMMARY_PROMPT, WELCOME_PROMPT


# Page Groups
def make_groups(pages):
    # pages = list of (page_number, text)
    # Pages with only images are skipped
    pages_with_text = []
    for number, text in pages:
        if text.strip() != "":
            pages_with_text.append((number, text))

    if not pages_with_text:
        return []

    # Pages per group, so there are MAX_GROUPS groups at most
    # (ceil rounds up: 396 pages / 10 = 39.6 to 40 pages per group)
    group_size = math.ceil(len(pages_with_text) / config.MAX_GROUPS)

    groups = []
    for start in range(0, len(pages_with_text), group_size):
        groups.append(pages_with_text[start:start + group_size])
    return groups


# Map Step
def summarize_group(group, model):
    first_page = group[0][0]
    last_page = group[-1][0]

    # Join the text of the pages and keep only the beginning
    text = ""
    for number, page_text in group:
        text += page_text + "\n"
    text = text[:config.CHARS_PER_GROUP]

    prompt = SECTION_SUMMARY_PROMPT.format(first_page=first_page, last_page=last_page, text=text)
    summary, seconds = generate([{"role": "user", "content": prompt}], model=model)
    return f"Pages {first_page}-{last_page}: {summary}"


# Main Function (Reduce Step)
def summarize_document(pages, model=config.LLM_MODEL, language="English"):
    # Returns the welcome message of the whole document
    groups = make_groups(pages)
    if len(groups) == 0:
        return "Welcome to LSDatasheet! I could not find any text in this document."

    all_text = ""
    for number, text in pages:
        all_text += text + "\n"

    summaries = []
    if len(all_text) <= config.SHORT_DOC_CHARS:
        # Short document: all the text at once, no map step needed
        summaries.append(all_text)
    else:
        for group in groups:
            summaries.append(summarize_group(group, model))

    prompt = WELCOME_PROMPT.format(summaries="\n".join(summaries), language=language)
    description, seconds = generate([{"role": "user", "content": prompt}],
                                    model=model, temperature=config.SUMMARY_TEMPERATURE)

    # The beginning and the end are added here, so they are always the same
    return "Hi there! Welcome to LSDatasheet! " + description + " I'm happy to help you with anything you need."


# Quick Test: python -m backend.summarizer data/pdfs/74LS157.pdf
if __name__ == "__main__":
    import sys
    import time
    from backend.pdf_loader import load_pdf

    doc_id, pages = load_pdf(sys.argv[1])
    pages_as_tuples = []
    for page in pages:
        pages_as_tuples.append((page.page, page.text))

    print(len(pages), "pages ->", len(make_groups(pages_as_tuples)), "groups")

    start = time.perf_counter()
    welcome = summarize_document(pages_as_tuples)
    seconds = time.perf_counter() - start

    print("\nWelcome message:\n", welcome)
    print("\nTime:", round(seconds, 1), "s")