"""
The web version of the SI agent (Streamlit). Same agent, same checks, in a browser.

Run locally:  streamlit run app.py
Settings (Streamlit secrets on the host, or .env locally):
  ANTHROPIC_API_KEY  required
  ACCESS_CODE        if set, visitors must enter it (keeps strangers from spending your money)
  VISITOR_BUDGET     dollars per visitor (default 2.50). At the limit: one final brief, then it stops.
Safety: no file uploads, no reading files on the server, nothing saved on the server.
"""
import os
import threading

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

VISITOR_BUDGET = float(os.environ.get("VISITOR_BUDGET", "2.50") or 2.50)
ACCESS_CODE = os.environ.get("ACCESS_CODE", "").strip()
EXAMPLE = "My insurer denied a claim for an MRI my doctor ordered."


@st.cache_resource
def shared():
    """One client, one policy, and one lock for the whole server. The lock makes visitors take turns:
    the agent's working state is swapped in per visitor, so only one turn may run at a time."""
    return s.make_client(), s.load_policy(), threading.Lock()


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

# --- one visitor's conversation ---
ss = st.session_state
if "si" not in ss:
    ss.si = s.fresh_state()      # this visitor's own working state (areas, their words, documents)
    ss.messages, ss.usage_log, ss.chat = [], [], []
    ss.finished, ss.last_reply, ss.brief, ss.sources = False, "", "", ""

with st.expander("How this works, and how to read it", expanded=not ss.chat):
    st.markdown(
        "We go one phase at a time, and I pause after each so you can ask questions, go deeper, or move on:\n"
        "1. **The big picture** · 2. **How it really works** · 3. **What you can do** · "
        "4. **How to push for change** · then a **final brief**.\n\n"
        "**Labels.** **[VERIFIED: source]** I read it and quote it · **[CHECK: why]** probably right, not "
        "confirmed (says what to confirm, and where) · **[UNVERIFIED: why]** general knowledge or my own "
        "reasoning. Before you see each reply, a separate checker compares its sourced claims with the "
        "documents and marks problems **[FACT CHECK: ...]**. You are the last check: confirm anything "
        "important before acting on it.\n\n"
        "**Privacy.** Nothing is saved on this server. Your messages are sent to Anthropic's API to write "
        "the answers. Don't type personal details (names, addresses, policy or account numbers).\n\n"
        "**Not advice.** This explains systems; it isn't legal, medical or financial advice.")

for turn in ss.chat:
    with st.chat_message(turn["role"]):
        st.markdown(turn["text"])
        for extra in turn.get("extras", []):
            st.caption(extra)


def run_turn(user_text: str, human: str | None):
    """Send one message and show the audited reply. `human` = what the visitor typed (None = opening)."""
    client, policy, lock = shared()
    ss.chat.append({"role": "user", "text": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)
    with st.chat_message("assistant"):
        box = st.status("Working: searching, reading and checking (this can take a minute or two)...")
        with lock:
            s.use_state(ss.si)
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
                cost_line = s.COST_SUMMARY.replace("\n", " ").replace("      ", " ")
            finally:
                s.save_state(ss.si)
        box.update(label="Done", state="complete")
        st.markdown(out["shown"])
        extras = out["check_lines"] + ([out["skeptic"]] if out["skeptic"] else []) + [cost_line]
        for extra in extras:
            st.caption(extra)
    ss.chat.append({"role": "assistant", "text": out["shown"], "extras": extras})
    ss.last_reply = reply
    ss.finished = ss.finished or out["finished"]
    if out["brief"]:
        ss.brief = out["brief"]


spent = ss.si["RUN_COST"]
over = spent >= VISITOR_BUDGET

if not ss.chat:
    st.markdown("**What system or problem do you want to look at?** A topic (\"prediction markets\", "
                "\"my health insurance\") or something that happened to you.")
    if st.button(f"Try the example: {EXAMPLE}"):
        run_turn(EXAMPLE, None)
        st.rerun()
    topic = st.chat_input("Type a topic or what happened...")
    if topic:
        run_turn(topic, None)
        st.rerun()
else:
    st.caption(f"Spent so far ≈ ${spent:.2f} of this visit's ${VISITOR_BUDGET:.2f} limit.")
    if over and ss.finished:
        st.info("This visit has reached its limit. Download your brief below. Thanks for trying it!")
    elif over:
        st.warning("This visit has reached its limit, so the next step is the final brief.")
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
        text = st.chat_input("Answer the questions, ask anything, or say \"more on ...\"")
        if text:
            run_turn(text, text)
            st.rerun()

if ss.brief:
    st.download_button("Download the final brief", ss.brief, file_name="brief.md")
if ss.sources:
    st.download_button("Download the sources list (verified, needs checking, checks)", ss.sources,
                       file_name="sources.md")
