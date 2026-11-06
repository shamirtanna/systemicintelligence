"""
Systemic Intelligence (SI) agent: the conversation loop.

Goes one phase at a time (big picture, deep dive, what you can do, how to push for change,
final brief), pausing after each. Uses web search + read_document (tools.py) to read primary sources.
Before each reply is shown, its labels are audited: code checks every quote (checks.py) and a
separate fact checker checks sourced claims (factcheck.py). A separate skeptic reviews the argument
after each phase (skeptic.py). The method itself lives in SI-AGENT-v2.md.

Run it:  python si_agent.py
Needs:   pip install -r requirements.txt  +  ANTHROPIC_API_KEY in a .env (see .env.example).
"""

import os
import re
import sys
from pathlib import Path

# Load the API key from a .env file (so you don't have to set it in the terminal
# every time, and it never lives in the code). The .env sits in the project root
# and is gitignored, so the key never gets committed.
try:
    from dotenv import load_dotenv
    # Look for a .env in BOTH the agent/ folder (next to this script) and the
    # project root (one level up). Whichever exists wins, so it works no matter
    # where you put the key.
    here = Path(__file__).parent
    # override=True: .env WINS over anything already set in the terminal. Without it, a leftover
    # setting in the terminal (e.g. PROVIDER=bedrock) silently beats .env, which is how one run
    # ended up with no search tool. AWS credentials aren't in .env, so they still come from the terminal.
    load_dotenv(here / ".env", override=True)           # agent/.env
    load_dotenv(here.parent / ".env")                   # project-root .env (fallback only)
except ImportError:
    pass  # dotenv is optional; env var set in the terminal still works.

# The Anthropic SDK is the official Python library for calling Claude.
# If this import fails, run:  pip install anthropic
try:
    import anthropic
except ImportError:
    print("Missing dependency. Run:  pip install anthropic")
    sys.exit(1)


# --- 1. Load the policy -------------------------------------------------------
# The "policy" is SI-AGENT-v1.md — the agent's whole brain, as plain text.
# We load it from the file sitting next to this script, so edits to the policy
# automatically flow into the agent (no copy-paste).
POLICY_PATH = Path(__file__).parent / "SI-AGENT-v2.md"   # v1 kept for reference

# Tools (tools.py) + where transcripts go.
from datetime import datetime
import shutil
from tools import (TOOLS as LOCAL_TOOLS, ANTHROPIC_WEB_SEARCH, SEARCH_WEB_TOOL,
                   run_tool, DOCS_DIR, documents_read, document_texts)
from checks import check_quotes, summary_line, fix_request, Ledger, apply_quote_labels
from factcheck import fact_check, fc_summary, fc_fix_request, needs_check, apply_fact_marks, apply_upgrades
FACT_CHECK_MODEL = os.environ.get("FACT_CHECK_MODEL", "").strip()  # empty = same model as the writer
# Checker for answers to questions (not phases): faster and cheaper. Set ANSWER_CHECK_MODEL= (empty) in
# .env to use the main checker for everything.
ANSWER_CHECK_MODEL = os.environ.get("ANSWER_CHECK_MODEL", "claude-haiku-5-5").strip()
from skeptic import skeptic_review, sk_summary, sk_fix_request
SKEPTIC_MODEL = os.environ.get("SKEPTIC_MODEL", "").strip()   # empty = same model as the writer
SKEPTIC_FULL = os.environ.get("SI_WEB_MODE") == "1"   # web: show every review item in full (no cutting)
SKEPTIC_AFTER = {1, 2, 3, 4}   # after every phase (≈ $0.02-0.04 each). Phase 1 matters most: its
                               # headlines are the first impression (an overreach there went unchallenged)
_SPARKS = Path(__file__).parent / "CASEBOOK-SPARKS.md"
SPARKS_TEXT = _SPARKS.read_text(encoding="utf-8") if _SPARKS.exists() else ""
FACT_CHECK = os.environ.get("FACT_CHECK", "1").strip() != "0"   # set FACT_CHECK=0 in .env to turn off

# PROVIDER SWITCH (set in .env): "anthropic" = Anthropic's API (has built-in web search);
# "bedrock" = Claude through your AWS account (no built-in web search for Claude there yet).
PROVIDER = os.environ.get("PROVIDER", "anthropic").strip().lower()
# Search: Anthropic's built-in web_search on Anthropic; our own search_web (AWS AgentCore Web
# Search, via the gateway from setup_search_gateway.py) on Bedrock; none if neither is set up.
if PROVIDER == "anthropic":
    SEARCH = "web_search"
    TOOLS = LOCAL_TOOLS + [ANTHROPIC_WEB_SEARCH]
elif os.environ.get("AGENTCORE_GATEWAY_URL"):
    SEARCH = "search_web"
    TOOLS = LOCAL_TOOLS + [SEARCH_WEB_TOOL]
else:
    SEARCH = None
    TOOLS = LOCAL_TOOLS
TRANSCRIPT_DIR = Path(__file__).parent / "transcripts"
MAX_TOOL_CALLS = 10  # cap document reads per turn, so a runaway loop can't run up cost (web searches
                     # have their own cap: max_uses=5 per model call, in tools.py)
                     # (was 8; the MRI run's Phase 2 hit it and left a key article unread)
MAX_CONTINUATIONS = 2  # cap cut-off continuations per turn (each one is another paid call)

# RUN BUDGET (set RUN_BUDGET in .env, in dollars; 0 or missing = no budget). Uses the cost display's
# estimate. At 75% the pause shows a warning; at 100% pressing Enter writes the final brief instead
# of starting another phase. A warning, not a hard stop, for now; the hosted version (C) will need a hard stop.
RUN_BUDGET = float(os.environ.get("RUN_BUDGET", "0") or 0)


def budget_note() -> str:
    if not RUN_BUDGET or RUN_COST < 0.75 * RUN_BUDGET:
        return ""
    if RUN_COST >= RUN_BUDGET:
        return (f"\n[!] This run has used about ${RUN_COST:.2f}, past its ${RUN_BUDGET:.2f} budget. "
                "Press Enter for the final brief (recommended), or type 'quit'.")
    return f"\n[!] Heads up: this run has used about ${RUN_COST:.2f} of its ${RUN_BUDGET:.2f} budget."


COST_SUMMARY = ""


def add_cost(amount: float):
    """Add a cost that happened outside the main turn (e.g. the fact checker) to the run total."""
    global RUN_COST
    RUN_COST += amount


def cost_summary(cost, u: dict) -> str:
    """Two plain lines shown at each pause: what this turn cost, and what the cache saved."""
    if cost is None:
        return (f"Usage this turn: {u['in'] + u['cached'] + u['cache_write']:,} tokens sent, "
                f"{u['out']:,} written, {u['searches']} search(es). (Add prices to .env to see cost.)")
    budget = f" of your ${RUN_BUDGET:.2f} budget" if RUN_BUDGET else ""
    line = f"Cost: this turn ≈ ${cost:.2f} · whole run so far ≈ ${RUN_COST:.2f}{budget}"
    try:
        saved = u["cached"] * (float(os.environ["PRICE_IN"]) - float(os.environ["PRICE_CACHE_READ"])) / 1e6
        line += (f"\n      Cache: {u['cached']:,} tokens re-used at a discount (saved ≈ ${saved:.2f}); "
                 f"{u['in']:,} sent at full price")
    except (KeyError, ValueError):
        pass
    return line


def over_budget() -> bool:
    return bool(RUN_BUDGET) and RUN_COST >= RUN_BUDGET

# COST DISPLAY. Prices come from .env (copy them from Anthropic's pricing page; we don't hard-code
# them because they change). Per MILLION tokens, plus per 1,000 web searches. If they're not set,
# the usage line shows token counts only.
#   PRICE_IN=  PRICE_OUT=  PRICE_CACHE_READ=  PRICE_CACHE_WRITE=  PRICE_SEARCH_PER_1000=
RUN_COST = 0.0


# Per-model prices (USD per million tokens: input, output, cache read, cache write) from
# https://docs.anthropic.com/en/docs/about-claude/pricing. Models not listed use the PRICE_* values in .env.
# Haiku 5.5 is priced by prompt length; these are its rates for prompts up to 100,000 tokens.
MODEL_PRICES = {"claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125)}


def turn_cost(u: dict, model: str = ""):
    if model in MODEL_PRICES:
        p_in, p_out, p_read, p_write = MODEL_PRICES[model]
        return (u["in"] * p_in + u["out"] * p_out + u["cached"] * p_read + u["cache_write"] * p_write) / 1e6 \
            + u["searches"] * float(os.environ.get("PRICE_SEARCH_PER_1000", "0") or 0) / 1000
    try:
        p = {k: float(os.environ[k]) for k in ("PRICE_IN", "PRICE_OUT", "PRICE_CACHE_READ",
                                                 "PRICE_CACHE_WRITE")}
    except (KeyError, ValueError):
        return None
    search = float(os.environ.get("PRICE_SEARCH_PER_1000", "0") or 0)
    return (u["in"] * p["PRICE_IN"] + u["out"] * p["PRICE_OUT"] + u["cached"] * p["PRICE_CACHE_READ"]
            + u["cache_write"] * p["PRICE_CACHE_WRITE"]) / 1_000_000 + u["searches"] * search / 1000

def load_policy() -> str:
    if not POLICY_PATH.exists():
        print(f"Can't find the policy at {POLICY_PATH}")
        sys.exit(1)
    policy = POLICY_PATH.read_text(encoding="utf-8")
    # The casebook sparks: real cases from other systems, as ideas to consider (not templates).
    # Appended to the policy so it's cached with it (about 1,200 extra tokens, at ~10% after the first call).
    sparks = POLICY_PATH.parent / "CASEBOOK-SPARKS.md"
    if sparks.exists():
        policy += "\n\n" + sparks.read_text(encoding="utf-8")
    # Tell the model which search tool it has this session (the policy says "web_search").
    if SEARCH == "search_web":
        policy += ("\n\n## This session\nYour search tool is called search_web (it does the same job "
                   "as web_search in this policy). It returns links and short snippets; read the "
                   "document with read_document before quoting it. Always show the source link.\n")
    elif SEARCH is None:
        # No search at all. Say so, or the model may claim it searched.
        policy += ("\n\n## This session\nNo search tool is available. Do not say you searched. "
                   "Name the documents you need and ask the user for links (PDF links work best).\n")
    return policy


# --- 2. Set up the model client ----------------------------------------------
# The client is the object that talks to Claude's API. It reads your API key
# from the environment variable ANTHROPIC_API_KEY (we never hard-code keys).
def make_client():
    if PROVIDER == "bedrock":
        # AnthropicBedrock takes the same messages.create(...) calls as the Anthropic client, so
        # nothing else changes. It finds AWS credentials the standard AWS way: env vars
        # (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN, e.g. from .env), or an
        # AWS profile (AWS_PROFILE). Temporary session credentials expire, so refresh them per session.
        if not (os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE")):
            print("PROVIDER=bedrock, but no AWS credentials found. Set your AWS credentials in this terminal")
            print("into THIS PowerShell window, then run the agent again from the same window.")
            sys.exit(1)
        if not MODEL:
            print("PROVIDER=bedrock, but BEDROCK_MODEL is empty. Run: python agent/list_bedrock_models.py")
            print("and put one of the IDs it prints into agent/.env as BEDROCK_MODEL=...")
            sys.exit(1)
        return anthropic.AnthropicBedrock(aws_region=os.environ.get("AWS_REGION", "us-east-1"),
                                          max_retries=4)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("No API key found. Add ANTHROPIC_API_KEY to agent/.env.")
        sys.exit(1)
    # max_retries: the library retries brief outages (overloaded / rate limit) with a pause between
    # tries. Default is 2; 4 rides out a short spike instead of failing the turn.
    return anthropic.Anthropic(max_retries=4)


# Which model to use. Claude Sonnet is a good balance of quality + cost for this.
# NOTE: model names are exact strings that change over time. This one was confirmed
# available on this account via client.models.list(). If you get a 404 "model not found",
# run that list again and pick a current name.
MODEL = (os.environ.get("BEDROCK_MODEL", "") if PROVIDER == "bedrock"
         else os.environ.get("WRITER_MODEL", "").strip() or "claude-sonnet-5-5")   # WRITER_MODEL in .env to try another
# Bedrock model IDs look different from Anthropic's (run list_bedrock_models.py to see yours).


# --- 2b. Test the connection (cheap safety check) ----------------------------
# Addresses the "is this a legit model / will this even connect" worry: before
# we send the big policy, send a one-word "hi". If the key or model name is wrong,
# we find out in 2 seconds with a clear error — not buried inside a long run.
def test_connection(client) -> bool:
    print("Testing connection (sending a tiny 'hi')...")
    try:
        r = client.messages.create(
            model=MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        )
        print(f"  Connection OK ({PROVIDER}, {MODEL}). Model replied: {extract_text(r).strip()!r}")
        print(f"  Web search: {'ON (' + SEARCH + ')' if SEARCH else 'OFF - the agent will ask you for links'}")
        return True
    except Exception as e:
        # Print the error TYPE + message so you know exactly what's wrong
        # (bad key, wrong model name, no internet, etc.) — but never the key itself.
        print(f"  Connection FAILED: {type(e).__name__}: {e}")
        return False


# --- 3. One model turn (with cut-off auto-continue) --------------------------
# Sends the current conversation + policy, returns the model's full text reply.
# This is ONE turn. The LOOP (below) calls it repeatedly, once per pass.
#
# system   = the standing instructions (the policy / the agent's brain) — sent every turn
# messages = the WHOLE conversation so far (the model is stateless; we resend history each time)
FAILED = "[the model call failed]"   # sentinel: never saved into the conversation


def with_cache_marker(working: list) -> list:
    """Copy of the conversation with a cache marker on the LAST block of the last message.
    Everything up to the marker is cached, so the next call in this turn (and the next turn,
    within ~5 minutes) reads it at a fraction of the price. The original list isn't changed."""
    if not working:
        return working
    last = dict(working[-1])
    content = last["content"]
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    else:
        content = [dict(b) if isinstance(b, dict) else b for b in content]
    if content and isinstance(content[-1], dict):
        content[-1] = {**content[-1], "cache_control": {"type": "ephemeral"}}
    last["content"] = content
    return working[:-1] + [last]


def one_turn(client, policy: str, messages: list, status=None) -> str:
    # `status` = where progress lines go. Terminal: print. Web app: passes its own function
    # so the lines show up on the page. Same agent logic either way.
    global LAST_USAGE, RUN_COST
    status = status or (lambda line: print(line, flush=True))
    # Simple, clean status so it never looks frozen. (The API call takes ~10-30s.)
    status("\nProcessing...")

    # Layer 3 of the cut-off defense (see BUILD-PLAN): if a reply hits the token
    # ceiling (stop_reason == "max_tokens"), it got cut off mid-thought. We send it
    # back saying "continue" and stitch the pieces, so the user never sees a dangling cut-off.
    full_text = ""
    working = list(messages)  # a copy we extend with tool calls / "continue" turns
    tool_calls = 0
    usage = {"in": 0, "out": 0, "cached": 0, "cache_write": 0, "searches": 0, "calls": 0}
    continuations = 0  # how many times this turn was cut off and continued (capped below)
    while True:
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=16000,     # Phase 2 hit 8,000 twice; cut-offs are where things went wrong
                # PROMPT CACHING: the policy is identical on every call, so we mark it cacheable.
                # The first call stores it (costs a bit extra); later calls within ~5 minutes read
                # it from the cache at ~10% of the normal input price. Tools are cached with it.
                system=[{"type": "text", "text": policy, "cache_control": {"type": "ephemeral"}}],
                # CONVERSATION CACHING: also mark the end of the conversation. Within a turn, each
                # tool-loop call re-sends everything so far (search results, document text); with
                # this marker, the repeated part is read from cache at ~5% of the price.
                messages=with_cache_marker(working),
                tools=TOOLS,          # read_document (ours) + web_search (Anthropic's servers)
            )
        except Exception as e:
            # Actionable error instead of a raw traceback. Tell the user what to do.
            LAST_USAGE = "model call failed"
            status(f"\n[!] Something went wrong talking to the model: {type(e).__name__}: {e}\n"
                   "    Common fixes: wait a minute and try again, check your internet or your API key.")
            return FAILED

        # Cost tally + show any web searches. Searches run on Anthropic's servers, so by the
        # time we see them they're already done; we just print what was searched.
        usage["calls"] += 1
        usage["in"] += response.usage.input_tokens
        usage["out"] += response.usage.output_tokens
        # input_tokens counts only the UNcached part; cached reads are reported separately.
        usage["cached"] += getattr(response.usage, "cache_read_input_tokens", 0) or 0
        usage["cache_write"] += getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        server = getattr(response.usage, "server_tool_use", None)
        usage["searches"] += (getattr(server, "web_search_requests", 0) or 0) if server else 0
        for block in response.content:
            if getattr(block, "type", None) == "server_tool_use":
                status(f"   Searched: {block.input.get('query', '?')}")

        # A long server-side search can come back paused. Send its reply back to let it finish.
        if response.stop_reason == "pause_turn":
            working.append({"role": "assistant", "content": response.content})
            continue

        # THE TOOL LOOP: the model asked us to run a tool. We run it, hand back the
        # result, and call the model again so it can use what it read. Repeat until it answers.
        if response.stop_reason == "tool_use":
            # Pass its full reply back unchanged (incl. thinking blocks) — the API requires it.
            working.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    tool_calls += 1
                    if block.name == "search_web":
                        status(f"   Searched: {block.input.get('query', '?')}")
                    elif block.name == "search_contracts":
                        status(f"   Searching US federal contracts (USAspending.gov): "
                               f"{block.input.get('recipient', '?')}"
                               + (f", {block.input['agency']}" if block.input.get("agency") else ""))
                    else:
                        find = block.input.get("find")
                        find = [find] if isinstance(find, str) else find
                        status(f"   Reading: {block.input.get('source', '?')}"
                               + (f"  (looking for: {', '.join(map(str, find))})" if find else " ..."))
                    output = (run_tool(block.name, block.input) if tool_calls <= MAX_TOOL_CALLS
                              else "[limit reached: no more document reads this turn — answer with what you have]")
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
            working.append({"role": "user", "content": results})
            continue

        full_text += extract_text(response)
        if response.stop_reason == "max_tokens" and continuations >= MAX_CONTINUATIONS:
            # Cap: each continuation is another paid call. Show what we have, and say so.
            full_text += ("\n\n_(This reply hit the length limit and was cut short. Type 'continue' "
                          "for the rest, or move on.)_")
            break
        if response.stop_reason == "max_tokens":
            continuations += 1
            # Cut off. Record what it said so far, then ask it to keep going.
            working.append({"role": "assistant", "content": extract_text(response)})
            # A bare "continue" made the model restart the phase (duplicate Key points) or jump to the
            # next phase. Be explicit: pick up mid-sentence, same phase, no repeats.
            working.append({"role": "user", "content": (
                "[Your reply was cut off by the length limit. Continue EXACTLY where you stopped, "
                "even mid-sentence. Do not repeat anything, do not add a heading or 'Key points', "
                "and do not start the next phase. Be brief, and finish this phase's closing "
                "section, then STOP.]")})
            continue
        break
    LAST_USAGE = (f"{usage['calls']} model call(s), {usage['in']:,} tokens in "
                  f"+ {usage['cached']:,} from cache + {usage['cache_write']:,} stored, {usage['out']:,} out, "
                  f"{usage['searches']} web search(es), {tool_calls} tool call(s)")
    cost = turn_cost(usage, MODEL)
    if cost is not None:
        RUN_COST += cost
        LAST_USAGE += f" | ≈ ${cost:.2f} this turn, ≈ ${RUN_COST:.2f} this run"
    # The detailed line goes in the transcript; the person sees a short cost summary at the pause
    # (printed by run_conversation AFTER the reply, so it isn't scrolled away).
    global COST_SUMMARY
    COST_SUMMARY = cost_summary(cost, usage)
    # NOTE: the raw document text lives only in `working` (this turn). Only the agent's
    # written reply goes into the long-term history — so a 50-page rulebook isn't re-sent
    # (and re-paid for) on every later turn. If it needs the doc again, it re-reads it.
    return full_text or "[no reply text — try again]"


# --- 3b. The PASS LOOP -------------------------------------------------------
# This is where INTENT (policy says "pause after each pass") becomes MECHANISM
# (we actually pause, read the human's reply, remember it, and continue).
#
# How it works, turn by turn:
#   1. We keep a running `messages` list = the ENTIRE conversation.
#   2. Send it -> model replies (e.g. Pass A) -> print it.
#   3. Append the model's reply to history (so it "remembers").
#   4. Read the human's typed reply -> append it to history.
#   5. Loop: send the (now longer) history -> model does the next pass. Repeat.
# The human types 'quit' to stop, or 'save' to write the transcript to a file.
LAST_USAGE = ""

# Moving around: typed commands at a pause become a clear instruction to the model.
# (Code, not policy: the policy can't see what the person typed until we decide what it means.)
JUMP = re.compile(r"^\s*(?:go\s+to\s+|jump\s+to\s+|back\s+to\s+)?phase\s*([1-5])\s*$", re.I)
PHASE_NAMES = {1: "The big picture", 2: "Deep dive", 3: "What you can do", 4: "How to push for change",
               5: "Final brief"}

# THE THREADS, enforced in code. The policy asks the agent to write "Threads: a; b; c" when it sets
# the list (Phase 1) or changes it. We capture the latest one and put it in the reminder on every
# later message, so no thread can quietly drop out, however long the conversation gets.
# Tolerates markdown around it (**Threads:**, `Threads: ...`, "- Threads:") but keeps the content intact.
# Accepts "Areas:" (the user-facing word now) and "Threads:" (the old word).
THREADS_LINE = re.compile(r"^[\s*_>`-]*(?:Areas(?: to dig into)?|Threads):[\s*_`]*(.+?)[\s*_`.]*$",
                          re.I | re.M)
CURRENT_THREADS = ""


def capture_threads(reply: str):
    global CURRENT_THREADS
    found = THREADS_LINE.findall(reply)
    if found:
        CURRENT_THREADS = found[-1].strip()


# WHAT THE PERSON HAS SAID, tracked in code (same idea as threads). Code doesn't try to decide what's
# a question (it can't do that reliably: "tell me more about the data part" has no '?'). It carries
# EVERYTHING the person typed (except commands, empty Enter, dragged-in files) and the MODEL decides
# which are questions to cover and which are answers to use. Model remembers; code makes it impossible
# to forget. Answers matter too: "I'm in Ohio" shouldn't be asked again in every phase.
QUESTIONS: list = []
MAX_REMEMBERED = 12   # keep the reminder short; the oldest items drop off after this


def brief_written(reply: str) -> bool:
    """True only if THIS reply is the final brief. Looks at what's DONE, not what's NEXT: the old
    check saw 'Next: Final brief' after Phase 4 and ended the run before the brief was written."""
    if BRIEF_HEADING.search(reply):
        return True
    done = re.findall(r"Done:([^\n]*)", reply)
    return bool(done) and "final brief" in re.split(r"Next", done[-1], flags=re.I)[0].lower()


def phases_done(reply: str) -> set:
    """Phase numbers listed as DONE in the reply's progress line (not the 'Next' part)."""
    done = re.findall(r"Done:([^\n]*)", reply)
    if not done:
        return set()
    return {int(n) for n in re.findall(r"Phase\s*([1-5])", re.split(r"Next", done[-1], flags=re.I)[0])}


def phase_heading(reply: str, messages: list) -> tuple:
    """(heading text, is_phase). Makes sure every reply says what it is, in code: the model sometimes
    leaves the 'Phase N' heading out. A reply that finishes a new phase is that phase; anything else
    (an answer at a pause) is 'Your question'."""
    if brief_written(reply):
        return "Phase 5: Final brief", True
    before = set().union(*(phases_done(m["content"]) for m in messages if m["role"] == "assistant")) \
        if any(m["role"] == "assistant" for m in messages) else set()
    new = phases_done(reply) - before
    if new:
        n = max(new)
        return f"Phase {n}: {PHASE_NAMES[n]}", True
    if not phases_done(reply) and not before:
        return "First steps", True          # e.g. "what to do today", before Phase 1
    return "Your question", False


def with_heading(reply: str, heading: str) -> str:
    """Put exactly one heading on top. If the model wrote its own matching heading anywhere near the top
    (the Amazon run put a 'Focus' line first, so a second 'Phase 1' heading appeared), it's removed."""
    label, _, name = heading.partition(":")
    def matches(l: str) -> bool:
        f = l.lower()
        return l.lstrip().startswith("#") and (label.lower() in f or (name.strip() and name.strip().lower() in f)
                                               or ("question" in heading.lower() and "question" in f))
    lines = reply.strip().splitlines()
    lines = [l for i, l in enumerate(lines) if not (i < 8 and matches(l))]
    return f"## {heading}\n\n" + "\n".join(lines).strip()


SKEPTIC_RAN: set = set()


def reached_phase_4(messages: list) -> bool:
    """True if any agent reply's progress line says Phase 4 is done."""
    return any(m["role"] == "assistant" and re.search(r"Done:[^\n]*Phase 4", m["content"])
               for m in messages)


def is_file_path(text: str) -> bool:
    """True if the reply is a dragged-in file path (those aren't questions)."""
    try:
        return Path(text.strip().lstrip("&").strip().strip('"').strip("'")).is_file()
    except (OSError, ValueError):
        return False


def capture_question(human: str):
    """Remember what the person said (a question OR an answer), trimmed."""
    QUESTIONS.append(" ".join(human.split())[:160])
    del QUESTIONS[:-MAX_REMEMBERED]


# SOURCE CHECK results from the last reply (see checks.py). Shown to the person, and any quotes that
# weren't found go back to the model in the next reminder so it corrects them.
LAST_FIX_REQUEST = ""
LEDGER = Ledger()

# A "Final brief" heading anywhere in a reply (start of a line). Used to save the brief to its own file.
BRIEF_HEADING = re.compile(r"^#+\s*(?:Phase\s*5\W*)?Final brief", re.I | re.M)
BRIEF_CHECKLIST = (
    " (Final brief checklist, every part required: 1 key points; 2 how the main options differ; 3 one short "
    "section per area: finding, action, ask; 4 what's working; 5 what's new vs. already out there; 6 sources: "
    "'Verified' and 'Needs checking' lists; 7 what a separate reviewer challenged, and what changed as a "
    "result (from the skeptic's points); 8 specialist tools or groups that do a step better than this, with "
    "who runs them and whether they charge; 9 your questions and the defaults I chose; 10 new questions for "
    "the agent; 11 glossary of every term of art used.)")

# "Next: Phase 3, what you can do" in the progress line -> "press Enter to move on to Phase 3, ..."
NEXT_LINE = re.compile(r"Next:\s*([^\n·|]+)")


def translate_command(human: str):
    """Turn 'phase 2', 'back', 'brief' into an instruction. Returns None if it's a normal reply."""
    m = JUMP.match(human)
    if m and m.group(1) == "5":
        return "(Skip ahead and write the final brief now.)"
    if m:
        n = m.group(1)
        return (f"(Go to Phase {n} now. If we've already done it, go deeper on it: don't repeat what "
                f"you said, add what's missing. If we haven't, do it as normal. Then stop.)")
    if human.lower() in ("back", "go back", "previous"):
        return ("(Go back to the previous phase and go deeper: don't repeat what you said, add what's "
                "missing or what I'm likely to care about. Then stop.)")
    if human.lower() in ("continue", "keep going with that", "finish"):
        return ("(Your last reply was cut short. Continue it exactly where it stopped, in the same "
                "phase. Don't repeat anything or start the next phase. Then stop.)")
    if human.lower() in ("brief", "final brief", "wrap up"):
        return "(Skip ahead and write the final brief now.)"
    return None


# --- PER-CONVERSATION STATE --------------------------------------------------
# The variables below hold one conversation's working state. In the terminal there's one conversation.
# In the web version, many visitors share one running program, so each visitor keeps their own copy
# and it's swapped in for their turn (see app.py). Otherwise one visitor's words could leak into
# another visitor's reminders.
def fresh_state() -> dict:
    return {"CURRENT_THREADS": "", "QUESTIONS": [], "LAST_FIX_REQUEST": "", "LEDGER": Ledger(),
            "RUN_COST": 0.0, "LAST_USAGE": "", "COST_SUMMARY": "", "SKEPTIC_RAN": set(),
            "ALREADY_ASKED": set(), "DOC_COPIES": {}}


def use_state(st: dict):
    """Make `st` the active conversation (puts it into the module variables the functions use)."""
    import checks as _checks, tools as _tools
    g = globals()
    for k in ("CURRENT_THREADS", "QUESTIONS", "LAST_FIX_REQUEST", "LEDGER", "RUN_COST", "LAST_USAGE",
              "COST_SUMMARY", "SKEPTIC_RAN"):
        g[k] = st[k]
    _checks.ALREADY_ASKED = st["ALREADY_ASKED"]
    _tools._DOC_COPIES = st["DOC_COPIES"]


def save_state(st: dict):
    """Copy the active conversation's variables back into `st` (some are replaced, not changed)."""
    g = globals()
    for k in ("CURRENT_THREADS", "LAST_FIX_REQUEST", "RUN_COST", "LAST_USAGE", "COST_SUMMARY"):
        st[k] = g[k]


def run_skeptic(client, messages: list, status=print) -> str:
    """Skeptic review of the whole story so far. Returns the text to show; its points go to the writer."""
    global LAST_FIX_REQUEST
    status("   Skeptic reviewing the analysis so far...")
    story = "\n\n---\n\n".join(m["content"] for m in messages if m["role"] == "assistant")
    sk = skeptic_review(client, SKEPTIC_MODEL or MODEL, story, documents_read(), SPARKS_TEXT)
    cost = turn_cost(sk["usage"], SKEPTIC_MODEL or MODEL) or 0.0
    add_cost(cost)
    LAST_FIX_REQUEST += sk_fix_request(sk)
    LEDGER.add_skeptic(sk["items"])
    return sk_summary(sk, full=SKEPTIC_FULL), cost, len(sk["items"])


def process_reply(client, reply: str, messages: list, usage_log: list, status=print) -> dict:
    """Everything after the writer replies: audit the labels, record, review.
    Returns {shown, check_lines, skeptic, finished, brief, checks_cost}. Used by the terminal and the web."""
    global LAST_FIX_REQUEST
    # AUDIT BEFORE SHOWING. The writer proposes labels (only it knows where each claim came from);
    # the checks audit them; the person reads the audited version.
    usage_log.append(LAST_USAGE)
    capture_threads(reply)
    heading, is_phase = phase_heading(reply, messages)
    reply = with_heading(reply, heading)
    # Answers to questions are checked by a faster model (they're short and come often); phases by the
    # main checker. Haiku scored 12/14 with 1 false alarm vs Sonnet's 12/14 with none (eval_factcheck.py).
    checker = (FACT_CHECK_MODEL or MODEL) if is_phase else (ANSWER_CHECK_MODEL or FACT_CHECK_MODEL or MODEL)
    # 1. Quote check (code, certain): a quote that isn't in the document loses its [VERIFIED] tag.
    results = check_quotes(reply, document_texts())
    line = summary_line(results)
    LAST_FIX_REQUEST = fix_request(results)
    shown = apply_quote_labels(reply, results)
    check_lines = [line] if line else []
    # 2. Fact check (separate model call): problems are marked next to the claim, visibly.
    checks_cost = 0.0
    if FACT_CHECK and needs_check(reply):
        status("   Checking the sources before showing the reply...")
        fc = fact_check(client, checker, reply)
        checks_cost = turn_cost(fc["usage"], checker) or 0.0
        add_cost(checks_cost)
        shown, unplaced = apply_fact_marks(shown, fc)
        # Unconfirmed claims the checker found in a document become [VERIFIED], if code confirms
        # the checker's quote is really there. They also count as verified quotes in the sources file.
        shown, fc["upgraded"] = apply_upgrades(shown, fc, document_texts())
        results += [{"quote": u["quote"], "source": u["source"] + " (confirmed by the fact checker)",
                     "found": True, "line": None} for u in fc["upgraded"]]
        check_lines.append(fc_summary(fc, unplaced))
        LAST_FIX_REQUEST += fc_fix_request(fc)
        LEDGER.add_fact_problems(fc["problems"])
        LEDGER.add_confirm(fc.get("confirm", []))
        usage_log[-1] += (f" | Fact check: {fc['checked']} checked, {len(fc['problems'])} problem(s), "
                          f"≈ ${checks_cost:.2f}")
    # 3. The "Areas: a; b; c" line is for the code (it carries the areas into every reminder), not for
    # the person, so it's hidden. The AUDITED version is what the writer sees from now on.
    shown = THREADS_LINE.sub("", shown).replace("\n\n\n", "\n\n")
    messages.append({"role": "assistant", "content": shown})
    # 4. SKEPTIC after each phase: review the whole story so far (argument level).
    skeptic = ""
    due = (phases_done(reply) & SKEPTIC_AFTER) - SKEPTIC_RAN
    if due and not brief_written(reply):
        SKEPTIC_RAN.update(due)
        skeptic, sk_cost, n = run_skeptic(client, messages, status)
        checks_cost += sk_cost
        usage_log[-1] += f" | Skeptic: {n} item(s), ≈ ${sk_cost:.2f}"
    LEDGER.add(shown, results)   # the audited version: upgraded claims leave the "needs checking" list
    usage_log[-1] += (" | " + line.splitlines()[0]) if line else ""
    brief_at = BRIEF_HEADING.search(shown)
    return {"shown": shown, "check_lines": check_lines, "skeptic": skeptic, "checks_cost": checks_cost,
            "finished": brief_written(reply), "brief": shown[brief_at.start():] if brief_at else "",
            "heading": heading}


def prepare_message(client, human: str, last_reply: str, messages: list, finished: bool,
                    allow_files: bool = True, status=print) -> str:
    """Turn what the person typed into the next message: commands, remembered words, defaults,
    the brief checklist, and the reminder. Used by the terminal and the web."""
    global LAST_FIX_REQUEST
    if not human and not finished and over_budget():
        human = "brief"   # over budget: Enter means "wrap up", not "another phase"
    command = translate_command(human)
    if command:
        human = command
        # Brief requested before the Phase 4 review happened (Phase 4 skipped): review the whole
        # story first, so the part people share is reviewed. Its points go into this brief request.
        if "final brief" in command.lower() and 4 not in SKEPTIC_RAN:
            SKEPTIC_RAN.add(4)
            text, _, _ = run_skeptic(client, messages, status)
            status("   " + text)
    elif human and not (allow_files and is_file_path(human)):
        capture_question(human)
    # A dragged-in file (terminal only; the web version never reads files from the server).
    added = add_document(human) if allow_files else None
    if added:
        status(f"   Added '{added}' to the docs folder.")
        human = f"I added a document for you to read: '{added}' (it's in the docs folder)."
    # Nothing typed: move on with sensible defaults, and say which ones.
    if not human:
        human = ("(No reply. Please continue to the next phase. Use sensible defaults for "
                 "any open questions and tell me in one line which ones you chose.)")
    # The brief skipped required parts in two runs despite the policy, so code adds the checklist
    # whenever the brief is what comes next (asked for, or Enter after Phase 4).
    nxt = NEXT_LINE.search(last_reply.split("Done:")[-1])
    if "final brief" in human.lower() or (human.startswith("(No reply") and nxt
                                          and "final brief" in nxt.group(1).lower()):
        human += BRIEF_CHECKLIST
    return human + reminder()


def next_phase_label(reply: str) -> str:
    nxt = NEXT_LINE.search(reply.split("Done:")[-1])
    return nxt.group(1).strip(" .*") if nxt else ""


def run_conversation(client, policy: str, user_opening: str):
    messages = [{"role": "user", "content": user_opening + reminder()}]
    usage_log = []   # one cost line per agent turn, saved with the transcript
    finished = False  # True once the final brief is out: the pause prompt changes
    # Transcript is saved automatically after every turn (no 'save' command needed).
    transcript = TRANSCRIPT_DIR / f"run-{datetime.now():%Y%m%d-%H%M%S}.md"
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    sources_file = transcript.with_name(transcript.stem + "-sources.md")
    brief_file = transcript.with_name(transcript.stem + "-brief.md")
    print(f"(Saving as you go to {TRANSCRIPT_DIR.name}/: the conversation, a sources list, and the brief)")

    while True:
        # --- model's turn ---
        reply = one_turn(client, policy, messages)
        if reply == FAILED:
            # Don't save a failure into the conversation (run 4 did, and lost the brief).
            # The last message is still waiting for an answer, so Enter simply resends it.
            again = input("\nPress Enter to try again, or type 'quit': ").strip().lower()
            if again in ("quit", "exit"):
                print(f"Stopping. Transcript saved at {transcript}")
                break
            continue
        out = process_reply(client, reply, messages, usage_log,
                            status=lambda l: print(l, flush=True))
        print("\n" + "-" * 70)
        render(out["shown"])
        print("-" * 70)
        for l in out["check_lines"]:
            print("   " + l)
        if out["skeptic"]:
            print("   " + out["skeptic"])
        LEDGER.write(sources_file, documents_read())
        save_transcript(messages, transcript, usage_log)
        finished = finished or out["finished"]
        if out["brief"]:   # the brief on its own, so it can be shared without the whole conversation
            brief_file.write_text(out["brief"], encoding="utf-8")
            print(f"   (Final brief saved to {brief_file.name})")

        # --- human's turn (the PAUSE) ---
        if COST_SUMMARY:
            print("\n   " + COST_SUMMARY + (f"\n      Checks (fact checker / skeptic): ≈ ${out['checks_cost']:.2f} "
                                             f"(included in the run total ≈ ${RUN_COST:.2f})"
                                             if out["checks_cost"] else ""))
        note = budget_note()
        if note and not finished:
            print(note)
        if finished:
            print(END_PROMPT)
        else:
            nxt = next_phase_label(reply)
            print(PAUSE_PROMPT.replace("move on", f"move on to {nxt}" if nxt else "move on"))
        human = input("> ").strip()
        if human.lower() in ("quit", "exit") and not finished and reached_phase_4(messages):
            # The health-insurance run reached Phase 4 and ended without a brief. Offer it once.
            ans = input("You haven't got the final brief yet. Write it before you go? (Enter = yes, "
                        "'n' = quit now): ").strip().lower()
            if ans in ("", "y", "yes"):
                human = "brief"
        if human.lower() in ("quit", "exit") or (finished and not human):
            print(f"Stopping. Transcript saved at {transcript}")
            break
        messages.append({"role": "user", "content": prepare_message(
            client, human, reply, messages, finished, status=lambda l: print(l, flush=True))})


def save_transcript(messages: list, out: Path, usage_log: list = ()):
    """Write the conversation so far to a markdown file (called after every turn)."""
    out.write_text(transcript_text(messages, usage_log), encoding="utf-8")


def transcript_text(messages: list, usage_log: list = ()) -> str:
    """The conversation as markdown, without the internal reminders (also the web page's download)."""
    lines, turn = [], 0
    for m in messages:
        who = "YOU" if m["role"] == "user" else "AGENT"
        text = m["content"].split(REMINDER_MARK)[0]  # hide our internal re-anchor
        lines.append(f"## {who}\n\n{text}\n")
        if who == "AGENT" and turn < len(usage_log):
            lines.append(f"_(usage: {usage_log[turn]})_\n")  # cost per turn, for later analysis
            turn += 1
    return "\n".join(lines)


def extract_text(response) -> str:
    """Pull the human-readable text out of a response, skipping thinking/tool blocks."""
    # Join with "" not "\n": when the model cites a search result, its sentence comes back split into
    # several text blocks around the quoted part. Newlines between them broke sentences apart.
    return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")


# --- 4. Main -----------------------------------------------------------------
PATH_BANNER = """
==============================================================
 HOW THIS WORKS: we go one phase at a time. I pause after each, so you can
 ask questions, go deeper on what interests you, or move on.
   Phase 1  The big picture: what it is, the key points, how the main options
            differ, and the most surprising things from a first look
   Phase 2  Deep dive: each area in depth: costs, fine print,
            who's on the other side, what protects you and what doesn't
   Phase 3  What you can do: practical steps for you and people you care about
   Phase 4  How to push for change: specific ways to fix what's broken
   Phase 5  Final brief: a one-page summary to keep or share
==============================================================
"""

# Shown after the person picks a topic (the "first click"), before Phase 1 appears.
HOW_TO_READ = """
HOW TO READ WHAT FOLLOWS
  [VERIFIED: source, where]   I read this source myself (a document or web page) and
                              quote it. It means the source really says this. Whether
                              to trust the source depends on who wrote it.
  [CHECK: why; what, where]   Probably right, not confirmed. Says why (e.g. snippet only,
                              couldn't open), and what to confirm, and where.
  [UNVERIFIED: why]           Not checked against any source: general knowledge (may be
                              out of date or wrong), or my own inference or arithmetic.
                              Treat it as a lead, not a fact.
  Before you see each reply, a separate checker compares its sourced claims with the
  documents. Problems are marked [FACT CHECK: ...] next to the claim.
"""

# Re-anchor sent with EVERY human turn. The policy SAYS "stop after each phase",
# but long policies drift — the model forgot to stop after Phase 0. Code guarantees it.
# It also tells the model how to treat a QUESTION (answer, then return to the same pause)
# vs. "keep going" (do the next phase), and lists documents it can re-read.
REMINDER_MARK = "\n\n[Instruction:"   # used to strip this from the saved transcript


def reminder() -> str:
    docs = documents_read()
    doc_line = (" Documents read so far (re-read them for exact wording when you go deeper): "
                + "; ".join(docs) + "." if docs else "")
    return (
        REMINDER_MARK + " If my message asks a question, answer it briefly now, or say which phase "
        "will cover it. If my message gives you a document, read it, then only confirm in two or "
        "three lines what it is and the one thing most worth digging into, and say which phase will "
        "cover it in full. Do NOT analyze it now; save that for the phase. In both cases, repeat where "
        "we paused (the open questions and 'Next: Phase N') and STOP. If my message says which phase "
        "to go to (or to go back, or to write the brief), do exactly that. Otherwise, do ONLY the next "
        "phase: begin with its heading ('## Phase N: name'), then 'Key points' (each with its 'So what'; "
        "Phase 1 is a short map, under 300 words, one line per bullet), "
        "and end with the progress line ('Done: ... · Next: Phase N, name'). Then STOP and wait for me. In "
        "Phase 3, give an action for each earlier key point that matters; in Phase 4, a change to push "
        "for on each one that's broken (or say there isn't one), each with Ask, To (the exact office), How "
        "(the channel) and Why. Don't re-ask questions you've already "
        "chosen a default for. "
        "Put every question for me ONLY in the 'Questions for you' section at the very end, "
        "never in the middle of the text."
        + (f" The areas to dig into (cover every one, in this order, under these names; add new "
           f"ones if needed): {CURRENT_THREADS}." if CURRENT_THREADS else "")
        + (" What I've told or asked you so far (answer my questions where they belong and say so; "
           "use my answers, and don't ask again what I've already answered. These are the ONLY "
           "things I've said; your 'You could also ask' suggestions are not my questions): "
           + "; ".join(f"({i}) {q}" for i, q in enumerate(QUESTIONS, 1)) + "." if QUESTIONS else "")
        + LAST_FIX_REQUEST
        + doc_line + "]"
    )


PAUSE_PROMPT = """
YOUR TURN:
  • Answer the questions above, then I'll go on to the next phase (skip any; I'll use defaults)
  • Or ask anything: a new question, something unclear, or "more on <a point>" to go deeper.
    I'll answer and stay here until you're ready to move on
  • Or paste a link, or drag a file into this window, for me to read
  • Or move around: 'phase 2' to jump (or go deeper on one we've done), 'back', 'brief'
  • Or just press Enter to move on
  • Or type 'quit' to stop"""

# After the final brief there's nothing to "move on" to, so the prompt changes.
END_PROMPT = """
THAT'S THE FULL PATH. ANYTHING ELSE?
  • Ask a question, or name a topic to go deeper on (e.g. a thread that got too little attention)
  • Or 'phase 2' (etc.) to revisit a phase in more depth
  • Or press Enter (or type 'quit') to finish"""

ALLOWED_DOC_TYPES = {".pdf", ".txt", ".md", ".html", ".htm"}


def add_document(raw: str):
    """If the person dragged a file into the terminal (which pastes its path), copy it into the
    docs folder and return its name. The model can still only read inside the docs folder."""
    candidate = raw.strip().lstrip("&").strip().strip('"').strip("'")
    try:
        path = Path(candidate)
        if path.is_file() and path.suffix.lower() in ALLOWED_DOC_TYPES:
            DOCS_DIR.mkdir(exist_ok=True)
            shutil.copy(path, DOCS_DIR / path.name)
            return path.name
    except (OSError, ValueError):
        pass
    return None


def render(text: str):
    """Show the model's reply as formatted markdown if 'rich' is installed, else plain."""
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        Console().print(Markdown(text))
    except ImportError:
        print(text)


def main():
    # Show something IMMEDIATELY — startup (loading + connection test) takes a few seconds.
    print("Starting up... (loading the policy, connecting to the model)", flush=True)
    policy = load_policy()
    client = make_client()

    # Step 2b: prove we can reach the model before spending tokens on the big policy.
    if not test_connection(client):
        print("Stopping — fix the connection above, then re-run.")
        sys.exit(1)

    # THE OPENING = the human's first message that kicks the agent off. You TYPE it,
    # so it feels concrete. It is NOT the rules/phases (those live in the policy).
    # 1) The intro: what we'll do together.
    print(PATH_BANNER)
    default_opening = "I want to understand prediction markets (like Kalshi and Polymarket)."
    print("What system or problem do you want to look at? (press Enter for the example)")
    print(f'  Example: "{default_opening}"')
    typed = input("> ").strip()
    user_opening = typed if typed else default_opening

    # 2) After the first click: the specifics of how to read the answers.
    print(HOW_TO_READ)
    print("=" * 70)
    run_conversation(client, policy, user_opening)
    print("=" * 70)
    print("(Done.)")


if __name__ == "__main__":
    main()
