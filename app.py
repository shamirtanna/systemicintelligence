"""
The web version of the SI agent (Streamlit). Same agent, same checks, in a browser.

Run locally:  python -m streamlit run app.py
Settings (Streamlit secrets on the host, or .env locally):
  ANTHROPIC_API_KEY  required
  ACCESS_CODE        if set, visitors must enter it (keeps strangers from spending your money)
  VISITOR_BUDGET     dollars per visitor (falls back to RUN_BUDGET, then 3.00). At the limit: one final
                     brief, then it stops.
  SAVE_TRANSCRIPTS   1 = save each conversation to transcripts/ (LOCAL TESTING ONLY; never on the host)
Safety: no file uploads, no reading files on the server, nothing saved on the server by default.
"""
import os
import threading
from datetime import datetime

import streamlit as st

# Settings from Streamlit secrets (on the host) go into the environment BEFORE the agent loads.
try:
    for k, v in st.secrets.items():
        if isinstance(v, (str, int, float)):
            os.environ.setdefault(k, str(v))
except Exception:
    pass   # no secrets file locally: the agent's .env is used instead
os.environ["SI_WEB_MODE"] = "1"          # tools.py: never read files from the server
os.environ.setdefault("PROVIDER", "anthropic")
for k, v in {"PRICE_IN": "2", "PRICE_OUT": "10", "PRICE_CACHE_WRITE": "2.50", "PRICE_CACHE_READ": "0.10",
             "PRICE_SEARCH_PER_1000": "10"}.items():   # Sonnet 5.5 defaults, so the budget always works
    os.environ.setdefault(k, v)

import si_agent as s  # noqa: E402  (must load after the settings above)
import tools  # noqa: E402
from skeptic import SK_INTRO  # noqa: E402

VISITOR_BUDGET = float(os.environ.get("VISITOR_BUDGET") or os.environ.get("RUN_BUDGET") or 3.00)
ACCESS_CODE = os.environ.get("ACCESS_CODE", "").strip()
SAVE = os.environ.get("SAVE_TRANSCRIPTS", "").strip() == "1"
EXAMPLE = "My insurer denied a claim for an MRI my doctor ordered."


@st.cache_resource
def _shared():
    """One client and one lock for the whole server. The lock makes visitors take turns: the agent's
    working state is swapped in per visitor, so only one turn may run at a time."""
    return s.make_client(), threading.Lock()


@st.cache_data
def _policy(changed: float) -> str:
    """The policy, reloaded whenever its files change (it used to load once, so edits needed a restart)."""
    return s.load_policy()


def shared():
    client, lock = _shared()
    files = [s.POLICY_PATH, s.POLICY_PATH.parent / "CASEBOOK-SPARKS.md"]
    return client, _policy(sum(f.stat().st_mtime for f in files if f.exists())), lock


def display(text: str) -> str:
    """Tidy the agent's text for Streamlit's markdown:
    - `code` shows in a colour that looks like a warning (the agent's text has no real code)
    - HTML underlines (<u>) the model sometimes adds show up as raw tags
    - a pair of $ signs is read as a math formula ("$25 million ... $9 billion" turns into garbled
      italics), so every $ is escaped to show as a plain dollar sign."""
    import re
    text = re.sub(r"(?:<|&lt;)/?(u|br|span)[^>]*?(?:>|&gt;)", "", text.replace("`", ""))
    return re.sub(r"(?<!\\)\$", r"\\$", text)


def link(source: str) -> str:
    """A clickable link for a document the agent read (web address), or just its name (a file)."""
    if not source.startswith(("http://", "https://")):
        return source
    from urllib.parse import urlparse
    u = urlparse(source)
    tail = u.path.rstrip("/").split("/")[-1] or u.netloc
    return f"[{u.netloc}: {tail[:60]}]({source})"


st.set_page_config(page_title="Systemic Intelligence", page_icon="🔎", layout="centered")
st.title("Systemic Intelligence")
st.caption("Understand a system that affects you, what you can do, and how to push for change.")

# --- access code ---
if ACCESS_CODE and not st.session_state.get("ok"):
    code = st.text_input("Access code", type="password")
    if code:
        if code.strip() == ACCESS_CODE:
            st.session_state.ok = True
            st.rerun()
        st.error("That code didn't work.")
    st.stop()

# --- one visitor's conversation (a page refresh starts a new one) ---
ss = st.session_state
# Each piece is set on its own, so a session started under an older version of this page still gets
# anything added later (a missing "transcript" crashed a session that was open during an update).
for key, make in (("si", s.fresh_state), ("messages", list), ("usage_log", list), ("chat", list),
                  ("finished", lambda: False), ("last_reply", str), ("brief", str), ("sources", str),
                  ("transcript", lambda: (s.TRANSCRIPT_DIR / f"web-{datetime.now():%Y%m%d-%H%M%S}.md")
                   if SAVE else None)):
    if key not in ss:
        ss[key] = make()
for key, value in s.fresh_state().items():   # same for the agent's own state
    ss.si.setdefault(key, value)

with st.expander("How this works, and how to read it", expanded=not ss.chat):
    st.markdown(
        "**We go one phase at a time.** I pause after each, so you can ask questions, go deeper, or move on.\n"
        "1. **The big picture:** what it is, the key points, how the main options differ\n"
        "2. **Deep dive:** each area in depth: costs, fine print, who's on the other side\n"
        "3. **What you can do:** practical steps, ready-to-send messages\n"
        "4. **How to push for change:** specific asks, to whom, and how\n"
        "5. **Final brief:** a one-page summary to keep or share\n\n"
        "**Every factual claim has one of three labels:**\n"
        "- **[VERIFIED: source]** I read the source and quote it\n"
        "- **[CHECK: why]** probably right, but not confirmed. Says what to confirm, and where\n"
        "- **[UNVERIFIED: why]** general knowledge or my own reasoning. Treat it as a lead\n\n"
        "**How the labels are kept honest:** before you see a reply, every quote is checked word for word "
        "against the documents, and a separate checker compares the claims with the sources (and with "
        "each other). If a claim doesn't hold up, its label changes to [CHECK] with the reason; if it has "
        "no source at all, to [UNVERIFIED].\n\n"
        f"**The Skeptic, after each phase:** {SK_INTRO}\n\n"
        "**You are the last check.** Confirm anything important before acting on it.\n\n"
        "**Privacy:** nothing is saved on this server. Your messages are sent to Anthropic's API to write "
        "the answers, so don't type personal details (names, addresses, policy or account numbers).\n\n"
        "**Not advice:** this explains systems; it isn't legal, medical or financial advice.")


def show_turn(turn: dict):
    st.markdown(display(turn["text"]))
    if turn.get("sources"):
        with st.expander(f"Sources read for this reply ({len(turn['sources'])}): open them yourself"):
            st.markdown("\n".join(f"- {link(d)}" for d in turn["sources"]))
    if turn.get("checks"):
        with st.expander("How this reply was checked, and what to confirm"):
            for c in turn["checks"]:
                st.markdown(display(c).replace("\n   ", "\n"))
    if turn.get("skeptic"):
        with st.expander("The Skeptic: a separate reviewer's challenge"):
            st.markdown(SK_INTRO)
            st.markdown(display(turn["skeptic"]))
    if turn.get("cost"):
        st.caption(turn["cost"])


for turn in ss.chat:
    with st.chat_message(turn["role"]):
        if turn["role"] == "user":
            st.markdown(turn["text"])
        else:
            show_turn(turn)


def run_turn(user_text: str, human: str | None):
    """Send one message and show the audited reply. `human` = what the visitor typed (None = opening)."""
    client, policy, lock = shared()
    ss.chat.append({"role": "user", "text": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)
    with st.chat_message("assistant"):
        # Open by default, so the visitor watches the work happen (searches, documents, checks).
        box = st.status("Working: searching, reading and checking. This usually takes 1 to 3 minutes...",
                        expanded=True)
        if lock.locked():
            box.update(label="Another visitor's turn is running (each takes 1 to 3 minutes). Yours starts when it finishes...",
                       state="running", expanded=True)
        with lock:
            box.update(label="Working: searching, reading and checking. This usually takes 1 to 3 minutes...",
                       state="running", expanded=True)
            s.use_state(ss.si)
            tools.READ_THIS_TURN.clear()        # reset under the lock, so it only holds this reply's reads
            try:
                if human is None:
                    ss.messages.append({"role": "user", "content": user_text + s.reminder()})
                else:
                    ss.messages.append({"role": "user", "content": s.prepare_message(
                        client, human, ss.last_reply, ss.messages, ss.finished, allow_files=False,
                        status=box.write)})
                reply = s.one_turn(client, policy, ss.messages, status=box.write)
                if reply == s.FAILED:
                    ss.messages.pop()          # not saved; the visitor can simply send it again
                    box.update(label="Something went wrong talking to the model. Try again.", state="error")
                    return
                out = s.process_reply(client, reply, ss.messages, ss.usage_log, status=box.write)
                ss.sources = s.LEDGER.text(s.documents_read())   # nothing written to the server's disk
                if ss.transcript:                                # local testing only
                    s.TRANSCRIPT_DIR.mkdir(exist_ok=True)
                    s.save_transcript(ss.messages, ss.transcript, ss.usage_log)
                    ss.transcript.with_name(ss.transcript.stem + "-sources.md").write_text(ss.sources, encoding="utf-8")
                cost = s.COST_SUMMARY.replace("\n", " ").replace("      ", " ")
                sources = list(tools.READ_THIS_TURN)   # every document this reply opened, incl. re-reads
            finally:
                s.save_state(ss.si)
        box.update(label="Done", state="complete")
        turn = {"role": "assistant", "text": out["shown"], "checks": out["check_lines"],
                "skeptic": out["skeptic"], "cost": cost, "sources": sources}
        show_turn(turn)
    ss.chat.append(turn)
    ss.last_reply = reply
    ss.finished = ss.finished or out["finished"]
    if out["brief"]:
        ss.brief = out["brief"]


def progress() -> str:
    done = set().union(*(s.phases_done(m["content"]) for m in ss.messages if m["role"] == "assistant")) \
        if ss.messages else set()
    if ss.finished:
        done |= {5}
    nxt = next((n for n in range(1, 6) if n not in done), None)
    return "  ·  ".join(f"✓ {n} {s.PHASE_NAMES[n]}" if n in done else
                        (f"**→ {n} {s.PHASE_NAMES[n]}**" if n == nxt else f"{n} {s.PHASE_NAMES[n]}")
                        for n in range(1, 6))


spent = ss.si["RUN_COST"]
over = spent >= VISITOR_BUDGET

if not ss.chat:
    with st.form("start"):
        st.markdown("**What system or problem do you want to look at?** For example:\n"
                    "- prediction markets\n- my health insurance\n- my rent keeps going up\n"
                    f"- {EXAMPLE.lower().rstrip('.')}")
        topic = st.text_input("Your topic", placeholder=f"Press Enter to use the example: {EXAMPLE}",
                              label_visibility="collapsed")
        if st.form_submit_button("Start"):
            text = topic.strip() or EXAMPLE
            run_turn(text, None)
            st.rerun()
else:
    st.markdown(progress())
    st.caption(f"Spent so far ≈ ${spent:.2f} of this visit's ${VISITOR_BUDGET:.2f} limit.")
    if over and ss.finished:
        st.info("This visit has reached its limit. Download your brief below. Thanks for trying it!")
    elif over:
        st.info("This visit has reached its limit, so the next step is the final brief.")
        if st.button("Write the final brief"):
            run_turn("Write the final brief.", "brief")
            st.rerun()
    else:
        nxt = s.next_phase_label(ss.last_reply)
        cols = st.columns(2)
        if not ss.finished and cols[0].button(f"Continue: {nxt}" if nxt else "Continue"):
            run_turn("Continue.", "")
            st.rerun()
        if not ss.finished and cols[1].button("Skip to the final brief"):
            run_turn("Skip to the final brief.", "brief")
            st.rerun()
        if not ss.finished:   # the nudge: the person's own questions and experience steer the next part
            st.markdown("**Worth a moment:** What isn't clear? What doesn't make sense to you? What could be "
                        "an issue for you, or for people you know? Say it below: it shapes what I dig into next.")
        # A form, not st.chat_input: chat_input ignores an empty Enter, and Enter should move you on.
        go_to = f"continue to {nxt}" if nxt and not ss.finished else "send"
        with st.form("reply", clear_on_submit=True):
            text = st.text_input("Your reply", label_visibility="collapsed",
                                 placeholder=f"Answer, ask anything, or say \"more on ...\". "
                                             f"Press Enter with nothing typed to {go_to}.")
            sent = st.form_submit_button("Send")
        if sent:
            if text.strip():
                run_turn(text.strip(), text.strip())
            elif not ss.finished:
                run_turn("Continue.", "")
            st.rerun()

if ss.brief:
    st.download_button("Download the final brief", ss.brief, file_name="brief.md")
if ss.sources:
    st.download_button("Download the sources list (verified, needs checking, checks)", ss.sources,
                       file_name="sources.md")
if ss.messages:
    # Nothing is saved on the server, so testers who want to help share their session by choice:
    # download it, read it, then send it (and remove anything personal first).
    st.download_button("Download this conversation (to share feedback, if you'd like)",
                       s.transcript_text(ss.messages, ss.usage_log), file_name="conversation.md")
    st.caption("Helping test this? Downloading and sending your conversation shows how people really use "
               "it: what you asked, where you got stuck. Remove anything personal first. It's never saved here.")
