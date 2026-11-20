# Systemic Intelligence (SI) agent

An AI agent that helps an ordinary person understand a system that affects them (a trading app,
health insurance, renting...), act on it in their own life, and push for change where it works
against them. It reads the primary documents (terms, rulebooks, regulator records), shows its sources,
and is honest about what it could and couldn't verify.

**Try it:** https://systemicintelligence.streamlit.app/ (access code on request: message me where you found this). It handles one visitor's turn at a time, so it can be slow, and each visit has a small spending limit.

**Status:** an early experiment, tested on prediction markets (Kalshi, Polymarket) and health insurance
denials. Not legal, medical or financial advice.

## How it works
It goes one phase at a time and pauses after each, so you can ask questions or go deeper:
1. **The big picture:** what it is, the key points, how the main options differ, your situation case
   by case, and the areas worth digging into.
2. **Deep dive:** each area in depth: costs, fine print, who's on the other side, what protects you
   and what doesn't.
3. **What you can do:** practical steps, ready-to-send messages.
4. **How to push for change:** specific asks, to whom, and how.
5. **Final brief:** a one-page summary to keep or share.

## How it checks itself
- Every factual claim is labelled: **[VERIFIED: source]** (read this session, quoted), **[CHECK: why]**
  (plausible, not confirmed: says what to confirm and where), **[UNVERIFIED: why]** (general knowledge
  or its own reasoning).
- **Before you see a reply:** code checks every quote word for word against the documents
  (`checks.py`), and a separate fact checker compares sourced claims with the source, redoes the math,
  and tries to confirm unconfirmed claims (`factcheck.py`). A claim that doesn't hold up has its
  label changed to [CHECK] with the reason, so the reader sees one set of labels.
- **After each phase:** a separate skeptic reviews the argument as a whole (`skeptic.py`).
- **Limits:** about half of claims end up unconfirmed in a typical run; checks reduce errors but don't
  catch all of them (`eval_factcheck.py` measures this). You are the last check.

## Run it
```
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
python si_agent.py
```
A full run costs roughly $1.50-2 at Claude Sonnet 5.5 prices. Transcripts, a sources list and the
brief are saved in `transcripts/`.

**Web version:** `python -m streamlit run app.py` (works even if the `streamlit` command isn't on your PATH). On a host (e.g. Streamlit Community Cloud), set
`ANTHROPIC_API_KEY`, and optionally `ACCESS_CODE` and `VISITOR_BUDGET` (dollars per visitor), as secrets.
The web version saves nothing on the server and never reads files from it.

## Examples
Two final briefs the agent wrote, unedited, in `examples/`: [Kalshi](examples/kalshi-brief.md) (from an
earlier version, before the separate fact checker) and [a denied MRI claim](examples/health-insurance-mri-brief.md).
Treat them as examples of the output, not as verified reports.

## A small comparison test
`compare_approaches.py` asks one question about Kalshi four ways: a plain AI chat, the method (the policy)
with the same tools, the full agent, and the full agent with a few real questions from earlier runs asked
along the way. An AI judge, which doesn't know which is which, scores each against 13 findings taken from
earlier, longer runs and checked in Kalshi's documents. In one run each: the plain chat found 3, the method
7, the full agent 7.5 to 8, and the full agent with questions 9.5 (half a point for a partial answer). Limits:
one run each; the judge is the same model family; the 13 findings come from the author's earlier runs, and
the questions asked match three of them; no version found all 13; and which documents get opened varies a lot
from run to run. Run it yourself with `python compare_approaches.py` (about $4 to $7).

## Files
- `SOURCES-ARTICLE.md`: the source, rule or page, and verification status for each claim in the article about Kalshi and health insurance.
- `SI-AGENT-v2.md`: the method (the policy the agent follows). `CASEBOOK-SPARKS.md`: the short version
  of the casebook that the agent reads. `CASEBOOK.md`: the full casebook of real cases and how each was found
  (compiled from news, regulator releases and court filings; not independently re-verified).
- `si_agent.py`: the conversation loop. `tools.py`: web search + document reading.
- `checks.py`, `factcheck.py`, `skeptic.py`: the checks. `eval_factcheck.py`: accuracy test for the
  fact checker. `compare_writers.py`: compare writer models on the same question.
  `compare_approaches.py`: the comparison test above.
