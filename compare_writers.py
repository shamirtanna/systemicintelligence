"""
Same question, two writer models, side by side (for choosing the model for the public version, C).

Runs two turns per model (the first reply, then Phase 1) with the real policy, tools and checks.
The fact checker is the same for both (Sonnet), so the checks are a fair yardstick.
Saves each model's replies to agent/transcripts/compare-<model>.md so you can read them.

Run: python agent/compare_writers.py
Cost: roughly $0.30-0.60 for Sonnet, a few cents for Haiku.
"""
from pathlib import Path
import si_agent as s
import tools
from checks import check_quotes
from factcheck import fact_check

QUESTION = "My insurer denied a claim for an MRI my doctor ordered."
import sys
MODELS = sys.argv[1:] or ["claude-sonnet-5-5", "claude-haiku-5-5"]
CHECKER = "claude-sonnet-5-5"
NEXT = ("(No reply. Please continue to the next phase. Use sensible defaults for any open questions "
        "and tell me in one line which ones you chose.)")


def run(model: str, client, policy: str) -> dict:
    tools._DOC_COPIES.clear()                  # each model finds and reads its own documents
    s.CURRENT_THREADS, s.QUESTIONS[:], s.LAST_FIX_REQUEST, s.RUN_COST = "", [], "", 0.0
    s.MODEL = model
    messages = [{"role": "user", "content": QUESTION + s.reminder()}]
    stats = {"model": model, "words": 0, "quotes": 0, "quotes_found": 0, "problems": 0, "checked": 0,
             "writer_cost": 0.0, "replies": []}
    for turn in range(2):
        reply = s.one_turn(client, policy, messages, status=lambda line: None)
        if reply == s.FAILED:
            stats["replies"].append("[model call failed]")
            break
        stats["writer_cost"] = s.RUN_COST
        q = check_quotes(reply, tools.document_texts())
        fc = fact_check(client, CHECKER, reply)
        stats["words"] += len(reply.split())
        stats["quotes"] += len(q)
        stats["quotes_found"] += sum(r["found"] for r in q)
        stats["checked"] += fc["checked"]
        stats["problems"] += len(fc["problems"])
        stats["replies"].append(reply + "\n\n_(fact check: " + "; ".join(
            f"{p['verdict']}: {p['claim']}" for p in fc["problems"]) + ")_")
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": NEXT + s.reminder()})
    stats["docs"] = len(tools.documents_read())
    return stats


def main():
    client, policy = s.make_client(), s.load_policy()
    rows = []
    for model in MODELS:
        print(f"Running {model}...", flush=True)
        st = run(model, client, policy)
        rows.append(st)
        out = Path(__file__).parent / "transcripts" / f"compare-{model}.md"
        out.write_text(f"# {model}\n\n" + "\n\n---\n\n".join(st["replies"]), encoding="utf-8")
    print(f"\n{'':22}" + "".join(f"{r['model']:>22}" for r in rows))
    for label, key in (("Words (2 replies)", "words"), ("Documents read", "docs"),
                       ("Quotes tagged VERIFIED", "quotes"), ("...found in the docs", "quotes_found"),
                       ("Claims fact-checked", "checked"), ("Problems found", "problems")):
        print(f"{label:22}" + "".join(f"{r[key]:>22}" for r in rows))
    print(f"{'Writer cost':22}" + "".join(f"{'$%.3f' % r['writer_cost']:>22}" for r in rows))
    print("\nRead them side by side: agent/transcripts/compare-<model>.md")


if __name__ == "__main__":
    main()
