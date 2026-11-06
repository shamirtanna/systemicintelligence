"""
Regression test for the agent's flow and the web page, with FAKE models (free, no API calls).
Run after any change:   python test_app.py
Each line prints PASS or FAIL. The accuracy of the real fact checker is tested separately
(eval_factcheck.py, which costs a little).
"""
import os
import si_agent as s, factcheck
from factcheck import apply_fact_marks

os.environ.update(SAVE_TRANSCRIPTS="0", ACCESS_CODE="", VISITOR_BUDGET="100")  # after .env loaded
results = []


def check(name, ok):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name)


# --- labels: one set, changed in place ---
reply = ('- Kalshi can freeze withdrawals at any time. [VERIFIED: Rule 6.4] "may be suspended"\n'
         "- So what: an appeal is free.\n- The fee is $500. [VERIFIED: Rulebook] \"fee is $500\"")
probs = {"problems": [
    {"verdict": "OVERSTATED", "claim": "Kalshi can freeze withdrawals at any time", "source_says": "only in listed cases", "fix": ""},
    {"verdict": "TAG MISSING", "claim": "So what: an appeal is free", "source_says": "", "fix": ""},
    {"verdict": "CONFLICT", "claim": "The fee is $500", "source_says": "the fee schedule says $250", "fix": ""}]}
out, _ = apply_fact_marks(reply, probs)
check("overstated claim relabelled [CHECK], [VERIFIED] removed", "[CHECK: checked, the source says less" in out
      and "[VERIFIED: Rule 6.4]" not in out)
check("claim with no source becomes [UNVERIFIED]", "[UNVERIFIED: no source given]" in out)
check("sources that disagree become [CHECK: ...sources disagree]", "the sources disagree" in out)
check("no separate FACT CHECK markers", "FACT CHECK" not in out)

# --- headings ---
h = s.with_heading("**Focus I chose:** x\n\n## Phase 1: The big picture\n\nbody", "Phase 1: The big picture")
check("exactly one Phase 1 heading (model's own heading below a focus line)", h.count("Phase 1: The big picture") == 1
      and h.startswith("## Phase 1"))
check("heading added when missing", s.with_heading("Key points", "Phase 2: Deep dive").startswith("## Phase 2: Deep dive"))
check("answers are 'Your question'",
      s.phase_heading("x\nDone: Phase 1 · Next: Phase 2", [{"role": "assistant", "content": "Done: Phase 1"}])
      == ("Your question", False))
check("'phase 5' means the final brief", "final brief" in (s.translate_command("phase 5") or "").lower())

# --- per-visitor state ---
a, b = s.fresh_state(), s.fresh_state()
s.use_state(a); s.capture_question("visitor A's private words"); s.save_state(a)
s.use_state(b)
check("visitor B can't see visitor A's words", "visitor A's private words" not in s.reminder())

# --- the web page, end to end, with a fake model ---
from streamlit.testing.v1 import AppTest  # noqa: E402

P1 = ('**Focus I chose:** x\n\n## Phase 1: The big picture\n\n**Key points**\n'
      '- **Fee.** The fee is $500. [VERIFIED: Rules, p. 1] "The fee is $500 for a Claim"\n'
      '- **Freeze.** Kalshi can freeze withdrawals at any time. [VERIFIED: Rules, p. 1] "The fee is $500 for a Claim"\n'
      "Areas: a; b\nDone: Phase 1 · Next: Phase 2, deep dive")
ANS = 'The fee is $500. [VERIFIED: Rules, p. 1] "The fee is $500 for a Claim"\nDone: Phase 1 · Next: Phase 2, deep dive'
seen = {"writer": [], "checkers": []}


class B:
    def __init__(self, t): self.type, self.text = "text", t
class U:
    input_tokens = output_tokens = 100
    cache_read_input_tokens = cache_creation_input_tokens = 0
    server_tool_use = None
class R:
    def __init__(self, t): self.content, self.stop_reason, self.usage = [B(t)], "end_turn", U()
class M:
    def create(self, **kw):
        sysp = str(kw.get("system", ""))
        if sysp == factcheck.FACT_CHECKER_PROMPT:
            seen["checkers"].append(kw["model"])
            return R("CHECKED: 2\nOVERSTATED | Kalshi can freeze withdrawals at any time | only in listed cases | narrow it")
        if sysp.startswith("You are a skeptical editor"):
            return R("STRENGTH | clear labels | trust\nWEAK | a long point that would be cut off in the terminal "
                     "because it runs well past one hundred and forty characters of text in total | thin | read more")
        last = kw["messages"][-1]["content"]
        last = (last if isinstance(last, str) else last[-1].get("text", "")).split(s.REMINDER_MARK)[0]
        seen["writer"].append(last)
        return R(ANS if "question" in last.lower() else P1)
class C:
    messages = M()


s.make_client, s.load_policy = (lambda: C()), (lambda: "policy")
_orig = s.fresh_state
s.fresh_state = lambda: {**_orig(), "DOC_COPIES": {"https://example.com/r.pdf":
                                                   "[page 1]\nThe fee is $500 for a Claim under $5,000."}}
at = AppTest.from_file("app.py", default_timeout=60)
at.run()
check("start box offers the example on Enter", "example" in (at.text_input[0].placeholder or "").lower())
at.button[0].click().run()
check("empty start uses the example", "MRI" in seen["writer"][0])
md = " ".join(m.value for m in at.markdown)
check("one Phase 1 heading on the page", md.count("Phase 1: The big picture") == 1)
check("label changed in place, no FACT CHECK marker", "[CHECK: checked, the source says less" in md and "FACT CHECK" not in md)
check("internal 'Areas:' line hidden", "Areas: a; b" not in md)
check("progress line shows the next phase", any("→ 2 Deep dive" in m.value for m in at.markdown))
check("Skeptic shown in full, under its name", "one hundred and forty characters" in md
      and any("Skeptic" in e.label for e in at.expander))
box = [t for t in at.text_input if "Press Enter" in (t.placeholder or "")]
check("reply box says Enter moves on to the next phase", bool(box) and "continue to Phase 2" in box[0].placeholder)
n_before = len(seen["writer"])
box[0].input("").run(); [b for b in at.button if b.label == "Send"][0].click().run()
check("empty Enter = continue", len(seen["writer"]) == n_before + 1 and "continue to the next phase"
      in seen["writer"][-1].lower())
box = [t for t in at.text_input if "Press Enter" in (t.placeholder or "")]
box[0].input("a question about fees?").run(); [b for b in at.button if b.label == "Send"][0].click().run()
check("phases use the main checker, answers the faster one", seen["checkers"][:1] == [s.MODEL]
      and seen["checkers"][-1] == s.ANSWER_CHECK_MODEL)
check("answer gets a 'Your question' heading", "Your question" in " ".join(m.value for m in at.markdown))
dl = [d for d in at.get("download_button") if "conversation" in d.label.lower()]
check("visitor can download their conversation to share feedback", bool(dl))

# --- display: dollar signs, HTML, links ---
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("app_mod", "app.py")
src = open("app.py", encoding="utf-8").read()
ns = {}
exec(src[src.index("def display"):src.index("st.set_page_config")], {"__name__": "x"}, ns)
d = ns["display"]('$25 million and $9 billion <u>quoted</u> `code`')
check("dollar signs escaped (not read as math)", d.count("\\$") == 2)
check("HTML underline tags removed", "<u>" not in d and "</u>" not in d)
check("source links are clickable", ns["link"]("https://www.example.gov/docs/report.pdf")
      == "[www.example.gov: report.pdf](https://www.example.gov/docs/report.pdf)")
import tools as T  # noqa: E402
T.READ_THIS_TURN.clear(); T._DOC_COPIES["u"] = "text"
T.lookup("u", ["text"])
check("the checker's lookups aren't listed as the writer's sources", "u" not in T.READ_THIS_TURN)

# --- search_contracts: a live call to USAspending.gov's free public API (needs internet, no key) ---
try:
    out = T.search_contracts("Amazon Web Services", "U.S. Immigration and Customs Enforcement",
                             start_date="2020-10-01", end_date="2026-09-30")
    check("search_contracts returns official awards with links", "USAspending.gov" in out
          and "usaspending.gov/award/" in out and "resellers" in out)
    check("search_contracts result is saved like a document (so the checks can use it)",
          any(k.startswith("USAspending.gov") for k in T._DOC_COPIES))
except Exception as e:
    print(f"SKIP  search_contracts live check (no internet?): {type(e).__name__}")

print(f"\n{sum(results)} of {len(results)} passed")
raise SystemExit(0 if all(results) else 1)
