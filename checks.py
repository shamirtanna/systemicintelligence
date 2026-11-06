"""
Source checks: code verifying the model's labels, after each reply.

The model tags its own claims. Nothing stopped it from tagging a paraphrase, a search snippet, or a
misremembered sentence as [VERIFIED]. Here Python compares every quote on a [VERIFIED] line against
the full text of the documents read this run (which tools.py already keeps in memory). Deterministic:
same reply + same documents = same result. No model involved.

It also keeps a LEDGER for the run: every verified quote (found or not), every [CHECK] item and every
[UNVERIFIED] item, written to a "sources" file next to the transcript.
"""
import re
from pathlib import Path

QUOTE = re.compile(r'[“"]([^“”"\n]{12,800})[”"]')         # text inside straight or curly quotes
SPLIT = re.compile(r"\s*(?:…|\.\.\.|\[[^\]]*\])\s*")        # "..." and [inserted words] break a quote into parts
VERIFIED_TAG = re.compile(r"\[VERIFIED:\s*([^\]]+)\]", re.I)  # needs a source after the colon
ALREADY_ASKED: set = set()   # quotes we've already asked the model to fix (ask once, not every turn)
MIN_WORDS = 4                                               # parts shorter than this are too short to test
PAGE_MARK = re.compile(r"\[page \d+\]")
ANY_TAG = re.compile(r"\[(?:VERIFIED|CHECK|UNVERIFIED)[^\]]*\]", re.I)


def _norm(s: str) -> str:
    """Lowercase, letters and digits only, single spaces. Survives PDF line breaks, hyphens, curly quotes."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _plain(line: str) -> str:
    """A ledger line without markdown clutter."""
    return re.sub(r"[*_`>#]+", "", line).strip(" -•\t")[:400]


CORRECTIONS_HEAD = re.compile(r"^\W*corrections?\b", re.I)


def correction_lines(lines: list) -> set:
    """Line numbers inside a 'Corrections' block (from its heading to the next heading or blank+heading).
    These discuss earlier claims; checking them made corrections of corrections in the MRI run."""
    out, inside = set(), False
    for i, l in enumerate(lines):
        s = l.strip()
        if CORRECTIONS_HEAD.match(s):
            inside = True                       # the "**Corrections:**" heading itself
        elif inside and s and not s.startswith(("-", "*  ", "  ")) and not l.startswith((" ", "\t")):
            inside = False                      # first line that isn't a list item ends the block
        if inside:
            out.add(i)
    return out


def check_quotes(reply: str, documents: dict) -> list:
    """Return one result per quote on a [VERIFIED] line: {quote, source, found}."""
    # Our own [page N] markers can land mid-sentence in PDF text; remove them before comparing.
    corpus = [_norm(PAGE_MARK.sub(" ", t)) for t in documents.values()]
    lines = reply.splitlines()
    results, seen = [], set()
    skip = correction_lines(lines)
    for i, line in enumerate(lines):
        if i in skip:   # the writer talking ABOUT earlier claims isn't a new claim (it looped in the MRI run)
            continue
        # Only real tags count: "[VERIFIED: source]". A bare mention like "it shouldn't have had a
        # [VERIFIED] tag" (in a correction) isn't a claim; counting it made corrections loop in run 4.
        if not VERIFIED_TAG.search(line):
            continue
        # Remove the tags themselves first: a quote mark inside a tag (e.g. 'item "I."') would
        # otherwise pair up with a real quote mark and produce a nonsense "quote".
        body = ANY_TAG.sub(" ", line)
        quotes = QUOTE.findall(body)
        # Some models put the quote INSIDE the tag: [VERIFIED: DOL booklet, p. 6: "you have at least..."].
        # Check those too (Haiku did this, and its quotes went unchecked).
        for t in VERIFIED_TAG.finditer(line):
            quotes += QUOTE.findall(t.group(1))
        if not quotes and i > 0 and lines[i - 1].lstrip().startswith(">"):
            quotes = QUOTE.findall(ANY_TAG.sub(" ", lines[i - 1]))  # block quote just above the tag
        tag = VERIFIED_TAG.search(line)
        source = QUOTE.sub("", tag.group(1)).strip(" :,;") if tag else ""   # source name, without the quote
        for q in quotes:
            key = _norm(q)
            if key in seen:
                continue
            seen.add(key)
            parts = [_norm(p) for p in SPLIT.split(q)]
            parts = [p for p in parts if len(p.split()) >= MIN_WORDS]
            if not parts:
                continue                                    # e.g. a one-word quote: nothing useful to test
            found = any(all(p in doc for p in parts) for doc in corpus)
            results.append({"quote": q.strip(), "source": source, "found": found, "line": i})
    return results


def apply_quote_labels(reply: str, results: list) -> str:
    """Audited labels: on each line whose quote wasn't found, change the writer's [VERIFIED: x] to
    [CHECK: quote not found in x]. Code is certain about this, so it's safe to change what's shown."""
    lines = reply.splitlines()
    for r in results:
        if r["found"] or r.get("line") is None or r["line"] >= len(lines):
            continue
        lines[r["line"]] = VERIFIED_TAG.sub(
            lambda m: f"[CHECK: quote not found word for word in {m.group(1).strip()}]", lines[r["line"]], count=1)
    return "\n".join(lines)


def summary_line(results: list) -> str:
    """One line shown to the person after each reply (empty if there was nothing to check)."""
    if not results:
        return ""
    missing = [r for r in results if not r["found"]]
    line = (f"Quotes: {len(results) - len(missing)} of {len(results)} found word for word in the documents "
            f"(checked by code)" + (", the rest changed to [CHECK]." if missing else "."))
    for r in missing[:3]:
        line += f'\n   - Not found: "{r["quote"][:160]}"'
    if len(missing) > 3:
        line += f"\n   ...and {len(missing) - 3} more (see the sources list)."
    return line


def fix_request(results: list) -> str:
    """Sent to the model (in the reminder) so it corrects quotes that weren't found."""
    missing = [r for r in results if not r["found"] and _norm(r["quote"]) not in ALREADY_ASKED]
    if not missing:
        return ""
    ALREADY_ASKED.update(_norm(r["quote"]) for r in missing)
    listed = "; ".join(f'"{r["quote"][:150]}"' for r in missing[:5])
    return (" Source check by code: these quotes tagged [VERIFIED] were NOT found word for word in any "
            f"document read this run: {listed}. Their tags were already changed to [CHECK] for the reader. "
            "Use real quotes from now on; don't list these as corrections unless one changes a finding. "
            "Never put your own wording in quotation marks. Don't withdraw quotes that weren't listed "
            "here: code found those word for word.")


class Ledger:
    """Everything the run claimed, by label. Written to <transcript>-sources.md after every turn."""

    def __init__(self):
        self.verified, self.check, self.unverified, self._seen = [], [], [], set()
        self.fact_problems = []   # from the fact checker (factcheck.py)

    def add_fact_problems(self, problems: list):
        self.fact_problems.extend(problems)

    def add_confirm(self, items: list):
        self.confirm_first = getattr(self, "confirm_first", []) + items

    def add_skeptic(self, items: list):
        self.skeptic = getattr(self, "skeptic", []) + items

    def add(self, reply: str, quote_results: list):
        for r in quote_results:
            k = ("v", _norm(r["quote"]))
            if k not in self._seen:
                self._seen.add(k)
                self.verified.append(r)
        for line in reply.splitlines():
            up = line.upper()
            for label, bucket in (("[CHECK", self.check), ("[UNVERIFIED", self.unverified)):
                if label in up:
                    k = (label, _norm(line))
                    if k not in self._seen:
                        self._seen.add(k)
                        bucket.append(_plain(line))

    def write(self, path: Path, documents: list):
        path.write_text(self.text(documents), encoding="utf-8")

    def text(self, documents: list) -> str:
        """The sources list as text (the web version offers it as a download)."""
        found = [r for r in self.verified if r["found"]]
        missing = [r for r in self.verified if not r["found"]]
        out = ["# Sources for this run", "",
               "## Verified: quoted, and the quote was found in the document text by code", ""]
        out += [f'- "{r["quote"]}"  ({r["source"] or "no source given"})' for r in found] or ["- (none)"]
        out += ["", "## Tagged [VERIFIED] but NOT found word for word (treat as needs checking)", ""]
        out += [f'- "{r["quote"]}"  ({r["source"] or "no source given"})' for r in missing] or ["- (none)"]
        out += ["", "## Fact checker: claims that the source doesn't fully support", ""]
        out += [f"- {p['verdict']}: {p['claim']} | source says: {p['source_says']} | fix: {p['fix']}"
                for p in self.fact_problems] or ["- (none found)"]
        out += ["", "## Confirm these first (the fact checker's top unconfirmed claims, by phase)", ""]
        out += [f"- {c['claim']} | why: {c['why']} | confirm: {c['how']}"
                for c in getattr(self, "confirm_first", [])] or ["- (none)"]
        out += ["", "## Skeptic review (argument level: what's strong, weak, missing, the other side)", ""]
        out += [f"- {i['kind']}: " + " | ".join(i["parts"]) for i in getattr(self, "skeptic", [])] or ["- (not run yet)"]
        out += ["", "## Needs checking", "", "### [CHECK]: plausible; the tag says what to confirm and where", ""]
        out += [f"- {c}" for c in self.check] or ["- (none)"]
        out += ["", "### [UNVERIFIED]: not checked against any source", ""]
        out += [f"- {u}" for u in self.unverified] or ["- (none)"]
        out += ["", "## Documents and pages read this run", ""]
        out += [f"- {d}" for d in documents] or ["- (none)"]
        return "\n".join(out) + "\n"
