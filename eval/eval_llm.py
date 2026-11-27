"""
eval_llm.py: Experiment 3 (compare local LLMs).
The retrieval is fixed: it reads the chunks that eval_retrieval.py saved in eval/retrieved.json.

Run from the repo root:
  python -m eval.eval_llm            -> asks every question to every model, saves eval/results_llm.csv
  (fill the "score" column by hand: 1, 0.5 or 0, only for answerable questions)
  python -m eval.eval_llm summary    -> prints accuracy, abstention and latency per model
"""
import csv
import json
import os
import platform
import sys

from backend.llm import generate, LLMError

# Models to compare (Change if any computer cannot run)
MODELS = ["qwen2.5:3b", "llama3.2:3b"]
TOP_K = 5
TEMPERATURE = 0.1

QUESTIONS = "eval/questions.json"
RETRIEVED = "eval/retrieved.json"
RESULTS = "eval/results_llm.csv"
DELIM = ";"  # Excel in Spanish opens ";" files correctly

NO_ANSWER = "I can't know based on this document."
SYSTEM_PROMPT = (
    "You answer questions about a technical document using ONLY the context given by the user. "
    "Be clear and concise. If the context does not contain the answer, reply exactly: " + NO_ANSWER
)

if len(sys.argv) > 1 and sys.argv[1] == "summary":
    # Reads the CSV after the manual grading
    rows = list(csv.DictReader(open(RESULTS, encoding="utf-8-sig"), delimiter=DELIM))
    for model in sorted({r["model"] for r in rows}):
        mine = [r for r in rows if r["model"] == model]
        answerable = [r for r in mine if r["answerable"] == "yes"]
        unanswerable = [r for r in mine if r["answerable"] == "no"]
        graded = [float(r["score"].replace(",", ".")) for r in answerable if r["score"].strip() != ""]
        refused = [r for r in unanswerable if r["abstained"] == "yes"]
        wrongly_refused = [r for r in answerable if r["abstained"] == "yes"]
        avg_seconds = sum(float(r["seconds"]) for r in mine) / len(mine)

        print("Model:", model)
        if graded:
            print(" Accuracy:", round(sum(graded) / len(graded), 3), f"({len(graded)}/{len(answerable)} answerable questions graded)")
        else:
            print(" Accuracy: fill the 'score' column first")
        print(" Abstention:", f"{len(refused)}/{len(unanswerable)} unanswerable questions declined")
        print(" Wrongly refused:", f"{len(wrongly_refused)}/{len(answerable)} answerable questions")
        print(" Average time per answer:", round(avg_seconds, 2), "s")
else:
    # Ask every question to every model
    if not os.path.exists(RETRIEVED):
        print("Missing", RETRIEVED, "- run eval_retrieval.py first to save the retrieved chunks.")
        sys.exit(1)

    questions = json.load(open(QUESTIONS, encoding="utf-8"))
    # retrieved.json format: {"1": [{"page": 3, "text": "..."}, ...], "2": [...]}
    retrieved = json.load(open(RETRIEVED, encoding="utf-8"))

    # The assignment asks to always note down the hardware
    print("Hardware:", platform.platform(), "|", platform.processor(), "| CPUs:", os.cpu_count())
    print("Also write down your GPU and RAM in the report.")

    rows = []
    try:
        for model in MODELS:
            # Warm-up: the first call loads the model and is slow, so we do not time it
            generate([{"role": "user", "content": "Hi"}], model)
            for q in questions:
                chunks = retrieved[str(q["id"])][:TOP_K]
                context = "\n\n".join(f"[Page {c['page']}] {c['text']}" for c in chunks)
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {q['question']}"},
                ]
                answer, seconds = generate(messages, model, TEMPERATURE)
                abstained = "yes" if NO_ANSWER.lower() in answer.lower() else "no"
                rows.append({
                    "model": model,
                    "id": q["id"],
                    "document": q["document"],
                    "answerable": "yes" if q["answerable"] else "no",
                    "question": q["question"],
                    "expected_answer": q["answer"] or "",
                    "answer": answer,
                    "abstained": abstained,
                    "seconds": round(seconds, 2),
                    "score": "",
                })
                print(model, "| question", q["id"], "|", round(seconds, 2), "s")
    except LLMError as e:
        print(e)
        sys.exit(1)

    with open(RESULTS, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=DELIM)
        writer.writeheader()
        writer.writerows(rows)
    print("Saved", RESULTS, "- now fill the 'score' column by hand and run: python -m eval.eval_llm summary")
