"""Generate the synthetic corpus: structured truth first, prose second.

Every document starts as a record built with a seeded RNG. The local LLM only
turns that record into prose, and the prose is checked against the record
before it is accepted. The records are saved to data/gold/ and are the ground
truth for the RAG questions and the extraction scoring.

    uv run python scripts/generate_corpus.py [--only wells|logs|manual]
"""

import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from fpdf import FPDF

from app.catalog import EQUIPMENT, EQUIPMENT_ID_RE, FAULT_CODES
from app.config import get_settings
from app.llm import chat, chat_json

SEED = 42
WORKERS = 8
SETTINGS = get_settings()
RAW = SETTINGS.data_dir
GOLD = SETTINGS.gold_dir


# --------------------------------------------------------------------------
# Well completion reports
# --------------------------------------------------------------------------

OPERATORS = ["Northmoor Energy", "Halden Petroleum", "Caldera Offshore"]
FORMATIONS = ["Zechstein", "Bunter", "Rotliegend", "Carboniferous", "Chalk"]
WELL_IDS = [
    "WELL-2847-NX", "WELL-3120-SE", "WELL-1975-NW", "WELL-4406-EA",
    "WELL-2261-SX", "WELL-3589-NX", "WELL-1402-SE", "WELL-4033-NW",
]
STATUSES = ["Successful"] * 5 + ["Partial"] * 2 + ["Abandoned"]
PDF_WELLS = {"WELL-1975-NW", "WELL-3589-NX"}


def well_issues(rng: random.Random, depth: int) -> list[dict]:
    """Pool of parametrised issues. Each carries its own recommendation."""
    at = lambda: rng.randrange(900, depth - 100)
    top = at()
    pump = rng.choice(EQUIPMENT["mud_pump"])
    return [
        {
            "type": "stuck_pipe",
            "fact": f"Differential sticking at {at()} m MD while running the completion string; the pipe was stuck for {rng.randrange(6, 30)} hours and was freed by jarring after spotting a {rng.randrange(30, 80)} bbl pipe-freeing pill.",
            "recommendation": "Reduce overbalance and limit stationary time across the depleted interval on offset wells.",
        },
        {
            "type": "lost_circulation",
            "fact": f"Lost circulation at {at()} m MD with total losses of {rng.randrange(40, 220)} m3 of drilling fluid; losses were cured with two LCM pills before casing was run.",
            "recommendation": "Pre-treat the mud system with lost-circulation material before entering the loss zone.",
        },
        {
            "type": "cement_bond",
            "fact": f"The cement bond log showed poor bonding across {top}-{top + rng.randrange(40, 120)} m MD; a remedial squeeze of {rng.randrange(15, 45)} bbl was performed and the repeat log was acceptable.",
            "recommendation": "Improve casing centralisation and review the spacer design for the production casing cement job.",
        },
        {
            "type": "packer",
            "fact": f"The production packer failed to set on the first attempt at {at()} m MD; it was retrieved, redressed and set on the second run, adding {rng.randrange(14, 40)} hours of rig time.",
            "recommendation": "Function-test packer setting tools at surface before running in hole.",
        },
        {
            "type": "h2s",
            "fact": f"H2S was detected at surface at {rng.randrange(12, 60)} ppm during clean-up flow; operations were suspended for {rng.randrange(4, 18)} hours while the area was ventilated.",
            "recommendation": "Add continuous H2S monitoring and scavenger treatment to the clean-up programme.",
        },
        {
            "type": "perforating",
            "fact": f"Perforating gun misfire on run {rng.randrange(2, 5)}: the guns across {top}-{top + rng.randrange(8, 25)} m MD did not fire and the interval was re-perforated on an additional run.",
            "recommendation": "Verify detonator continuity at surface and carry a backup firing head for each perforating run.",
        },
        {
            "type": "mud_pump",
            "fact": f"{pump} tripped on fault FLT-0392 (piston seal leak) during displacement to completion brine, causing {rng.randrange(5, 16)} hours of non-productive time while the seal was replaced.",
            "recommendation": "Replace mud pump piston seals ahead of critical displacement operations rather than running them to the 500-hour limit.",
        },
        {
            "type": "wellhead",
            "fact": f"The tubing hanger seal leaked during the {rng.choice([5000, 6500, 7500, 10000])} psi wellhead pressure test; the seal was replaced and the repeat test held.",
            "recommendation": "Inspect tubing hanger seal surfaces before landing and keep a spare seal kit on location.",
        },
        {
            "type": "wireline",
            "fact": f"The wireline logging tool became stuck at {at()} m MD and a fishing operation lasting {rng.randrange(10, 36)} hours was needed to recover it.",
            "recommendation": "Run a wiper trip and condition the hole before open-hole wireline logging.",
        },
    ]


def build_well_records(rng: random.Random) -> list[dict]:
    records = []
    statuses = STATUSES[:]
    rng.shuffle(statuses)
    for well_id, status in zip(WELL_IDS, statuses):
        depth = round(rng.uniform(2100, 4600), 1)
        completed = date(2024, 1, 15) + timedelta(days=rng.randrange(0, 330))
        issues = rng.sample(well_issues(rng, int(depth)), k=rng.choice([2, 2, 3]))
        outcome = {
            "Successful": "The well was completed as planned and handed over to production.",
            "Partial": f"Only the upper zone was completed; the lower zone was isolated with a bridge plug at {int(depth) - rng.randrange(150, 400)} m MD.",
            "Abandoned": f"The reservoir section was found to be water-bearing; the well was plugged and abandoned with cement plugs set at {int(depth) - rng.randrange(200, 500)} m MD and at surface.",
        }[status]
        records.append(
            {
                "well_id": well_id,
                "operator": rng.choice(OPERATORS),
                "completion_date": completed.isoformat(),
                "depth_md": depth,
                "formation": rng.choice(FORMATIONS),
                "completion_status": status,
                "outcome": outcome,
                "issues": [{"type": i["type"], "fact": i["fact"]} for i in issues],
                "recommendations": [i["recommendation"] for i in issues],
                "source": f"{well_id}.{'pdf' if well_id in PDF_WELLS else 'txt'}",
            }
        )
    return records


WELL_SECTION_SCHEMA = {
    "type": "object",
    "properties": {
        k: {"type": "string"}
        for k in ["summary", "operations_overview", "issues_encountered", "recommendations"]
    },
    "required": ["summary", "operations_overview", "issues_encountered", "recommendations"],
}


def numbers_in(text: str) -> set[str]:
    """Numbers of two or more digits. Single digits are skipped because the
    model legitimately spells them out ("run four", "three ram preventers")."""
    return set(re.findall(r"\d{2,}(?:\.\d+)?|\d\.\d+", text.replace(",", "")))


def write_well_prose(rec: dict) -> dict:
    facts = "\n".join(f"- {i['fact']}" for i in rec["issues"])
    recs = "\n".join(f"- {r}" for r in rec["recommendations"])
    prompt = f"""Write the prose sections of a well completion report summary as the completion engineer.

Well: {rec['well_id']}, operated by {rec['operator']}, {rec['formation']} formation,
measured depth {rec['depth_md']} m, completed {rec['completion_date']}, status {rec['completion_status']}.
Outcome: {rec['outcome']}

Issues encountered (use every one, keep every number, depth and code exactly as written):
{facts}

Recommendations (use every one):
{recs}

Return four sections of plain prose, no markdown and no bullet points:
- summary: 60-90 words.
- operations_overview: 120-160 words on the completion sequence. Do not put any depths, volumes or durations here that are not given above.
- issues_encountered: 150-220 words, one paragraph per issue.
- recommendations: 80-130 words.
Do not invent other well IDs, equipment IDs or fault codes."""
    required = set().union(*(numbers_in(i["fact"]) for i in rec["issues"]))
    for attempt in range(3):
        sections = chat_json(
            [{"role": "user", "content": prompt}],
            WELL_SECTION_SCHEMA,
            temperature=0.5,
            max_tokens=1400,
            seed=SEED + attempt,
        )
        missing = required - numbers_in(sections["issues_encountered"])
        if not missing:
            return sections
    raise RuntimeError(f"{rec['well_id']}: issue numbers missing from prose: {missing}")


def render_well(rec: dict, sections: dict) -> str:
    return f"""WELL COMPLETION REPORT SUMMARY

Well ID: {rec['well_id']}
Operator: {rec['operator']}
Completion Date: {rec['completion_date']}
Measured Depth (m): {rec['depth_md']}
Formation: {rec['formation']}
Completion Status: {rec['completion_status']}

1. Summary

{sections['summary'].strip()}

2. Operations Overview

{sections['operations_overview'].strip()}

3. Issues Encountered

{sections['issues_encountered'].strip()}

4. Recommendations

{sections['recommendations'].strip()}
"""


def latin1(text: str) -> str:
    for src, dst in {"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "₂": "2", "³": "3", "°": " deg "}.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


class ReportPDF(FPDF):
    """Adds the running header and footer a real scanned report would carry,
    so the loader's cleaning step has something to remove."""

    operator = ""
    well_id = ""

    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 6, f"{self.operator} - CONFIDENTIAL - {self.well_id}", align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 6, f"Page {self.page_no()} of {{nb}}", align="C")


def write_well_pdf(rec: dict, text: str, path) -> None:
    pdf = ReportPDF()
    pdf.operator, pdf.well_id = rec["operator"], rec["well_id"]
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, latin1(text))
    pdf.output(str(path))


def generate_wells(rng: random.Random) -> None:
    out = RAW / "well_reports"
    out.mkdir(parents=True, exist_ok=True)
    records = build_well_records(rng)
    with ThreadPoolExecutor(WORKERS) as pool:
        prose = list(pool.map(write_well_prose, records))
    for rec, sections in zip(records, prose):
        text = render_well(rec, sections)
        if rec["source"].endswith(".pdf"):
            write_well_pdf(rec, text, out / rec["source"])
        else:
            (out / rec["source"]).write_text(text)
    (GOLD / "well_reports.json").write_text(json.dumps(records, indent=2))
    print(f"wells: {len(records)} reports ({len(PDF_WELLS)} as PDF)")


# --------------------------------------------------------------------------
# Maintenance logs
# --------------------------------------------------------------------------

ENGINEERS = [
    "James Okafor", "Priya Raman", "Tom Hallworth", "Aisha Siddiqui",
    "Lars Eriksen", "Maria Kowalczyk", "Dev Patel", "Sarah McAllister",
]

# family -> list of (fault_code or None, fault_description, action_category, [action phrasings])
SCENARIOS = {
    "mud_pump": [
        ("FLT-0392", "piston seal leaking at the fluid end", "seal_replacement",
         ["replaced the seal", "seal swap carried out", "new seal fitted", "changed out the piston seal"]),
        ("FLT-0417", "liner worn, discharge pressure low", "part_replacement",
         ["replaced the liner", "liner changed out", "fitted a new liner"]),
        ("FLT-0455", "pulsation dampener pre-charge low", "recalibration",
         ["recharged the dampener to the correct pre-charge", "dampener pre-charge topped up and reset"]),
        (None, "suction strainer partially blocked with debris", "cleaning",
         ["cleaned out the suction strainer", "strainer pulled and flushed"]),
    ],
    "top_drive": [
        ("FLT-0521", "gearbox oil running over temperature", "lubrication",
         ["drained and replaced the gearbox oil", "gearbox oil change carried out", "flushed and refilled the gearbox"]),
        ("FLT-0538", "high vibration on the main bearing", "bearing_replacement",
         ["replaced the main bearing", "main bearing swapped out", "new main bearing fitted"]),
        (None, "service loop hose chafing on the guide rail", "inspection",
         ["inspected the hose, no action needed yet", "checked the hose over and left as is"]),
    ],
    "bop": [
        ("FLT-0610", "accumulator pressure low", "recalibration",
         ["recharged the accumulator bottles", "accumulator pre-charge restored"]),
        ("FLT-0633", "annular preventer element leaking", "seal_replacement",
         ["replaced the annular sealing element", "annular element swap carried out", "new annular element fitted"]),
        (None, "routine function check after rig move", "pressure_test",
         ["full pressure test carried out", "pressure tested the stack"]),
    ],
    "shaker": [
        ("FLT-0704", "screen torn on the bottom deck", "part_replacement",
         ["replaced the screen", "screen swapped for a new one", "fitted a new screen panel"]),
        ("FLT-0719", "vibrator motor failed", "part_replacement",
         ["replaced the vibrator motor", "motor swap carried out"]),
        (None, "screens blinded with sticky clay", "cleaning",
         ["washed down the screens", "screens pressure washed"]),
    ],
    "drawworks": [
        ("FLT-0802", "brake pads worn beyond limit", "part_replacement",
         ["replaced the brake pads", "new brake pads fitted", "brake pad change carried out"]),
        ("FLT-0815", "drum encoder signal dropping out", "recalibration",
         ["recalibrated the drum encoder", "encoder re-zeroed and recalibrated"]),
        (None, "drive chain running dry", "lubrication",
         ["greased the drive chain", "chain lubricated"]),
    ],
}

OUTCOMES = {
    "resolved": [
        "the unit is back in service and running normally",
        "tested OK afterwards and returned to service",
        "the fault has cleared and the job is closed out",
    ],
    "pending": [
        "the fix is temporary and a follow-up check is still needed next shift",
        "the unit is running but still waiting on parts to finish the job",
        "the job is not closed yet and is to be re-checked after 12 hours running",
    ],
    "escalated": [
        "the problem persists and has been escalated to the maintenance supervisor",
        "the fault came back and has been escalated to the OEM for support",
        "it is beyond what can be done on site and has been escalated to onshore engineering",
    ],
}

STYLES = [
    "terse, with a few abbreviations",
    "plain full sentences",
    "note form, clipped",
    "slightly chatty, as if written at the end of a long shift",
]

# Deliberately bad entries, to exercise the quarantine path.
DEFECTS = [
    "missing_equipment_id", "malformed_equipment_id", "unparseable_date",
    "malformed_fault_code", "missing_engineer", "future_date",
]
EXPECTED_REASON = {
    "missing_equipment_id": "MISSING_FIELD",
    "malformed_equipment_id": "BAD_EQUIPMENT_ID",
    "unparseable_date": "BAD_DATE",
    "malformed_fault_code": "BAD_FAULT_CODE",
    "missing_engineer": "MISSING_FIELD",
    "future_date": "BAD_DATE",
}


def written_name(rng: random.Random, full: str) -> str:
    first, last = full.split()
    return rng.choice([full, f"{first[0]}. {last}", f"{first[0]}{last[0]}", last])


def written_date(rng: random.Random, d: date) -> str | None:
    style = rng.choice(["iso", "long", "us_long", "slash", "none"])
    if style == "slash" and d.day <= 12:
        style = "long"  # dd/mm with a day <= 12 would be ambiguous ground truth
    return {
        "iso": d.isoformat(),
        "long": f"{d.day} {d:%B %Y}",
        "us_long": f"{d:%B} {d.day}, {d.year}",
        "slash": f"{d:%d/%m/%Y}",
        "none": None,
    }[style]


def build_log_records(rng: random.Random, n_good: int = 36) -> list[dict]:
    families = list(SCENARIOS)
    specs = [None] * n_good + DEFECTS
    rng.shuffle(specs)
    records = []
    for n, defect in enumerate(specs, start=1):
        family = rng.choice(families)
        code, fault, category, phrasings = rng.choice(SCENARIOS[family])
        status = rng.choices(["resolved", "pending", "escalated"], weights=[6, 2, 2])[0]
        day = date(2025, 1, 6) + timedelta(days=rng.randrange(0, 84))
        rec = {
            "log_id": f"LOG-{n:04d}",
            "equipment_id": rng.choice(EQUIPMENT[family]),
            "fault_code": code,
            "fault_description": fault,
            "action_taken": rng.choice(phrasings),
            "action_category": category,
            "engineer_name": written_name(rng, rng.choice(ENGINEERS)),
            "date": day.isoformat(),
            "date_as_written": written_date(rng, day),
            "resolution_status": status,
            "timestamp": f"{day.isoformat()}T{rng.randrange(6, 22):02d}:{rng.randrange(0, 60):02d}:00Z",
            "outcome_hint": rng.choice(OUTCOMES[status]),
            "style": rng.choice(STYLES),
            "family": family,
            "defect": defect,
            "expected_reason": EXPECTED_REASON.get(defect),
        }
        if defect == "missing_equipment_id":
            rec["equipment_id"] = None
        elif defect == "malformed_equipment_id":
            rec["equipment_id"] = rec["equipment_id"].replace("-", "").rstrip("0123456789") + str(rng.randrange(1, 5))
        elif defect == "unparseable_date":
            rec["date"], rec["date_as_written"] = None, "31/02/2025"
        elif defect == "malformed_fault_code":
            rec["fault_code"] = "FLT-39A"
        elif defect == "missing_engineer":
            rec["engineer_name"] = None
        elif defect == "future_date":
            rec["date"], rec["date_as_written"] = "2052-03-14", "14 March 2052"
        records.append(rec)
    return records


def log_prompt(rec: dict) -> str:
    family_name = rec["family"].replace("_", " ")
    lines = [
        f"- Equipment worked on: {rec['equipment_id']}. Copy this ID character for character, keeping its capitals and hyphens, and call the equipment by the ID alone (never write 'equipment tag' or 'equipment ID')."
        if rec["equipment_id"]
        else f"- Equipment: refer to it only as 'the {family_name}'. Do NOT write any equipment ID or number.",
        f"- Fault code shown on the panel: {rec['fault_code']} (write it exactly)"
        if rec["fault_code"]
        else "- No fault code was raised. Do not mention any fault code.",
        f"- What was wrong: {rec['fault_description']}",
        f"- What you did: \"{rec['action_taken']}\" (keep these words, adjusting only the grammar so the sentence reads naturally)",
        f"- How it ended: {rec['outcome_hint']}",
        f"- The entry must state the date of the work, written exactly like this: {rec['date_as_written']}"
        if rec["date_as_written"]
        else "- Do not mention any date or day. You may say 'this shift'.",
        f"- You identify yourself exactly as: {rec['engineer_name']} (as a sign-off or 'logged by')"
        if rec["engineer_name"]
        else "- Do not sign the entry and do not mention your own name.",
        f"- Writing style: {rec['style']}",
    ]
    return (
        "Write one equipment maintenance log entry as a field engineer on a drilling rig. "
        "One paragraph of 2 to 4 sentences, plain text, no markdown, no lists, no quotation marks. "
        "Include every detail below.\n\n" + "\n".join(lines) + "\n\n"
        "Beyond those details, do not add any other equipment IDs, fault codes, dates, times or people."
    )


def log_text_problem(rec: dict, text: str) -> str | None:
    """Return why `text` contradicts its record, or None when it is faithful."""
    for field in ("equipment_id", "fault_code", "engineer_name", "date_as_written"):
        if rec[field] and rec[field] not in text:
            return f"{field} missing"
    codes = set(re.findall(r"FLT-\w+", text))
    if codes - {rec["fault_code"]}:
        return "unexpected fault code"
    if not rec["equipment_id"] and any(EQUIPMENT_ID_RE.match(tok.strip(".,;:()")) for tok in text.split()):
        return "equipment ID leaked"
    if not rec["date_as_written"] and re.search(r"\b20\d\d\b", text):
        return "date leaked"
    if not rec["engineer_name"] and any(part in text for name in ENGINEERS for part in name.split()):
        return "engineer name leaked"
    return None


def write_log_text(rec: dict) -> str:
    problem = None
    for attempt in range(4):
        retry_note = f"\n\nA previous draft was rejected: {problem}. Fix that." if problem else ""
        text, _ = chat(
            [{"role": "user", "content": log_prompt(rec) + retry_note}],
            temperature=0.8,
            max_tokens=220,
            seed=SEED + int(rec["log_id"][-4:]) * 10 + attempt,
        )
        text = " ".join(text.split()).strip('"')
        problem = log_text_problem(rec, text)
        if problem is None:
            return text
    raise RuntimeError(f"{rec['log_id']}: {problem}")


def generate_logs(rng: random.Random) -> None:
    out = RAW / "maintenance_logs"
    out.mkdir(parents=True, exist_ok=True)
    records = build_log_records(rng)
    with ThreadPoolExecutor(WORKERS) as pool:
        texts = list(pool.map(write_log_text, records))

    by_month: dict[str, list[dict]] = {}
    gold = []
    for rec, text in zip(records, texts):
        # Raw files follow the appendix schema. The extractor reads log_text
        # and timestamp only; the other columns are not given to it.
        by_month.setdefault(rec["timestamp"][:7], []).append(
            {
                "log_id": rec["log_id"],
                "equipment_id": rec["equipment_id"] or "",
                "fault_code": rec["fault_code"] or "",
                "log_text": text,
                "engineer_name": rec["engineer_name"] or "",
                "timestamp": rec["timestamp"],
            }
        )
        gold.append(
            {k: rec[k] for k in (
                "log_id", "equipment_id", "fault_code", "fault_description", "action_taken",
                "action_category", "engineer_name", "date", "resolution_status",
                "defect", "expected_reason",
            )}
            | {"log_text": text, "timestamp": rec["timestamp"]}
        )
    for old in out.glob("maintenance_log_*.jsonl"):
        old.unlink()
    for month, rows in sorted(by_month.items()):
        with (out / f"maintenance_log_{month}.jsonl").open("w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    with (GOLD / "maintenance_logs.jsonl").open("w") as f:
        f.writelines(json.dumps(g) + "\n" for g in gold)
    print(f"logs: {len(records)} entries in {len(by_month)} files ({len(DEFECTS)} deliberately defective)")


# --------------------------------------------------------------------------
# Reference manual
# --------------------------------------------------------------------------

MANUAL_TITLE = "Drilling Equipment Reference Guide"

# (section, subsection, facts). Facts are the checkable content; the LLM only
# supplies the connecting prose.
MANUAL = [
    ("1. System Overview", "1.1 Scope and Purpose", [
        "This guide covers the five equipment families on the rig: mud pumps, top drives, the BOP stack, shale shakers and the drawworks.",
        "It is written for field engineers and maintenance technicians and is the reference for fault diagnosis and scheduled maintenance.",
        "Equipment IDs follow the pattern FAMILY-NN, for example MUD-PUMP-04; fault codes follow the pattern FLT-NNNN.",
        "Where this guide and the OEM manual disagree, the OEM manual takes precedence and the discrepancy must be reported to the maintenance supervisor.",
    ]),
    ("1. System Overview", "1.2 Circulating System", [
        "The rig has four triplex mud pumps, MUD-PUMP-01 to MUD-PUMP-04, each rated at 1600 hp.",
        "Maximum discharge pressure is 5000 psi and the maximum pump speed is 120 strokes per minute.",
        "Normal drilling uses two or three pumps on line with one held on standby.",
        "Each pump has a pulsation dampener on the discharge side, pre-charged with nitrogen to 30 percent of the expected operating pressure.",
        "Mud returns pass over the shale shakers before going back to the active pits.",
    ]),
    ("1. System Overview", "1.3 Hoisting and Rotary Systems", [
        "The drawworks, DRAWWORKS-01, is rated at 1500 hp and uses a disc brake as the primary brake.",
        "A drum encoder provides block position to the driller's console and to the crown and floor saver system.",
        "There are two top drives, TOP-DRIVE-01 in service and TOP-DRIVE-02 held as a spare; each is rated for 500 tons hoisting load and 50000 ft-lb continuous drilling torque.",
        "The top drive gearbox is oil-lubricated and has its own temperature sensor.",
    ]),
    ("1. System Overview", "1.4 Well Control and Solids Control", [
        "BOP-STACK-01 is a 13-5/8 inch, 10000 psi stack with one annular preventer and three ram preventers.",
        "The accumulator unit operates at 3000 psi with a nitrogen pre-charge of 1000 psi in each bottle.",
        "There are three linear-motion shale shakers, SHALE-SHAKER-01 to SHALE-SHAKER-03, normally dressed with API 140 screens.",
        "Each shaker has two vibrator motors.",
    ]),
    ("2. Component Specifications", "2.1 Mud Pump Fluid End", [
        "Liner sizes from 5.5 inch to 7 inch can be fitted; the liner size sets the maximum allowable discharge pressure.",
        "Piston seals are nitrile rubber rated to 120 degrees Celsius.",
        "The liner wash system must deliver at least 40 litres per minute of coolant to each liner.",
        "The liner retainer nut is torqued to 1350 Nm.",
        "Valves and seats are replaced as a matched pair, never individually.",
    ]),
    ("2. Component Specifications", "2.2 Top Drive Gearbox and Bearings", [
        "The gearbox uses ISO VG 220 gear oil and holds 95 litres.",
        "The gearbox oil temperature alarm is at 85 degrees Celsius and the automatic trip is at 95 degrees Celsius.",
        "Main bearing vibration is alarmed at 7.1 mm/s RMS and the unit must be shut down above 11 mm/s RMS.",
        "The main bearing is grease-lubricated separately from the gearbox.",
    ]),
    ("2. Component Specifications", "2.3 BOP Stack and Accumulator", [
        "Ram preventers must close within 30 seconds and the annular preventer within 45 seconds.",
        "The accumulator must hold enough usable fluid to close all preventers with the charge pumps off and still retain 1200 psi.",
        "The annular sealing element is a consumable and is replaced when it fails to hold test pressure or shows visible cracking.",
        "The low-pressure test is 250 psi held for 5 minutes, followed by the high-pressure test.",
    ]),
    ("2. Component Specifications", "2.4 Shale Shakers and Drawworks Brake", [
        "Shakers run at 7.0 G with a deck angle adjustable from minus 1 to plus 5 degrees.",
        "Each vibrator motor is rated at 2.5 hp.",
        "Screens are tensioned to 50 Nm on each tension bolt.",
        "Drawworks brake pads are new at 25 mm thick and must be replaced at 6 mm.",
        "The drum encoder has a resolution of 1024 pulses per revolution.",
    ]),
    ("3. Fault Diagnosis", "3.1 Fault Code Reference", None),  # templated table, see below
    ("3. Fault Diagnosis", "3.2 Mud Pump Faults", [
        "FLT-0392 is a piston seal leak. Symptoms are fluid weeping from the liner tell-tale hole and discharge pressure fluctuating by more than 5 percent.",
        "To replace the mud pump piston seal: isolate and lock out the pump, bleed the discharge pressure to zero, drain the fluid end, remove the liner retainer and withdraw the piston.",
        "Fit the new seal with its lip facing the pressure side, lubricate it with clean water, reassemble and torque the liner retainer nut to 1350 Nm.",
        "After a seal replacement, run the pump in at 40 strokes per minute for 15 minutes and check the tell-tale hole for leaks before returning it to service.",
        "FLT-0417 is liner wear: discharge pressure falls at constant pump speed. Replace the liner and its piston together.",
        "FLT-0455 is low dampener pre-charge: discharge line vibration increases. Recharge with nitrogen only, never with air or oxygen.",
    ]),
    ("3. Fault Diagnosis", "3.3 Top Drive Faults", [
        "FLT-0521 is gearbox oil over-temperature, raised at the 85 degrees Celsius alarm point.",
        "For FLT-0521 check the oil level and the oil cooler fan first; if both are normal, drain and replace the oil and take a sample for analysis.",
        "FLT-0538 is high main bearing vibration. Re-grease the bearing and re-measure; if vibration stays above 7.1 mm/s RMS the bearing must be replaced.",
        "A top drive that trips on FLT-0538 twice within 24 hours must be swapped for the spare unit, TOP-DRIVE-02.",
    ]),
    ("3. Fault Diagnosis", "3.4 BOP Stack Faults", [
        "FLT-0610 is low accumulator pressure, raised when system pressure falls below 2700 psi.",
        "For FLT-0610 check the charge pumps and look for hydraulic leaks, then check bottle pre-charge and recharge any bottle below 900 psi.",
        "FLT-0633 is an annular preventer element leak, raised when the annular fails to hold test pressure.",
        "The annular sealing element must be replaced before drilling continues; drilling ahead with an active FLT-0633 is not permitted.",
        "Any BOP fault must be reported to the maintenance supervisor immediately, whatever its resolution status.",
    ]),
    ("3. Fault Diagnosis", "3.5 Shale Shaker and Drawworks Faults", [
        "FLT-0704 is a torn or blinded screen: solids appear in the active pit or mud runs off the end of the deck. Replace torn screens; wash blinded screens.",
        "FLT-0719 is a vibrator motor failure. Both motors on a shaker are replaced as a pair so that they stay balanced.",
        "FLT-0802 is brake pad wear beyond the 6 mm limit. The drawworks must not be used for hoisting until the pads have been replaced.",
        "FLT-0815 is a drum encoder signal fault. Check the connector and cable first, then recalibrate the encoder against the block height reference marks.",
    ]),
    ("4. Maintenance Schedules", "4.1 Per-Tour and Daily Checks", [
        "Every tour: check mud pump liner wash flow, look at the tell-tale holes for weeping, and inspect shaker screens for tears.",
        "Every tour: record top drive gearbox oil temperature and accumulator pressure.",
        "Daily: check the gearbox oil level, grease the top drive main bearing and check drawworks brake pad thickness visually.",
        "All readings are entered in the maintenance log with the equipment ID.",
    ]),
    ("4. Maintenance Schedules", "4.2 Weekly and Monthly Tasks", [
        "The BOP stack is function tested every 7 days and pressure tested every 21 days.",
        "Weekly: check pulsation dampener pre-charge on every mud pump and measure drawworks brake pad thickness with a gauge.",
        "Monthly: take a top drive gearbox oil sample for analysis and check shaker motor mounting bolts.",
        "Monthly: verify drum encoder calibration against the block height reference marks.",
    ]),
    ("4. Maintenance Schedules", "4.3 Scheduled Replacement Intervals", [
        "Mud pump piston seals are replaced every 500 operating hours, or immediately on fault FLT-0392.",
        "Mud pump liners are replaced every 1500 operating hours.",
        "Top drive gearbox oil is changed every 1000 operating hours or every 6 months, whichever comes first.",
        "The top drive main bearing is replaced every 8000 operating hours.",
        "Annular sealing elements are replaced every 12 months regardless of condition.",
    ]),
    ("4. Maintenance Schedules", "4.4 Record Keeping and Escalation", [
        "Every maintenance log entry must give the equipment ID, the fault code if one was raised, the action taken, the engineer's name and the date.",
        "A fault that is still pending after 24 hours must be escalated to the maintenance supervisor.",
        "The same fault code occurring three times on one piece of equipment within 30 days must be escalated to the OEM.",
        "Resolution status is recorded as resolved, pending or escalated.",
    ]),
]


def write_manual_subsection(item: tuple) -> str:
    section, title, facts = item
    if facts is None:
        rows = "\n".join(f"| {code} | {fam.replace('_', ' ')} | {meaning} |" for code, (fam, meaning) in FAULT_CODES.items())
        return (
            "The table lists every fault code raised by the rig control system. "
            "Diagnosis and corrective action for each code are given in sections 3.2 to 3.5.\n\n"
            "| Fault code | Equipment | Meaning |\n|---|---|---|\n" + rows
        )
    prompt = f"""Write the body of one subsection of a drilling rig equipment reference manual.

Manual section: {section}
Subsection: {title}

Facts (state every one; keep every number, unit, equipment ID and fault code exactly as written):
{chr(10).join('- ' + f for f in facts)}

Write 2 to 3 paragraphs of formal technical prose, 170 to 260 words in total.
Plain text only: no headings, no bullet points, no markdown.
Do not introduce any numeric value, equipment ID or fault code that is not in the facts."""
    required = set().union(*(numbers_in(f) for f in facts))
    missing: set[str] = set()
    for attempt in range(3):
        text, _ = chat([{"role": "user", "content": prompt}], temperature=0.4, max_tokens=700, seed=SEED + attempt)
        missing = required - numbers_in(text)
        if not missing:
            return text.strip()
    raise RuntimeError(f"{title}: facts missing from prose: {missing}")


def generate_manual() -> None:
    out = RAW / "manual"
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(WORKERS) as pool:
        bodies = list(pool.map(write_manual_subsection, MANUAL))
    parts = [f"# {MANUAL_TITLE}\n\nSynthetic document written for a retrieval demo. Not for operational use."]
    current = None
    for (section, title, _), body in zip(MANUAL, bodies):
        if section != current:
            parts.append(f"## {section}")
            current = section
        parts.append(f"### {title}\n\n{body}")
    (out / "drilling_equipment_reference_guide.md").write_text("\n\n".join(parts) + "\n")
    facts = [{"section": s, "subsection": t, "facts": f} for s, t, f in MANUAL if f]
    (GOLD / "manual_facts.json").write_text(json.dumps(facts, indent=2))
    print(f"manual: {len(MANUAL)} subsections, {sum(len(b.split()) for b in bodies)} words")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["wells", "logs", "manual"])
    args = parser.parse_args()
    GOLD.mkdir(parents=True, exist_ok=True)
    # One RNG per document type, so regenerating one type leaves the others' truth unchanged.
    if args.only in (None, "wells"):
        generate_wells(random.Random(SEED))
    if args.only in (None, "logs"):
        generate_logs(random.Random(SEED + 1))
    if args.only in (None, "manual"):
        generate_manual()


if __name__ == "__main__":
    main()
