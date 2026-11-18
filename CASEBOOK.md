# Accountability Casebook

> **About this file.** Real cases where people were taken advantage of, how each was found, and what changed. It is the background for the sparks the agent uses (see `CASEBOOK-SPARKS.md`). Cases are compiled from news reports, regulator releases and court filings, which are listed under each case. They were not independently re-verified by the author, so check the sources before relying on a detail. Allegations are attributed and denials are noted where known. Some cases are ongoing. This is background for questions to ask, not proof that the same thing happened elsewhere.

A growing collection of cases where something systemically wrong was surfaced and acted on —
documenting HOW each one came about, and the cross-domain connections between them.

Purpose: a standalone reference. Each entry = a real case + the investigative "move" that cracked
it + where that move could travel. Over time the collection reveals which techniques are PORTABLE
across domains. Useful on its own (reference / content / corpus) independent of any product.

## THE PIPELINE (the meta-move — domain-independent)
How harm actually goes from "feeling" to "action." The DoorDash case ran this exactly.
1. ANECDOTES — individuals notice something off ("my pay doesn't change when I'm tipped"). Scattered, individually dismissible.
2. PUBLIC DATA + PATTERN — aggregate the anecdotes, cross-check vs. what's publicly knowable (published pay model, advertised guarantee). Now a HYPOTHESIS, not a feeling.
3. HANDOFF TO AN ENFORCER WITH SUBPOENA POWER — regulator pulls the INTERNAL records no outsider can, turning hypothesis into proof. (DoorDash: public model raised flags 2019 -> NY AG subpoenaed internal ledgers -> $16.75M.)

CAVEAT: not every case runs all 3 (Kawhi/Meta = journalist+public docs, no subpoena needed; EY = whistleblower insider start). The pipeline is the IDEAL path when proof lives in internal records.

## CASE TEMPLATE
```
### CASE N — <short title>  [status: settled | ongoing | exposed-no-action]  (sources below)
- Domain(s):
- Who caught it: [journalist | regulator | whistleblower | academic/analyst | worker | class-action | community]
- Trigger (first signal):
- THE MOVE (how it surfaced):
- Escalation (signal -> action):
- Outcome / penalty:
- Ordinary-person accessibility: [public-record / insider-only / data-skill / etc.]
- Cross-domain reach (where this move could travel):
- WHO BENEFITS / WHO IT APPLIES TO (the affected group + their action):
- Primary source(s):
```

---

## TWO PARALLEL ENGINES (both cross-domain)
This casebook now tracks TWO kinds of portable, cross-domain pattern:
1. DETECTION MOVES — how wrongdoing gets FOUND (the MOVE INDEX below). Hard-sourced from real cases.
2. ADVOCACY MOVES — how change gets WON, transferable across domains (the ADVOCACY-MOVE NOTES below).
   SOFTER: advocacy history is messy, can't be rigorously sourced -> treat as [UNVERIFIED/spark] to prompt
   the human's own knowledge, NOT as proven playbook. Keep separate from the hard detection moves.

## ACTION + ADVOCACY MOVE NOTES (tentative; sparks, not sourced playbook) [UNVERIFIED/spark]
Cross-domain transfer applies to BOTH personal-protection actions AND advocacy tactics (softer than
detection moves — can't be rigorously sourced; frame as sparks for the human's knowledge).
ADVOCACY:
- A1 "FIND THE MOST AGGRESSIVE ENFORCER WITH JURISDICTION, not just the obvious one." From DoorDash: NYC
  DCWP escalated the remedy ~8x over the NY state AG. Transfers to any domain with overlapping enforcers.
- A2 "DEMAND PUBLIC DISCLOSURE / REGISTERS where secrecy enabled the harm." From Abramovich: public
  beneficial-ownership registers. Transfers to any secrecy-jurisdiction / opacity problem (incl. Kalshi
  "disclose how often discretion is used").
PERSONAL ACTION:
- P1 "DON'T LEAVE IDLE BALANCES; move to an insured/real account." From banking, applied to Kalshi
  (uninsured + withdrawals deniable). Transfers to any uninsured-custodian situation.
- P2 "GET IT IN WRITING BEFORE YOU SIGN / COMMIT." Generic defensive move; transfers broadly.
(Add A3+/P3+ as approaches recur. Always tag [UNVERIFIED/spark].)

## MOVE INDEX (the portable-technique catalog)
Tally of which investigative moves recur across cases. The higher the count / the more domains, the
more portable (and more cross-domain-valuable) the technique.

- M1 SHELL-ENTITY DECODE — names in public filings encode the real beneficiary; same-named entities across
  jurisdictions hide ownership.
  Cases: Kawhi (KL2 Aspire LLC), Meta (Laidley LLC), Abramovich (twin "Electus Investments" Cyprus vs BVI).
  Domains: sports, tax/politics, offshore wealth. [3] — now the most-recurring move.
- M2 PER-ORDER/UNIT DECOMPOSITION of the target's own records — break the headline number into its parts and watch how the parts move against each other (DoorDash: as tip rose, company share fell, worker total flat). Often needs the target's INTERNAL data = subpoena power.
  Cases: DoorDash (tip vs base vs guarantee). Domains: gig/labor. [1] (Dieselgate = external-test variant)
- M3 CROSS-REFERENCE TWO PUBLIC DATASETS -> conflict of interest.
  Cases: Meta (land deeds x legislative votes). Domains: politics/housing. [1]
- M4 COVER-UP AS LEVERAGE — lying to investigators is a cleaner/bigger charge than the act.
  Cases: EY (misled SEC). Domains: audit/corporate. [1]
- M5 FOLLOW THE COUNTERPARTY/CREDITOR LIST — who is owed money reveals the hidden deal.
  Cases: Kawhi (Aspiration creditors). Domains: sports/finance. [1]

- M6 WHO-FUNDS-THE-WATCHDOG — the "regulator"/rater/certifier is financed or run by the very parties it judges.
  CASE: LBMA (Case 6) — the gold industry's "global authority" is financed + run by its biggest refiners +
  banks (HSBC, Morgan Stanley, JPM, Deutsche Bank). [1 full case + recurs in:] finance (advisor conflicts),
  prediction-market affiliate trackers, nonprofit raters (Charity Navigator/Candid/Give.org). Now a FULL move.
- M9 PUBLIC-vs-PRIVATE STATEMENT CONTRADICTION — compare what a body claims in PUBLIC (marketing, website,
  press) against what it says in COURT FILINGS / under oath / to regulators. The gap exposes the real story.
  CASE: LBMA (Case 6) — public "global standard-setter, 85-90% of gold" vs. court "a small not-for-profit...
  does not possess the staff/expertise/resources" (and DENIES the standard-setter claim). Transfers anywhere a
  body makes bold public claims but hedges its legal exposure. Ordinary-person accessible (both are public record).
- M7 DATA-RIGHTS / WHO-REALLY-GETS-YOUR-DATA — surface the clause/practice where a platform claims broad or
  perpetual rights to user data, then trace the consequences when exposed. NOW A FULL MOVE: Kalshi Member
  Agreement data license (perpetual/sublicensable/assignable, PDF-VERIFIED) + Meta/Cambridge Analytica (Case 8)
  = the consequence-when-exposed case ($25B NM verdict). Portable to: 23andMe (genetic data in bankruptcy),
  data-broker ToS. Lesson: data-rights harm is invisible to the user but CAN carry huge penalties once surfaced.

- M8 BACKDATING-TO-REWRITE-HISTORY — detect by cross-checking TRANSACTION DATES against when a law,
  threshold, or disclosure requirement changed; backdated transfers that conveniently predate a new rule.
  Cases: Abramovich/Deloitte (asset + ownership transfers backdated ~3 yrs to beat a 2006 transparency law). [1]
  Domains it travels to: tax, sanctions, securities, procurement — anywhere dated filings meet a rule change.

(Add moves M9+ as new ones appear: whistleblower-channel/bounty, academic road-test/field study, etc.)

---

## CASES

### CASE 1 — Pablo Torre / Kawhi Leonard / Clippers salary-cap circumvention  [status: settled]  (sources below; not independently re-verified)
- Domain(s): pro sports, salary cap, corporate sponsorship/fraud (Aspiration).
- Who caught it: JOURNALIST (Pablo Torre, "Pablo Torre Finds Out"). Regulator (NBA) acted after.
- Trigger (first signal): reviewing Aspiration's public BANKRUPTCY filings.
- THE MOVE (M5 + M1): followed the creditor list; spotted entity "KL2 Aspire LLC" and decoded it = Kawhi Leonard (KL = initials, 2 = jersey #).
- Escalation: Sept 3 2025 first episode reveals $28M/4yr no-show endorsement deal; 13+ part series; uncovered a 2nd hidden deal (Daktronics, Intuit Dome scoreboard maker) via on-tape sources. NBA hired a law firm; investigated.
- Outcome / penalty: NBA (Sept 2 2026) found Clippers helped Leonard get deals w/ 4 companies doing business w/ the team in exchange for business = cap violation. Clippers fined $30M + stripped 5 first-round picks; owner Steve Ballmer suspended 1 yr; Leonard fined $700K. (Among largest in US sports history.)
- Ordinary-person accessibility: PUBLIC RECORD (bankruptcy creditor list) + pattern recognition.
- Cross-domain reach: shell-entity decode -> finance (advisor affiliates), politics (dark-money LLCs), prediction markets (big accounts).
- WHO BENEFITS / WHO IT APPLIES TO: fans/leagues (competitive integrity); other players (cap fairness); ANYONE tracing hidden money through intermediaries (reporters, researchers). Action: read bankruptcy creditor lists; decode LLC names.
- Primary source(s): pablo.show; Fortune 2026-10-03; Variety; Bleacher Report; The Verge; Rolling Stone PH; NBA findings.

### CASE 2 — Meta AI data-center tax breaks (Louisiana "Hyperion")  [status: exposed-no-action]  (sources below; not independently re-verified)
- Domain(s): corporate tax subsidy, state/local politics, energy, self-dealing.
- Who caught it: LOCAL JOURNALIST (Jon Keegan, Sherwood News); then nonprofits (Floodlight, Verite, Louisiana Illuminator) + transparency group (Good Jobs First).
- Trigger (first signal): Richland Parish commissioners "quietly approved" billions in tax breaks (July 2024) for Delaware shell "Laidley LLC."
- THE MOVE (M1 + M3): decoded shell "Laidley LLC" = Meta; then cross-referenced public LAND DEEDS vs. a state senator's legislative VOTES.
- Escalation: Floodlight found state Sen. Jay Morris bought/sold land around the site over 15 months while co-sponsoring enabling bills + lobbying the utility regulator. Good Jobs First: >=14 states don't report data-center tax-abatement losses. NYT: Meta also labeled data centers "experimental" for federal R&D credits (own accountants flagged risk).
- Outcome / penalty: NONE yet — ongoing exposure. ~$3.3B in sales-tax exemptions (20 yrs).
- Ordinary-person accessibility: PUBLIC RECORD (parish approvals, LLC registration, land deeds). Built from local records, not leaks.
- Cross-domain reach: shell decode (universal); land-deeds x votes = conflict detection -> money-in-politics, housing, any official-benefits-from-own-vote case.
- WHO BENEFITS / WHO IT APPLIES TO: local taxpayers/ratepayers (who fund the breaks + power buildout); residents near any subsidized megaproject; watchdogs auditing officials' land holdings. Action: pull parish/county approval records, LLC filings, officials' property deeds; compare to their votes.
- Primary source(s): Sherwood News / Yahoo Finance; lailluminator.com (Floodlight); hoodline (Good Jobs First); qz/NYT.

### CASE 3 — DoorDash / Dashers tip-theft & underpayment  [status: settled (x2)]  (sources below; not independently re-verified)
- Domain(s): gig economy / labor / consumer deception.
- Who caught it: REGULATORS — NY State AG (Letitia James), then NYC DCWP (under Mayor Mamdani).
- Trigger (first signal): investigation into how guaranteed pay interacted with customer tips.
- THE MOVE (M2, refined): PER-ORDER DECOMPOSITION of the company's OWN pay records. The guarantee (e.g. $10) was funded by: tiny base (~$1) + customer tip filling the gap. Detection = watch the inverse relationship across orders: as customer TIP goes UP, DoorDash's CONTRIBUTION goes DOWN, worker TOTAL stays FLAT. Proof: example guarantee $10, tip $6 -> DoorDash pays $1 base + $6 tip + $3 topup = $10 (worker earns same as if tip were $0). The tip subsidized DOORDASH, not the Dasher.
  HOW THEY COMPARED THE NUMBERS: not two external datasets — it was decomposing DoorDash's INTERNAL per-delivery ledger (base vs tip vs total) against the advertised guarantee, showing the company's share shrank as tips rose. Required SUBPOENA power (NY AG) because the proof lived in internal records. (NY AG Assurance of Discontinuance; Verge; HR Morning; Axios 2019.)
- Escalation: NY AG settlement ~Feb 2025. Separately NYC DCWP investigation found underpaid/late/unpaid wages for 260,000+ workers.
- Outcome / penalty: (A) NY AG $16.75M + payment-practice reform/transparency. (B) NYC $131.5M (record) — >$115M to 260,000+ workers (some up to 3x missing pay / up to $5,000), ~$16M penalties, auto-distributed from Oct 2026.
- Ordinary-person accessibility: the harm = detectable structure (promised vs actual). Remedy = CLAIMABLE (AG urged workers to file; NYC auto-pays).
- Cross-domain reach: promised-vs-delivered -> gig pricing, prediction-market payout vs odds, finance fee-vs-return. Advocacy lesson: a sympathetic enforcer escalated the remedy ~8x.
- WHO BENEFITS / WHO IT APPLIES TO: gig/delivery workers (direct claimants — must FILE in NY-AG version, auto-paid in NYC version); customers who tip (deception); any worker on a platform with "guaranteed pay." Action: check eligibility + file claim; compare promised pay vs actual incl. tips.
- Primary source(s): ag.ny.gov; nyc.gov/mayors-office 2026-09; classaction.org; courthousenews; mayerbrown.

### CASE 4 — EY (Ernst & Young) ethics-exam cheating + cover-up  [status: settled]  (sources below; not independently re-verified)
- Domain(s): corporate audit / professional integrity / securities regulation.
- Who caught it: INTERNAL WHISTLEBLOWER -> SEC Enforcement.
- Trigger (first signal): whistleblower disclosure that EY audit pros cheated on CPA ETHICS exams + continuing-ed over years (49 pros / 5 yrs).
- THE MOVE (M4): the COVER-UP became leverage — EY told the SEC it had no current cheating issue when it had already been informed; misleading the investigation became its own charge.
- Escalation: SEC investigation; EY admitted facts.
- Outcome / penalty: June 28 2022 — $100M (LARGEST EVER vs an audit firm) + remedial measures + independent compliance consultant. Precedent: KPMG $50M (2019).
- Ordinary-person accessibility: INSIDER-ONLY entry (requires being inside); SEC whistleblower bounty program is the channel.
- Cross-domain reach: cover-up-as-leverage + whistleblower-channel-exists-and-pays -> any regulated industry where a probe can be misled.
- WHO BENEFITS / WHO IT APPLIES TO: investors relying on audited financials (integrity of the gatekeeper); employees who witness misconduct (SEC whistleblower bounty = financial upside to reporting). Action: use the SEC whistleblower program; document contemporaneously.
- Primary source(s): SEC press release 2022-114; Cleary Gottlieb; CNBC; The Hill; Globe & Mail; whistleblowersblog.

### CASE 5 — Deloitte / Abramovich — backdated docs to hide wealth + evade tax  [status: exposed/ongoing]  (sources below; not independently re-verified)
- Domain(s): offshore wealth, audit/professional-adviser integrity, tax evasion, sanctions.
- Who caught it: JOURNALISTS off a LEAK — BBC Panorama + Bureau of Investigative Journalism, via the "Cyprus Confidential" leak (thousands of docs on Abramovich's offshore network, 1995-2022).
- Trigger (first signal): a 2006 Cyprus transparency law forcing company accounts public threatened to expose ~$672m of luxury assets (mansions, jets, superyachts incl. $147.5m Pelorus) in Amiscan Investments.
- ORIGIN MECHANISM (distinct from the detection technique): LEAK-ENABLED INTERNAL-vs-PUBLIC DISCREPANCY CHECK. Reporters did NOT reverse-engineer this from public filings (unlike Kawhi/Meta). They got leaked INTERNAL MeritServus docs and compared them against the PUBLIC Cypriot accounts — the mismatch exposed the lie. The leak played the role the SUBPOENA played in DoorDash: it granted access to the internal truth. (Closer to DoorDash's internal-vs-stated move than to Kawhi's public-record shell-decode.)
- THE TECHNIQUES EXPOSED (what the falsification actually was): M1 same-name shells + M8 backdating. SAME-NAME SHELLS: used a 2nd company with the EXACT same name "Electus Investments" but in the BVI (accounts private) vs. the Cyprus one (accounts public after 2006). Backdated docs to make the BVI twin look like it owned the $10bn since Nov 2003, so the public Cyprus Electus appeared to hold just $145k. (Same-name across jurisdictions = concealment: paperwork referencing "Electus" is ambiguous about WHICH one; outsiders can't untangle the transfer.) M8 BACKDATING: changes backdated ~3 yrs to 2003 to predate the 2006 transparency law. Deloitte Cyprus reviewed the backdated docs, called them "adequate," signed off accounts it knew were misleading; also advised changing Kravin Investments' records so ~$2bn interest-earning cash looked owned by a BVI parent -> no Cyprus tax.
- Escalation: leak -> joint investigation -> on-record experts (Andrew Mitchell KC: "straightforward" tax evasion, "couldn't be more blatant"; Lord Sikka: "violation of a statutory duty"). Jersey: £5.4bn assets frozen, 4-yr criminal investigation ongoing. Abramovich denies; Deloitte Cyprus says it "acts in compliance." MeritServus (the Cyprus admin firm) closed after the leak.
- Outcome / penalty: NO penalty yet — exposed + under criminal investigation (Jersey). Deloitte reputational.
- Ordinary-person accessibility: INSIDER/LEAK-dependent to originate; but the TECHNIQUE (same-named shell in a secrecy jurisdiction + backdated transfer) is spottable in public filings once you know to look for date/ownership mismatches.
- Cross-domain reach: M1 shell-decode (universal); M8 backdating -> any accounts/filings where TRANSACTION DATES can be checked against when a law/threshold changed (tax, sanctions, securities, procurement). "Who-funds / who-really-owns" ties to money-in-politics + the Meta/Kawhi shell cases.
- WHO BENEFITS / WHO IT APPLIES TO: tax authorities + the public (evaded tax = public money); sanctions enforcers; journalists tracing oligarch/elite wealth. Reinforces the NONPROFIT/foundation finding (rich individuals + the ADVISER ARMY that whitewashes them — Milov quote). Action: cross-check transaction DATES vs. when a disclosure law/threshold changed; flag same-named entities across jurisdictions.
- ADVOCACY (why a LEAK was even needed = the advocacy target): the scheme worked by moving the fortune to the BVI, which DELIBERATELY provides corporate secrecy (no public register of accounts/beneficial ownership). Cyprus's accounts were public (that's WHY they hid the assets); the BVI twin went dark BY DESIGN. So the leak-dependency is a direct consequence of secrecy jurisdictions. Concrete, LIVE advocacy targets: (1) PUBLIC BENEFICIAL-OWNERSHIP REGISTERS — the EU moved toward these, then a 2022 EU court ruling rolled them back to "legitimate interest" access = contested policy fight NOW; (2) CROSS-JURISDICTION ENTITY TRANSPARENCY (so "Electus Cyprus" <-> "Electus BVI" links are public/searchable; same-name concealment only works because registries don't talk); (3) AUDITOR/GATEKEEPER ACCOUNTABILITY (Deloitte signed off accounts it knew were misleading — ties to EY case).
- Primary source(s): BBC Panorama / Bureau of Investigative Journalism, "Deloitte helped in falsifying documents..." (bbc.com/news/articles/c64g1l5389kvo, 2026); Cyprus Confidential leak.

### CASE 6 — LBMA / "clean gold" self-regulation failure  [status: exposed/ongoing]  (sources below; not independently re-verified)
- Domain(s): commodities, self-regulation, supply-chain certification, human rights / child labor, sanctions.
- Who caught it: JOURNALISTS (New York Times investigation) — went to the mines in person + obtained records/emails;
  an EU inspector's chance scrutiny (considering certifying the LBMA for an oversight role) first exposed the Madagascar deal.
- Trigger (first signal): soaring gold price (>$5,000/oz) made destructive/illegal mining profitable; evidence gold was
  financing armed groups (Sudan) + Amazon polluters, vs. the industry's claim it keeps "dirty" gold out.
- THE MOVE (M6 who-watches-the-watchdog + public-vs-private statement contradiction + backdated-record):
  1) PUBLIC-vs-PRIVATE contradiction: compare the LBMA's public claim ("the standard-setting org... global authority,
     85-90% of global gold") against its OWN COURT FILINGS ("a small, not-for-profit... does not possess the staff,
     expertise or resources"; it DENIES the standard-setter claim). The gap between what a body says publicly vs. in
     court/under oath = a reusable detection move. 2) WHO-FUNDS-THE-WATCHDOG: the LBMA is financed + run by the industry's
     biggest players (refiners like Asahi; HSBC, Morgan Stanley, J.P. Morgan, Deutsche Bank) — the "regulator" is owned by
     the regulated. 3) The certifier is a PAPERWORK COLLECTOR: relies on refiners to self-report + self-inspect; doesn't
     independently verify unless a whistleblower/journalist/law-enforcement forces it (leak-dependency again).
- Escalation / the cover-up: for Madagascar's central-bank gold (sourced partly from mines using child labor, e.g.
  Madagold), the Istanbul Gold Refinery's auditor filed paperwork claiming "no red-flag business" (freeing it from
  required mine inspections). When an EU inspector flagged it, the LBMA's compliance panel (incl. CEO Ruth Crowell)
  did NOT punish — instead helped create a NEW report making it look like red flags were disclosed from the start, and
  BACKDATED it as if filed in real time. The backdated report still sits on the LBMA site with no indication of alteration.
- Outcome / penalty: NONE — exposed, ongoing. Gold certified + sold; refiners now call Madagascar to buy. (Tanzanians
  are separately suing the LBMA over mine violence — that's where the court filings surfaced.)
- Ordinary-person accessibility: the public-vs-court-statement contradiction is PUBLIC-RECORD + spottable; the mine
  reality needed on-the-ground journalism; the backdating needed obtained emails/records (insider/leak).
- Cross-domain reach: M6 (who-funds-the-watchdog) recurs — finance (advisor conflicts), prediction-market affiliate
  trackers, nonprofit raters (Charity Navigator), and now an industry "regulator." The PUBLIC-vs-PRIVATE-STATEMENT move
  transfers anywhere a body makes bold public claims but hedges in court/filings. Backdating overlaps Abramovich (M8).
- WHO BENEFITS / WHO IT APPLIES TO: anyone relying on a "certified clean / ethically sourced" stamp (gold buyers,
  central banks, investors, consumers of any certification scheme — fair-trade, organic, ESG labels); mining communities,
  children. Action: ask WHO funds/runs the certifier; compare its public claims to its legal filings; treat a self-graded
  standard as [CHECK]. Lesson: "clean vs dirty is an industry fiction — there is just gold."
- Primary source(s): New York Times investigation (2026) — incl. "U.S. Mint Buys Drug Cartel Gold," "To Find Criminals
  and Child Exploitation in Gold Mines," reporting on LBMA/Istanbul Gold Refinery/Madagascar central bank; SwissAid (Marc Ummel).

### CASE 7 — T-Mobile "Price Guarantee" backtrack  [status: settled]  (sources below; not independently re-verified)
- Domain(s): telecom, consumer protection, advertising/deceptive promise, fine print.
- Who caught it: REGULATOR — NY Attorney General (Letitia James), Consumer Frauds & Protection Bureau.
- Trigger (first signal): T-Mobile advertised "Price Guarantee Plans" (2017) promising to "never change the
  price you pay" / "abolishes price hikes" (CEO said so publicly) — then in 2024 raised prices ~$5/line on
  ~252,957 NY plans. The PUBLIC PROMISE vs. the later PRICE HIKE is the contradiction.
- THE MOVE (M9 public-vs-private + promised-vs-delivered): the company's bold PUBLIC promise ("never raise
  prices") vs. the FINE PRINT it hid on its website "that supposedly gave it the right to raise rates." NY law:
  hidden/fine-print disclaimers are NOT an excuse to mislead. Classic promised(public)-vs-delivered(fine print).
- Escalation: OAG investigation -> settlement.
- Outcome / penalty: T-Mobile pays $98,000 to NY + consumer remedies worth up to >$38M: affected 4G customers
  can cancel + refund last month + $25 gift card, OR stay + free $250 5G phone / $150 credit + NO price hike
  until 2029. Must honor future guarantees + clearly disclose limits.
- Ordinary-person accessibility: the contradiction (public promise vs. your rising bill) is VISIBLE to the
  customer — you LIVED it. The remedy requires knowing it exists + claiming it (see EChannel note below).
- Cross-domain reach: M9 (public-vs-private statement) recurs — LBMA (Case 6), now T-Mobile. "Promised vs
  delivered" recurs — DoorDash (Case 3). Fine-print-as-escape-hatch transfers to any subscription/telecom/SaaS
  "guarantee." Ties to the SI finding: the fine print contradicts the headline promise.
- WHO BENEFITS / WHO IT APPLIES TO: anyone who bought on a "price lock / guarantee" that later broke
  (telecom, streaming, insurance, gym memberships). Action: compare the PUBLIC promise you were sold to the
  CURRENT fine print + your actual bill; if a regulator settled, CLAIM the remedy.
- Primary source(s): NY AG press release 2026-10-20 ("Secures Reimbursements for T-Mobile Customers...").

### CASE 8 — Meta / Cambridge Analytica (New Mexico verdict)  [status: settled/verdict]  (sources below; not independently re-verified)
- Domain(s): data privacy, platform consumer protection, consent/data-rights.
- Who caught it: REGULATOR + COURT — New Mexico AG (Raúl Torrez) sued 2021; a Santa Fe JURY decided.
- Trigger (first signal): the 2018 Cambridge Analytica revelations — a political consulting firm harvested
  personal data from up to 87M Facebook users via a third-party app, without consent.
- THE MOVE (misrepresentation at scale, proven in court): the state showed Meta MISLED users about who had
  access to their data + how it handled hate speech/misinformation. Jury found 26 of 29 statements misleading
  = 43M+ violations of NM consumer-protection law (counted per NM resident who saw each misleading statement).
- Escalation: jury verdict (Sep 25) -> judge's penalty order (Oct). Judge found >$219B warranted under state
  law ($5k/violation), reduced to $25B. (A SEPARATE NM case earlier in 2026: jury found Meta misled on teen
  safety -> $375M civil penalty + $567M into a teen-mental-health fund + required teen-protection measures.)
- Outcome / penalty: $25B (all directed to NM's school system). Meta had urged a cap of $3.45B; argued it
  doesn't SELL data + NM didn't prove any consumer was actually misled — the jury rejected that.
- Ordinary-person accessibility: the harm (data taken without consent) is invisible to the user — needed a
  whistleblower/journalist origin (CA revelations) + a state AG + a jury to surface + price it.
- Cross-domain reach: DATA-RIGHTS (M7 perpetual-data-license candidate) — this is the consequence-when-exposed
  case that move needed: platforms claiming broad data access, surfaced, now a $25B penalty. Directly supports
  the Kalshi data-license finding (perpetual/sublicensable license = the same "who really gets your data" issue).
- WHO BENEFITS / WHO IT APPLIES TO: anyone on a platform with broad data-access terms (i.e. everyone). Shows
  data-rights claims CAN carry real penalties once a regulator + court engage. Action: read what data rights
  you grant; data-rights harm is real even when invisible.
- Primary source(s): Reuters 2026-10-21 (NM v. Meta, Judge Francis Mathew, $25B order).

---

## CLAIMING IS TOO HARD — a recurring low-hanging-fruit finding (not a case; a pattern across settlements)
Across DoorDash (Case 3), T-Mobile (Case 7), and similar settlements: a regulator wins money/remedies FOR
consumers, but the consumer must (a) KNOW the settlement exists and (b) figure out IF THEY'RE ELIGIBLE and
(c) actually CLAIM it — and all three are HARD right now. Most eligible people never claim. This is a prime
SI ACTION/PRODUCT opportunity + low-hanging fruit: "a settlement happened at a company you used — are you
eligible, and here's the one-click way to claim." Pin as a strong Phase-3/4 action pattern + a feature. The
easier the eligibility check + claim, the more real money reaches people. 

---

## Cases to add (not yet researched)
- Wells Fargo fake accounts (how surfaced — LA Times reporting? internal?)
- Dieselgate / VW (ICCT academic road-test discrepancy = clean M2 promised-vs-delivered)
- Theranos (WSJ / Carreyrou + whistleblowers Shultz/Cheung)
- Boeing 737 MAX (internal messages / MCAS)
- Purdue / opioids
- Facebook / Cambridge Analytica (whistleblower Wylie)
- Finfluencer accountability (CFA Institute study = academic/analyst origin type)
- Roosevelt Institute $500M prediction-market retail-loss study (academic origin type)
