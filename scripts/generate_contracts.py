"""Generate a synthetic Kearney consulting-contracts corpus.

Writes long .md files under data/raw/contracts/ so ingest can pick them up
alongside the Wikipedia sample. Each file has front matter with a distinctive
``kearney-contracts/...`` source used by the dataset filter.

These documents are synthetic. They are not real agreements.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

DEFAULT_COUNT = 400
DEFAULT_SEED = 1634
MIN_BODY_CHARS = 6000
DATASET = "contracts"
LICENSE = "synthetic-test-corpus"
_SLUG_RE = re.compile(r"[^a-z0-9]+")
ATTRIBUTION_NAME = "ATTRIBUTION.md"

CONTRACT_TYPES: tuple[tuple[str, str], ...] = (
    ("msa", "Master Services Agreement"),
    ("sow", "Statement of Work"),
    ("nda", "Mutual Non-Disclosure Agreement"),
    ("dpa", "Data Processing Agreement"),
    ("change-order", "Change Order"),
    ("subcontractor", "Subcontractor Agreement"),
    ("engagement", "Engagement Letter"),
    ("staffing", "Staffing and Rate Card Agreement"),
    ("teaming", "Teaming and Alliance Agreement"),
    ("wind-down", "Engagement Wind-Down and Transition Agreement"),
    ("license", "Analytics Tooling License"),
    ("advisory", "Expert Advisory Retainer"),
)

KEARNEY_ENTITIES: tuple[str, ...] = (
    "A.T. Kearney, Inc.",
    "Kearney Ltd",
    "Kearney GmbH",
    "Kearney Middle East Limited",
    "Kearney India Private Limited",
    "Kearney SAS",
    "Kearney Japan LLC",
)

CLIENTS: tuple[tuple[str, str], ...] = (
    ("Northwind Automotive Holdings", "automotive"),
    ("Helios Consumer Brands", "consumer packaged goods"),
    ("Aether Energy Partners", "energy"),
    ("Meridian Health Systems", "healthcare"),
    ("Oakridge Capital Partners", "private equity"),
    ("Harborline Retail Group", "retail"),
    ("Nimbus Telecom plc", "telecommunications"),
    ("Vanguard Aerospace", "aerospace"),
    ("Solstice Chemicals", "chemicals"),
    ("Riverbank Financial", "banking"),
    ("Crestview Insurance", "insurance"),
    ("Ironclad Industrials", "industrials"),
    ("Copperridge Mining", "mining"),
    ("Blueharbor Logistics", "logistics"),
    ("Lumen Pharma", "pharmaceuticals"),
    ("Atlas Steelworks", "metals"),
    ("Greenfield AgriCo", "agriculture"),
    ("Pinnacle Hotels", "hospitality"),
    ("Silverline Utilities", "utilities"),
    ("Horizon Media Group", "media"),
    ("Cascade Semiconductors", "semiconductors"),
    ("Redwood Pensions", "pensions"),
    ("Summit Construction", "construction"),
    ("Pacific Ports Authority", "infrastructure"),
)

JURISDICTIONS: tuple[tuple[str, str], ...] = (
    ("the State of New York", "New York, New York"),
    ("the State of Delaware", "Wilmington, Delaware"),
    ("the laws of England and Wales", "London, England"),
    ("the Republic of Singapore", "Singapore"),
    ("the Federal Republic of Germany", "Frankfurt am Main"),
    ("the State of Illinois", "Chicago, Illinois"),
    ("the State of Texas", "Houston, Texas"),
    ("the laws of France", "Paris, France"),
    ("the Dubai International Financial Centre", "Dubai, UAE"),
    ("the laws of India", "Mumbai, India"),
)

FEE_MODELS: tuple[str, ...] = (
    "time and materials with a not-to-exceed cap",
    "fixed fee with milestone billing",
    "success-fee overlay on a reduced retainer",
    "monthly retainer plus pass-through expenses",
    "value-based fee tied to agreed savings",
)

DELIVERABLES: tuple[str, ...] = (
    "a diagnostic baseline and opportunity heatmap",
    "a 100-day value-creation roadmap",
    "a should-cost model for the top twenty SKUs",
    "a network redesign with scenario comparisons",
    "an operating-model blueprint and RACI",
    "a pricing-architecture playbook",
    "a digital-readiness and systems map",
    "a working-capital unlock plan",
    "a procurement category strategy",
    "a commercial-excellence sprint pack",
    "an integration day-one checklist",
    "a board-ready investment thesis memo",
)


@dataclass(frozen=True)
class ContractSpec:
    index: int
    type_slug: str
    type_label: str
    client: str
    industry: str
    kearney: str
    governing_law: str
    venue: str
    fee_model: str
    deliverable: str
    year: int
    month: int
    day: int
    number: str
    currency: str
    cap_amount: int
    hourly_rate: int
    term_months: int
    liability_months: int
    notice_days: int
    data_residency: str
    project_name: str


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    if not slug:
        raise ValueError(f"empty slug for {value!r}")
    return slug


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _pick(seq: tuple[T, ...], rng: random.Random, salt: int) -> T:
    return seq[(rng.randrange(len(seq)) + salt) % len(seq)]


def build_spec(index: int, rng: random.Random) -> ContractSpec:
    type_slug, type_label = CONTRACT_TYPES[index % len(CONTRACT_TYPES)]
    client, industry = CLIENTS[(index * 3) % len(CLIENTS)]
    kearney = KEARNEY_ENTITIES[(index * 5) % len(KEARNEY_ENTITIES)]
    law, venue = JURISDICTIONS[(index * 7) % len(JURISDICTIONS)]
    year = 2022 + (index % 5)
    month = 1 + (index % 12)
    day = 1 + ((index * 11) % 28)
    return ContractSpec(
        index=index,
        type_slug=type_slug,
        type_label=type_label,
        client=client,
        industry=industry,
        kearney=kearney,
        governing_law=law,
        venue=venue,
        fee_model=_pick(FEE_MODELS, rng, index),
        deliverable=_pick(DELIVERABLES, rng, index + 1),
        year=year,
        month=month,
        day=day,
        number=f"{year}-{index + 1:04d}",
        currency=("USD", "EUR", "GBP", "SGD")[index % 4],
        cap_amount=250_000 + (index % 40) * 75_000,
        hourly_rate=320 + (index % 15) * 25,
        term_months=3 + (index % 18),
        liability_months=6 + (index % 18),
        notice_days=15 + (index % 6) * 15,
        data_residency=("EU", "US", "UK", "SG", "IN")[index % 5],
        project_name=(
            f"Project {('Harbor', 'Cedar', 'Atlas', 'Nimbus', 'Quarry', 'Helix')[index % 6]}"
            f" {industry.split()[0].title()} {year}"
        ),
    )


def title_for(spec: ContractSpec) -> str:
    return (
        f"{spec.type_label} — {spec.client} and {spec.kearney} "
        f"({spec.industry}, {spec.year}) No. {spec.number}"
    )


def source_for(spec: ContractSpec) -> str:
    slug = slugify(f"{spec.type_slug}-{spec.client}-{spec.number}")
    return f"kearney-contracts/{spec.type_slug}/{slug}"


def filename_for(spec: ContractSpec) -> str:
    return f"{slugify(f'{spec.type_slug}-{spec.client}-{spec.number}')}.md"


def created_at_for(spec: ContractSpec) -> str:
    return date(spec.year, spec.month, spec.day).isoformat()


def _paragraphs(spec: ContractSpec) -> list[str]:
    cap = f"{spec.currency} {spec.cap_amount:,}"
    rate = f"{spec.currency} {spec.hourly_rate}"
    effective = f"{spec.day:02d}/{spec.month:02d}/{spec.year}"
    return [
        (
            f"This {spec.type_label} (the \"Agreement\") is entered into as of {effective} "
            f"by and between {spec.client}, a company operating in the {spec.industry} "
            f"sector (the \"Client\"), and {spec.kearney} (\"Kearney\"). The parties "
            f"intend this Agreement to govern {spec.project_name} and related advisory "
            f"work. The document is a synthetic test record for hybrid search and is "
            f"not an executed legal instrument."
        ),
        (
            f"Recitals. Client wishes to obtain management-consulting support covering "
            f"strategy, operations, commercial excellence, and transformation in "
            f"{spec.industry}. Kearney is willing to provide those services on the "
            f"terms below. The primary work product is {spec.deliverable}. Fees follow "
            f"{spec.fee_model}, subject to a commercial cap of {cap} unless a written "
            f"change order raises that cap."
        ),
        (
            f"Definitions. \"Affiliate\" means any entity controlling, controlled by, "
            f"or under common control with a party. \"Confidential Information\" means "
            f"non-public business, technical, financial, personal, or strategic "
            f"information disclosed in connection with {spec.project_name}, including "
            f"board materials, customer lists, cost models, and draft recommendations. "
            f"\"Deliverable\" means a work product identified in a statement of work. "
            f"\"Personal Data\" has the meaning given in the applicable privacy law "
            f"at the {spec.data_residency} residency location. \"Services\" means the "
            f"advisory work described in this Agreement and any attached schedules."
        ),
        (
            f"Scope of Services. Kearney shall perform the Services as an independent "
            f"contractor and not as an employee, partner, or joint venturer of Client. "
            f"Unless the parties agree otherwise in a change order, the Services "
            f"include diagnostic interviews, quantitative analysis, workshop "
            f"facilitation, and {spec.deliverable}. Kearney may use subcontractors "
            f"who are bound by confidentiality no less protective than this Agreement. "
            f"Client shall provide timely access to data rooms, plant tours, and "
            f"knowledgeable counterparts. Delays caused by missing Client inputs "
            f"extend milestones day-for-day."
        ),
        (
            f"Fees, expenses, and invoicing. Professional fees are billed under "
            f"{spec.fee_model}. Standard consultant time is charged at {rate} per "
            f"hour for manager-and-above roles unless a rate card schedule replaces "
            f"that figure. Reasonable travel, lodging, data, and specialist-tool "
            f"expenses are passed through at cost with a five percent administration "
            f"charge. Invoices issue monthly in {spec.currency} and are due within "
            f"thirty days. Late amounts accrue interest at one percent per month. "
            f"The aggregate professional-fee cap is {cap}. Work beyond the cap "
            f"requires a signed change order before Kearney continues."
        ),
        (
            f"Term and termination. The initial term is {spec.term_months} months "
            f"from the effective date and renews only by written agreement. Either "
            f"party may terminate for convenience on {spec.notice_days} days' written "
            f"notice. Either party may terminate immediately for material breach "
            f"that remains uncured fifteen days after notice, or for insolvency. "
            f"On termination Kearney shall deliver work-in-progress then existing, "
            f"and Client shall pay for Services performed plus non-cancellable "
            f"third-party commitments. Survival clauses include confidentiality, "
            f"intellectual property, data protection, and limitation of liability."
        ),
        (
            f"Confidentiality. Each party shall keep the other party's Confidential "
            f"Information in confidence for three years after expiry, using at least "
            f"the care it uses for its own similar information and no less than "
            f"reasonable care. Exceptions are information that is public, already "
            f"known, independently developed, or required by law, provided the "
            f"receiving party gives prompt notice where legally allowed. Kearney "
            f"may include Client's name and a high-level description of "
            f"{spec.project_name} in internal credentials unless Client objects in "
            f"writing. No press release shall be issued without prior written consent."
        ),
        (
            f"Intellectual property. Client retains ownership of its pre-existing "
            f"materials and of Client data. Kearney retains ownership of its "
            f"methodologies, models, benchmarks, software, and generic knowledge. "
            f"Upon full payment, Kearney grants Client a perpetual, non-exclusive, "
            f"non-transferable licence to use the Deliverables for Client's internal "
            f"business purposes. Client shall not resell Deliverables or use them "
            f"to train a competing advisory practice. Feedback about Kearney tools "
            f"may be used by Kearney without restriction."
        ),
        (
            f"Data protection and information security. Where Kearney processes "
            f"Personal Data, it acts as a processor for Client as controller unless "
            f"a statement of work says otherwise. Processing is limited to "
            f"{spec.project_name}. Data residency is {spec.data_residency} unless "
            f"Client consents to a transfer under an approved mechanism. Kearney "
            f"shall maintain ISO-aligned access control, encryption in transit, "
            f"and incident notification within seventy-two hours of confirming a "
            f"personal-data breach. Client is responsible for the lawfulness of "
            f"the data it provides and for notifying its own regulators."
        ),
        (
            f"Representations. Each party represents that it has authority to enter "
            f"this Agreement, that performance will not breach another contract, and "
            f"that it will comply with anti-bribery, sanctions, and export-control "
            f"laws. Kearney represents that it will perform the Services in a "
            f"professional manner consistent with generally accepted consulting "
            f"practice for {spec.industry} engagements. Kearney does not guarantee "
            f"a particular financial outcome, regulatory approval, or transaction "
            f"close. Client represents that information it supplies is materially "
            f"accurate to its knowledge."
        ),
        (
            f"Indemnification and limitation of liability. Each party shall indemnify "
            f"the other against third-party claims arising from its gross negligence, "
            f"wilful misconduct, or infringement of a third-party intellectual-property "
            f"right by materials it supplied. Kearney's aggregate liability under "
            f"this Agreement is limited to the fees paid for the Services giving "
            f"rise to the claim during the {spec.liability_months} months before "
            f"the claim, and in any event not more than {cap}. Neither party is "
            f"liable for indirect, incidental, special, or consequential damages, "
            f"lost profits, or lost data, except for confidentiality breaches, "
            f"infringement indemnity, or fraud. Claims must be brought within "
            f"{spec.liability_months} months after the claiming party knew or "
            f"should have known of the facts."
        ),
        (
            f"Insurance. During the term Kearney shall maintain professional-indemnity "
            f"and cyber insurance customary for an international consulting firm, "
            f"and workers-compensation cover as required by law. Certificates are "
            f"available on request. Client shall maintain commercially reasonable "
            f"cover for its own operations. Insurance is not a cap on liability "
            f"except where this Agreement already sets a cap."
        ),
        (
            f"Non-solicitation. For twelve months after the later of completion or "
            f"termination, neither party shall solicit the other party's employees "
            f"who had material contact with {spec.project_name}, except through "
            f"general advertising. Hiring in breach of this clause incurs a fee "
            f"equal to six months of the hired person's base salary. Independent "
            f"contractors engaged through a staffing schedule are excluded from "
            f"this restriction if the schedule says so."
        ),
        (
            f"Governing law and disputes. This Agreement is governed by "
            f"{spec.governing_law}, without regard to conflict-of-law rules. The "
            f"exclusive venue for litigation is {spec.venue}. The parties shall "
            f"first attempt good-faith negotiation for fifteen days, then mediation "
            f"in {spec.venue} before filing suit, except for applications for "
            f"injunctive relief to protect Confidential Information. EACH PARTY "
            f"WAIVES A JURY TRIAL TO THE EXTENT A COURT WOULD OTHERWISE ALLOW ONE."
        ),
        (
            f"Notices. Notices must be in writing and are effective on receipt if "
            f"sent by recognised courier or confirmed email to the legal contacts "
            f"listed in Schedule D. Informal project email does not change the "
            f"Agreement. Amendments must be signed by authorised representatives "
            f"of both parties. A scanned or electronic signature is sufficient."
        ),
        (
            f"General. If a provision is unenforceable, the remainder stays in "
            f"force. Failure to enforce a right is not a waiver. This Agreement, "
            f"including its schedules, is the entire agreement for "
            f"{spec.project_name} and supersedes prior proposals and oral "
            f"discussions. Neither party may assign the Agreement without consent, "
            f"except to an Affiliate in a corporate reorganisation. The Agreement "
            f"may be signed in counterparts. Headings are for convenience only."
        ),
        _schedule_a(spec, cap, rate),
        _schedule_b(spec, rate),
        _schedule_c(spec),
        _signature_block(spec, effective),
    ]


def _schedule_a(spec: ContractSpec, cap: str, rate: str) -> str:
    weeks = 4 + (spec.index % 8)
    return (
        f"Schedule A — Statement of work detail for {spec.project_name}. "
        f"Phase 1 (weeks 1–{weeks // 2}): confirm the baseline, interview "
        f"stakeholders across finance, operations, and commercial teams, and "
        f"collect the data needed for {spec.deliverable}. Phase 2 (weeks "
        f"{weeks // 2 + 1}–{weeks}): quantify opportunities, test them with "
        f"Client challenge sessions, and draft the recommendation pack. Phase 3: "
        f"transfer the model, train Client owners, and close open actions. "
        f"Success looks like a documented decision on the recommended path, not "
        f"a guaranteed P&L result. The commercial envelope remains {cap}. "
        f"On-site time is estimated at two days per week in {spec.venue} unless "
        f"the teams agree a remote cadence. Specialist support (modelling, "
        f"legal-adjacent research, or industry bench data) is billed at {rate} "
        f"per hour inside the cap. Client will nominate a single executive "
        f"sponsor and a day-to-day project manager within five business days."
    )


def _schedule_b(spec: ContractSpec, rate: str) -> str:
    junior = spec.hourly_rate - 80
    partner = spec.hourly_rate + 180
    return (
        f"Schedule B — Rate card and staffing. Roles and reference rates in "
        f"{spec.currency}: Analyst {junior}, Associate {spec.hourly_rate - 20}, "
        f"Manager {rate}, Principal {spec.hourly_rate + 80}, Partner {partner}. "
        f"A core team of one manager and two associates is assumed for "
        f"{spec.term_months} months, with partner time reserved for steering "
        f"committees. Weekend or statutory-holiday work, if requested in writing, "
        f"is billed at one and a half times the role rate. Unused retainer days "
        f"do not roll beyond the term. Travel time above four hours in a day may "
        f"be billed at half the role rate. This schedule controls if it conflicts "
        f"with the body of the {spec.type_label}."
    )


def _schedule_c(spec: ContractSpec) -> str:
    return (
        f"Schedule C — Data processing and security exhibit. Categories of data "
        f"may include employee identifiers, supplier commercial terms, customer "
        f"aggregates, and operational telemetry for the {spec.industry} estate. "
        f"No special-category health or children's data is in scope unless a "
        f"later change order says so. Sub-processors are limited to standard "
        f"productivity, storage, and model-hosting vendors under Kearney's "
        f"processor list. Deletion or return of Client data occurs within thirty "
        f"days after the later of project close or a written request, except for "
        f"backups cycled on a ninety-day rotation and records Kearney must keep "
        f"for professional or tax reasons. Security questionnaires will be "
        f"answered using Kearney's standard pack. Penetration-test summaries "
        f"can be reviewed under NDA at Kearney offices. Data residency remains "
        f"{spec.data_residency}."
    )


def _signature_block(spec: ContractSpec, effective: str) -> str:
    return (
        f"Signature block. IN WITNESS WHEREOF the parties have executed this "
        f"{spec.type_label} as of {effective}. For {spec.client}: ________________ "
        f"Name / Title / Date. For {spec.kearney}: ________________ Name / Title "
        f"/ Date. Agreement number {spec.number}. Project name {spec.project_name}. "
        f"Industry {spec.industry}. Governing law {spec.governing_law}. Venue "
        f"{spec.venue}. Synthetic corpus record only."
    )


def render_body(spec: ContractSpec) -> str:
    parts = _paragraphs(spec)
    body = "\n\n".join(parts)
    extra = 0
    while len(body) < MIN_BODY_CHARS:
        extra += 1
        body += (
            f"\n\nAnnex {extra} — Additional working notes for {spec.project_name}. "
            f"The teams will keep a weekly RAID log covering risks, assumptions, "
            f"issues, and dependencies. Sample risk themes include data quality in "
            f"the {spec.industry} source systems, delayed access to plants or "
            f"distribution centres, and overlapping transformation programmes. "
            f"Assumptions include stable organisational scope, a single source of "
            f"financial truth, and availability of the executive sponsor. "
            f"Dependencies include legal review of any customer-facing "
            f"recommendation and information-security approval for tools. These "
            f"notes are part of the searchable body so lexical queries on "
            f"limitation of liability, data residency {spec.data_residency}, "
            f"change orders, and {spec.fee_model} can still retrieve this "
            f"{spec.type_label}."
        )
    return body


def render_markdown(spec: ContractSpec, *, fetched: str) -> str:
    return (
        "---\n"
        f"title: {_yaml_quote(title_for(spec))}\n"
        f"source: {_yaml_quote(source_for(spec))}\n"
        f"license: {_yaml_quote(LICENSE)}\n"
        f"topic: {_yaml_quote(spec.type_slug)}\n"
        f"dataset: {_yaml_quote(DATASET)}\n"
        f"fetched: {_yaml_quote(fetched)}\n"
        "---\n"
        "\n"
        f"{render_body(spec).rstrip()}\n"
    )


def generate_specs(count: int, seed: int) -> list[ContractSpec]:
    if count < 0:
        raise ValueError("count must be >= 0")
    rng = random.Random(seed)
    return [build_spec(index, rng) for index in range(count)]


def write_contracts(
    out_dir: Path,
    specs: list[ContractSpec],
    *,
    fetched: str | None = None,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    day = fetched or today_iso()
    wrote = 0
    for spec in specs:
        path = out_dir / filename_for(spec)
        path.write_text(render_markdown(spec, fetched=day), encoding="utf-8")
        wrote += 1
    attribution = (
        "Synthetic Kearney consulting contracts for hybrid-search testing. "
        "Not real agreements and not legal advice.\n"
    )
    (out_dir / ATTRIBUTION_NAME).write_text(attribution, encoding="utf-8")
    return wrote


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic Kearney contracts into data/raw/contracts."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"number of contracts to write (default {DEFAULT_COUNT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"RNG seed (default {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output directory (default: data/raw/contracts under the repo)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    args = parse_args(argv)
    if args.count < 0:
        print("count must be >= 0", file=sys.stderr)
        return 1
    repo = root if root is not None else repo_root()
    out_dir = args.out if args.out is not None else repo / "data" / "raw" / "contracts"
    if args.out is not None and not out_dir.is_absolute():
        out_dir = repo / out_dir
    specs = generate_specs(args.count, args.seed)
    wrote = write_contracts(out_dir, specs)
    print(f"wrote {wrote} -> {out_dir.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
