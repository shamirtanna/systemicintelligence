"""
Tools the agent can call.

A "tool" is just: (1) a DESCRIPTION we send the model so it knows the tool exists, and
(2) a normal Python function WE run when the model asks for it. The model never runs code
itself. It replies "please call read_document with these inputs", our code runs the
function, and we send the result back. That back-and-forth is the TOOL LOOP (in si_agent.py).

Tool 1: read_document — read a web page, a PDF link, or a file you put in agent/docs/.
"""

import io
from html.parser import HTMLParser
from pathlib import Path

import httpx  # installed alongside the anthropic library

DOCS_DIR = Path(__file__).parent / "docs"   # "upload" = drop a file here
MAX_CHARS = 30000      # per call, so one huge rulebook doesn't blow up cost
MAX_DOWNLOAD = 20_000_000  # 20 MB safety cap on downloads
SHELL_THRESHOLD = 600  # a web page with less text than this is probably a JavaScript "empty shell"

# Documents already read in THIS run, kept in memory (gone when you quit). Re-reading in Phase 2
# is then instant and doesn't hit the website again (which helps with sites that rate-limit).
_DOC_COPIES: dict[str, str] = {}


def documents_read() -> list[str]:
    """The documents read so far this run (shown to the model so it knows it can re-read them)."""
    return list(_DOC_COPIES)


def document_texts() -> dict:
    """Full text of every document read this run (used by checks.py to verify quotes)."""
    return dict(_DOC_COPIES)

# --- 1. The DESCRIPTION the model sees ---------------------------------------
TOOLS = [
    {
        "name": "read_document",
        "description": (
            "Read the text of a document so you can quote it directly. Use this for the primary "
            "documents that matter (terms of service, member agreements, rulebooks, risk "
            "disclosures, fee schedules, regulator reports, court rulings). Works with a web "
            "URL (web pages or PDF links) or the name of a file the user placed in the docs "
            "folder. Long documents come back in chunks: if the result says there is more, "
            "call again with a larger 'start'. PDF text includes [page N] markers. Cite them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "A full URL (https://...) or a file name in the docs folder.",
                },
                "start": {
                    "type": "integer",
                    "description": "Character position to start from (for long docs). Default 0.",
                },
                "find": {
                    "type": "array", "items": {"type": "string"},
                    "description": (
                        "Optional: words or phrases to look for (not case-sensitive). Returns ONLY "
                        "the passages that contain them, each with its page and position, instead "
                        "of a full chunk. Much cheaper for long documents. Include synonyms "
                        "(e.g. ['arbitration', 'dispute', 'class action']). To see more around a "
                        "passage, call again with start=<its position> and no find."
                    ),
                },
            },
            "required": ["source"],
        },
    },
]

# Tool 2: web_search. A SERVER tool: Anthropic's servers run the search, so there's no Python
# function for it and run_tool never sees it. The results come back inside the model's response.
# Chose the 2025-03-05 version: in a side-by-side test it found the same Kalshi PDF with ~40%
# fewer tokens than the newer version (12.6k vs 20.1k), and no hidden code execution.
# NOT available on Bedrock (Anthropic's docs list Bedrock as "Not available"), so si_agent.py only
# adds it when PROVIDER=anthropic.
ANTHROPIC_WEB_SEARCH = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


# Tool 3: search_web. Our OWN tool (a client tool, like read_document) for when we're on Bedrock.
# Python sends the query to AWS's Web Search through our AgentCore Gateway and returns the raw
# results list (title, link, snippet, date). No second model in between, so nothing gets filtered.
# si_agent.py only adds it when PROVIDER=bedrock AND AGENTCORE_GATEWAY_URL is set.
SEARCH_WEB_TOOL = {
    "name": "search_web",
    "description": (
        "Search the web. Returns up to 10 results, each with a title, URL, short snippet and date. "
        "Use it to FIND primary documents (then read them with read_document) and independent "
        "sources (regulators, courts, reporters). Snippets are not the document: read before you "
        "quote. Put 'pdf' or a site name in the query to find source documents. Optionally limit "
        "results to certain sites (e.g. ['cftc.gov', 'sec.gov']) to get primary sources."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for (200 characters max)."},
            "only_sites": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional: only return results from these domains.",
            },
        },
        "required": ["query"],
    },
}
SEARCH_TOOL_NAME = "web-search-tool___WebSearch"  # gateway names tools "<target>___<tool>"


def search_web(query: str, only_sites: list | None = None) -> str:
    """Call the AgentCore Gateway (an MCP server) with one signed JSON-RPC 'tools/call' request."""
    import json, os
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    url = os.environ.get("AGENTCORE_GATEWAY_URL", "")
    if not url:
        return "[search unavailable: AGENTCORE_GATEWAY_URL is not set]"
    args = {"query": query[:200], "maxResults": 10}
    if only_sites:
        args["filters"] = {"domainFilter": {"include": list(only_sites)[:100]}}
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": SEARCH_TOOL_NAME, "arguments": args}})

    # SigV4 = AWS's way of proving who's calling: it signs the request with your AWS credentials
    # (the ones set in your terminal). The gateway checks the signature, not a password.
    creds = boto3.Session().get_credentials()
    req = AWSRequest(method="POST", url=url, data=body,
                     headers={"Content-Type": "application/json",
                              "Accept": "application/json, text/event-stream"})
    SigV4Auth(creds, "bedrock-agentcore", "us-east-1").add_auth(req)
    r = httpx.post(url, content=body, headers=dict(req.headers), timeout=30)
    r.raise_for_status()

    # The reply is JSON, or the same JSON wrapped as a "server-sent event" (lines starting 'data:').
    raw = r.text
    if raw.lstrip().startswith("event:") or raw.lstrip().startswith("data:"):
        raw = next(l[5:].strip() for l in raw.splitlines() if l.startswith("data:"))
    msg = json.loads(raw)
    if "error" in msg:
        return f"[search failed: {msg['error'].get('message', msg['error'])}]"
    result = msg.get("result", {})
    text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
    if result.get("isError"):
        return f"[search failed: {text[:500]}]"

    # Turn the results JSON into a short numbered list the model can scan.
    try:
        items = json.loads(text).get("results", [])
    except ValueError:
        return text[:6000]
    if not items:
        return f"[no results for: {query}]"
    lines = [f"[search results for: {query}]"]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it.get('title', '(no title)')}\n   {it.get('url', '')}"
                     f"{'  (' + it['publishedDate'] + ')' if it.get('publishedDate') else ''}\n"
                     f"   {it.get('text', '')[:400]}")
    lines.append("[AWS terms: show the source link for any result you use.]")
    return "\n".join(lines)


# --- 2. Helpers that turn raw bytes into plain text --------------------------
class _TextExtractor(HTMLParser):
    """Keep visible text from a web page; skip scripts, styles, and navigation clutter."""
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header"}

    def __init__(self):
        super().__init__()
        self.parts, self._skip_depth = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())


def _html_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    return "\n".join(p.parts)


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader  # pip install pypdf
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(f"[page {i}]\n{p}" for i, p in enumerate(pages, 1))
    # A scanned PDF holds PICTURES of letters, not characters, so almost no text comes out.
    real_chars = sum(len(p.strip()) for p in pages)
    if pages and real_chars < 100 * len(pages):
        text += ("\n[note: very little text came out of this PDF. It may be a scanned image (pictures "
                 "of pages, not text), which this tool can't read. Tell the person, and ask them to "
                 "paste the key passages or find a text version.]")
    return text


def _fetch_url(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (SI agent; reading public documents)"}
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as c:
        r = c.get(url)
        r.raise_for_status()
        if len(r.content) > MAX_DOWNLOAD:
            raise ValueError("document is larger than the 20 MB safety limit")
        ctype = r.headers.get("content-type", "").lower()
        if "pdf" in ctype or url.lower().split("?")[0].endswith(".pdf"):
            return _pdf_text(r.content)
        if "html" in ctype:
            text = _html_text(r.text)
            if len(text) < SHELL_THRESHOLD:
                # Most likely the page builds its content with JavaScript after it opens,
                # and we only got the empty frame. Say so plainly, so the model looks elsewhere.
                text += ("\n[note: very little text came back. This page probably builds its "
                         "content with JavaScript, so this is an empty shell, not the document. "
                         "Look for a PDF version (the company's document links, or a copy filed "
                         "with a regulator), or ask the person for a direct link.]")
            return text
        return r.text


def _read_local(name: str) -> str:
    import os
    # Public web version: no local files at all (visitors must not read files on the server).
    if os.environ.get("SI_WEB_MODE") == "1":
        raise ValueError("this version can only read web links (https://...), not files")
    # Only allow files INSIDE agent/docs — the model can't wander around your disk.
    path = (DOCS_DIR / name).resolve()
    if DOCS_DIR.resolve() not in path.parents:
        raise ValueError("can only read files inside the agent/docs folder")
    if not path.exists():
        available = ", ".join(p.name for p in DOCS_DIR.glob("*")) or "(folder is empty)"
        raise FileNotFoundError(f"no file named '{name}' in docs. Available: {available}")
    if path.suffix.lower() == ".pdf":
        return _pdf_text(path.read_bytes())
    return path.read_text(encoding="utf-8", errors="replace")


# --- 3. The FUNCTION we run when the model asks ------------------------------
FIND_CONTEXT = 700      # characters kept on each side of a match
FIND_MAX_PASSAGES = 8   # cap, so a common word can't return half the document
FIND_MAX_CHARS = 12000  # total cap on what one find call returns
FIND_MAX_PASSAGE = 3000 # cap on ONE passage (many nearby matches merge into one window)


def _page_at(text: str, pos: int) -> str:
    """Which [page N] marker comes before this position (PDFs only)."""
    i = text.rfind("[page ", 0, pos + 12)  # +12 so a marker right at the window start counts
    if i == -1:
        return ""
    return text[i + 1 : text.find("]", i)]  # e.g. "page 41"


def _find_passages(source: str, text: str, terms: list) -> str:
    """SEARCH INSIDE the document: return only the passages containing the terms.
    Plain text matching in Python, so the same terms always give the same passages."""
    # BUG FIX (found by the fact checker test): the model sometimes sends ONE phrase as a string, not a
    # list. Looping over a string goes letter by letter; single letters match everywhere, and the whole
    # 205,000-character rulebook came back as one "passage" (~218,000 tokens, ~$0.45).
    if isinstance(terms, str):
        terms = [terms]
    terms = [str(t) for t in terms if len(str(t).strip()) >= 3][:10]   # ignore 1-2 letter "terms"
    if not terms:
        return f"[source: {source} | give find a list of words or phrases of 3+ letters]"
    low = text.lower()
    hits = []  # (position, term)
    for term in terms:
        t = str(term).lower().strip()
        pos = low.find(t)
        while pos != -1:
            hits.append((pos, term))
            pos = low.find(t, pos + 1)
    if not hits:
        return (f"[source: {source} | {len(text)} characters | no passages found for: "
                f"{', '.join(map(str, terms))}. Try other wording or synonyms, or read by chunk "
                f"with start=0.]")

    # Turn each hit into a window of text around it, and merge windows that overlap.
    hits.sort()
    windows = []  # [start, end, set of terms]
    for pos, term in hits:
        s, e = max(0, pos - FIND_CONTEXT), min(len(text), pos + FIND_CONTEXT)
        if windows and s <= windows[-1][1]:
            windows[-1][1] = max(windows[-1][1], e)
            windows[-1][2].add(term)
        else:
            windows.append([s, e, {term}])

    out, used = [], 0
    for s, e, found in windows[:FIND_MAX_PASSAGES]:
        if used >= FIND_MAX_CHARS:
            break
        # Some PDFs come out one word per line; join into normal sentences (easier to quote, fewer chars).
        passage = " ".join(text[s:e].split())
        # Hard caps: one passage can't exceed FIND_MAX_PASSAGE, the total can't exceed FIND_MAX_CHARS.
        passage = passage[:min(FIND_MAX_PASSAGE, FIND_MAX_CHARS - used)]
        page = _page_at(text, s) or "no page markers"
        out.append(f"--- passage at position {s} ({page}) | matches: {', '.join(sorted(map(str, found)))}\n"
                   f"{passage}")
        used += len(passage)
    more = len(windows) - len(out)
    tail = (f"\n[{more} more passage(s) not shown. Narrow the terms to see them.]" if more > 0
            else "\n[all matching passages shown]")
    return (f"[source: {source} | {len(text)} characters | {len(windows)} passage(s) found for: "
            f"{', '.join(map(str, terms))}]\n" + "\n\n".join(out) + tail)


def read_document(source: str, start: int = 0, find: list | None = None) -> str:
    text = _DOC_COPIES.get(source)
    if text is None:
        text = (_fetch_url(source) if source.startswith(("http://", "https://"))
                else _read_local(source))
        _DOC_COPIES[source] = text
    if find:
        return _find_passages(source, text, find)
    total = len(text)
    start = max(0, int(start or 0))
    chunk = text[start : start + MAX_CHARS]
    end = start + len(chunk)
    note = (f"\n[more remains: call read_document again with start={end}]"
            if end < total else "\n[end of document]")
    return f"[source: {source} | characters {start}-{end} of {total}]\n{chunk}{note}"


def lookup(source: str, find: list | None = None, start: int = 0) -> str:
    """For the fact checker: like read_document, but ONLY documents already read this run (no web
    access, no new downloads), so it checks the main agent's sources instead of hunting for new ones."""
    if source not in _DOC_COPIES:
        return f"[not available: '{source}' wasn't read this run. Available: {', '.join(_DOC_COPIES)}]"
    return read_document(source, start, find)


def run_tool(name: str, args: dict) -> str:
    """Run whichever tool the model asked for. Errors go back to the model as text,
    so it can tell the user plainly instead of the program crashing."""
    try:
        if name == "read_document":
            return read_document(args.get("source", ""), args.get("start", 0), args.get("find"))
        if name == "search_web":
            return search_web(args.get("query", ""), args.get("only_sites"))
        return f"[unknown tool: {name}]"
    except Exception as e:
        return f"[{name} failed: {type(e).__name__}: {e}]"


# Quick test without running the agent:  python agent/tools.py "kalshi member agreement pdf"
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    print(search_web(" ".join(sys.argv[1:]) or "kalshi member agreement pdf"))
