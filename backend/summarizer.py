"""
summarizer.py: makes the welcome summary when a document is loaded.

How it works (map-reduce):
A long datasheet doesn't fit in the LLM, and the summary has to talk about
the whole document, not only the first page. So we do this:
1. We split the pages into groups (maximum 10 groups).
2. For each group, the LLM writes a short summary (1-2 sentences).
   We only send the beginning of each group (2500 characters) so it fits
   in the model and it's faster. The beginning is usually where a section
   explains what it is about.
3. We give all the small summaries to the LLM and it writes the welcome message.

Like this we do at most 11 calls to the LLM, even if the PDF has 400 pages.
"""
import math
from backend.llm import generate
from backend.prompts import SECTION_SUMMARY_PROMPT, WELCOME_PROMPT

MAX_GROUPS = 10          # max number of groups
CHARS_PER_GROUP = 2500   # characters of each group we send to the LLM
SHORT_DOC_CHARS = 6000   # if the whole document is shorter than this, we send it all at once


def make_groups(pages):
    # pages = list of (page_number, text)

    # remove empty pages (pages with only images)
    pages_with_text = []
    for num, text in pages:
        if text.strip() != "":
            pages_with_text.append((num, text))

    # number of pages in each group, so there are 10 groups max
    # (ceil rounds up, e.g. 396 pages / 10 = 39.6 -> 40 pages per group)
    group_size = math.ceil(len(pages_with_text) / MAX_GROUPS)

    groups = []
    for i in range(0, len(pages_with_text), group_size):
        groups.append(pages_with_text[i:i + group_size])
    return groups


def summarize_group(group, model):
    # summary of one group of pages (step 2)
    first_page = group[0][0]
    last_page = group[-1][0]

    # join the text of all the pages and keep only the beginning
    text = ""
    for num, page_text in group:
        text += page_text + "\n"
    text = text[:CHARS_PER_GROUP]

    prompt = SECTION_SUMMARY_PROMPT.format(first_page=first_page, last_page=last_page, text=text)
    summary, seconds = generate([{"role": "user", "content": prompt}], model=model)
    return f"Pages {first_page}-{last_page}: {summary}"


def summarize_document(pages, model, language="English"):
    # returns the welcome message of the whole document
    groups = make_groups(pages)

    if len(groups) == 0:
        return "Welcome to LSDatasheet! I could not find any text in this document."

    # join all the text to see if the document is short
    all_text = ""
    for num, text in pages:
        all_text += text + "\n"

    summaries = []
    if len(all_text) <= SHORT_DOC_CHARS:
        # short document: we send all the text directly, no need for step 2
        summaries.append(all_text)
    else:
        # long document: one summary for each group (step 2)
        for group in groups:
            summaries.append(summarize_group(group, model))

    # step 3: the LLM writes one sentence about the document
    prompt = WELCOME_PROMPT.format(summaries="\n".join(summaries), language=language)
    description, seconds = generate([{"role": "user", "content": prompt}], model=model, temperature=0.3)

    # we add the beginning and the end ourselves, so they are always the same
    welcome = "Hi there! Welcome to LSDatasheet! " + description + " I'm happy to help you with anything you need."
    return welcome


if __name__ == "__main__":
    # Test: python -m backend.summarizer data/pdfs/74LS157.pdf
    import sys
    import time
    import pymupdf

    path = sys.argv[1]
    model = "qwen2.5:3b"

    # read the PDF page by page (later we will use Júlia's pdf_loader)
    doc = pymupdf.open(path)
    pages = []
    for i, page in enumerate(doc):
        pages.append((i + 1, page.get_text()))   # pages start at 1

    print(len(pages), "pages ->", len(make_groups(pages)), "groups")

    start = time.perf_counter()
    welcome = summarize_document(pages, model)
    seconds = time.perf_counter() - start

    print("\nWelcome message:\n", welcome)
    print("\nTime:", round(seconds, 1), "s")