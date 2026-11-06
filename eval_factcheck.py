"""
How accurate is the fact checker? A test with known answers.

Two kinds of error matter, and they do different harm:
  - FALSE ALARM: flags a TRUE claim as a problem -> the reader distrusts a real fact.
  - MISS: passes a WRONG claim -> a wrong fact goes through looking checked (worse than no checker).
This script plants claims whose right answer we know (from the real Kalshi documents), runs the
checker, and counts both. It also checks upgrades: unconfirmed claims the documents DO support should
become [VERIFIED]; opinions must not.

Run:  python agent/eval_factcheck.py                          (the writer's model)
      python agent/eval_factcheck.py claude-haiku-5-5 2        (a model, and how many repeats)
Costs a few cents per repeat. Results vary run to run, so repeat 2-3 times before trusting a number.
"""
import sys
import si_agent as s
from tools import read_document, document_texts
from factcheck import fact_check, apply_fact_marks, apply_upgrades

HARD_ONLY = "--hard" in sys.argv
if HARD_ONLY:
    sys.argv.remove("--hard")
AGREEMENT = "https://kalshi-public-docs.s3.amazonaws.com/kalshi-member-agreement.pdf"
RULEBOOK = "https://www.cftc.gov/sites/default/files/filings/orgrules/25/07/rules07012525155.pdf"

# (expected, line). expected: "ok" = true, must NOT be flagged; "flag" = must be flagged;
# "upgrade" = unconfirmed but the documents support it; "leave" = opinion: no flag, no upgrade.
REPLY_A = [  # sourced claims (what the checker judges)
    ("ok",   '- The clearing house keeps investment profit it doesn\'t pay out. [VERIFIED: Kalshi Rulebook, Rule 8.1(c)] "Clearing House will retain all profit from investment of Participant funds not paid to Members."'),
    ("ok",   '- You have two years to start arbitration. [VERIFIED: Kalshi Rulebook, Rule 10.2(a)] "within two years from the time the Claim arose"'),
    ("ok",   '- Outcome Review Committee decisions are final. [VERIFIED: Kalshi Rulebook, Rule 7.1(c)] "The determinations made by the Outcome Review Committee are final."'),
    ("ok",   '- If the agreement and the Rulebook conflict, the Rulebook wins. [VERIFIED: Member Agreement, Section V.B] "In the event of any conflict between this Agreement and the Kalshi Rulebook, the Kalshi Rulebook will govern."'),
    ("ok",   '- Kalshi\'s trading affiliate must not have access to inside information on order flow. [VERIFIED: Kalshi Rulebook, Rule 2.12(b)] "Not have access to material non-public information"'),
    ("ok",   '- Kalshi convenes the arbitration panel. [VERIFIED: Kalshi Rulebook, Rule 10.2(c)] "Kalshi shall promptly convene an arbitration panel."'),
    ("flag", '- Kalshi can freeze your withdrawals at any time, for any reason. [VERIFIED: Kalshi Rulebook, Rule 6.4(a)] "may be suspended or denied"'),
    ("flag", '- The arbitration fee is $250 for claims under $5,000. [VERIFIED: Kalshi Rulebook, Rule 10.2(b)]'),
    ("flag", '- Market makers get position allowances 5 times higher than everyone else. [VERIFIED: Kalshi Rulebook, Rule 4.5(a)]'),
    ("flag", '- Kalshi must pay you interest on your cash balance. [VERIFIED: Kalshi Rulebook, Rule 8.1(b)]'),
    ("flag", '- The Rulebook guarantees refunds within 24 hours when an outcome is wrong. [VERIFIED: Kalshi Rulebook, Rule 7.3]'),
    ("flag", '- Kalshi\'s affiliate is banned from trading on the exchange. [VERIFIED: Member Agreement, Section VII.C]'),
]
REPLY_B = [  # math, untagged facts, and unconfirmed claims (upgrades and opinions)
    ("flag",    "- A $1.75 fee on a $50 purchase is 7% of what you pay. [UNVERIFIED: my arithmetic]"),
    ("flag",    "- You can always sue Kalshi in small claims court instead of arbitrating."),
    ("upgrade", "- Disputes go to an arbitration panel that Kalshi itself convenes. [CHECK: snippet only]"),
    ("upgrade", "- When the agreement and the rulebook disagree, the rulebook wins. [CHECK: secondary site]"),
    ("leave",   "- This setup gives Kalshi a reason to discourage disputes. [UNVERIFIED: my inference]"),
    ("ok",      "- Kalshi is a US company that runs a prediction market. [UNVERIFIED: general knowledge]"),
]


REPLY_C = [  # HARD: subtle stretches, dropped conditions, scope errors, and true-but-surprising claims
    # Answer-key lesson: these two were first written as "ok" WITHOUT their conditions, and the checker
    # flagged them correctly. The accurate versions are "ok"; the overstated versions are now "flag".
    ("ok",   "- If a contract's data source becomes unreliable or unavailable, Kalshi can name a new source and change the contract's specifications, even after trading has started. [VERIFIED: Kalshi Rulebook, Rule 7.2(a)]"),
    ("ok",   "- Unless otherwise specified, market makers with quoting obligations get position accountability levels 10 times those of other traders on those contracts. [VERIFIED: Kalshi Rulebook, Rule 4.5(a)]"),
    ("flag", '- Kalshi can change a contract\'s specifications after trading has started. [VERIFIED: Kalshi Rulebook, Rule 7.2(a)] "change any associated contract specifications after the first day of trading"'),
    ("flag", "- Market makers can hold positions up to 10 times larger than other traders. [VERIFIED: Kalshi Rulebook, Rule 4.5(a)]"),
    ("ok",   "- Kalshi's liability is capped at the lesser of what you paid for the assets in the claim or what you deposited. [VERIFIED: Member Agreement, liability section]"),
    ("ok",   "- Kalshi can hold a withdrawal when the funds are relevant to a pending investigation. [VERIFIED: Kalshi Rulebook, Rule 6.4(a)]"),
    ("flag", "- Arbitration costs $500 to file. [VERIFIED: Kalshi Rulebook, Rule 10.2(b)]"),
    ("flag", "- Kalshi starts an outcome review whenever a trader asks for one. [VERIFIED: Kalshi Rulebook, Rule 7.1(a)]"),
    ("flag", "- Kalshi can hold a withdrawal only when there is a pending investigation. [VERIFIED: Kalshi Rulebook, Rule 6.4(a)]"),
    ("flag", "- Kalshi's liability to you is capped at the total funds you have deposited. [VERIFIED: Member Agreement, liability section]"),
    ("flag", "- Kalshi will pay interest on any balance you leave in your account. [VERIFIED: Kalshi Rulebook, Rule 8.1(b)]"),
]


def score(model: str, block: list) -> dict:
    reply = "## Key points\n" + "\n".join(line for _, line in block)
    r = fact_check(s.make_client(), model, reply)
    marked, unplaced = apply_fact_marks(reply, r)
    upgraded, done = apply_upgrades(reply, r, document_texts())
    m_lines, u_lines = marked.splitlines()[1:], upgraded.splitlines()[1:]
    out = {"caught": 0, "should_flag": 0, "false_alarm": 0, "should_pass": 0, "upgraded": 0,
           "should_upgrade": 0, "wrong_upgrade": 0, "unplaced": len(unplaced), "cost": s.turn_cost(r["usage"]) or 0,
           "error": r["error"], "misses": [], "alarms": []}
    for (exp, line), ml, ul in zip(block, m_lines, u_lines):
        flagged, up = ml != line, ul != line   # flagged = the checker changed or added a label on this line
        if exp == "flag":
            out["should_flag"] += 1
            out["caught"] += flagged
            if not flagged:
                out["misses"].append(line[2:70])
        elif exp in ("ok", "leave"):
            out["should_pass"] += 1
            if flagged:
                out["false_alarm"] += 1
                out["alarms"].append(line[2:70])
            if up and exp == "leave":
                out["wrong_upgrade"] += 1
        elif exp == "upgrade":
            out["should_upgrade"] += 1
            out["upgraded"] += up
    return out


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else s.MODEL
    repeats = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    read_document(AGREEMENT)
    read_document(RULEBOOK)
    total = {}
    for i in range(repeats):
        blocks = (("C (hard)", REPLY_C),) if HARD_ONLY else (("A", REPLY_A), ("B", REPLY_B), ("C (hard)", REPLY_C))
        for name, block in blocks:
            r = score(model, block)
            if r["error"]:
                print(f"  repeat {i + 1}, reply {name}: checker error: {r['error'][:150]}")
            for k, v in r.items():
                if isinstance(v, (int, float)):
                    total[k] = total.get(k, 0) + v
            for m in r["misses"]:
                print(f"  repeat {i + 1}: MISSED      {m}")
            for a in r["alarms"]:
                print(f"  repeat {i + 1}: FALSE ALARM {a}")
    t = total
    print(f"\nModel: {model} · {repeats} repeat(s)")
    print(f"  Caught errors:   {t['caught']} of {t['should_flag']}  (misses: {t['should_flag'] - t['caught']})")
    print(f"  False alarms:    {t['false_alarm']} of {t['should_pass']} true claims flagged")
    print(f"  Upgrades:        {t['upgraded']} of {t['should_upgrade']} supported claims upgraded; "
          f"{t['wrong_upgrade']} opinion(s) wrongly upgraded")
    print(f"  Couldn't place:  {t['unplaced']} flag(s) that didn't match a line (not counted above)")
    print(f"  Cost:            ≈ ${t['cost']:.2f} total, priced at the .env (writer's) rates; a cheaper "
          f"model costs proportionally less")


if __name__ == "__main__":
    main()
