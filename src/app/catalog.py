"""Domain vocabulary shared by the corpus generator, the extractor and the checks."""

import re

EQUIPMENT_ID_RE = re.compile(r"^[A-Z]+(-[A-Z]+)*-\d{2}$")
FAULT_CODE_RE = re.compile(r"^FLT-\d{4}$")

RESOLUTION_STATUSES = ["resolved", "pending", "escalated"]

# Controlled vocabulary that free-text actions are normalised onto, so that
# "replaced the seal", "seal swap carried out" and "new seal fitted" all land
# on seal_replacement.
ACTION_CATEGORIES = {
    "seal_replacement": "a seal, packing or sealing element was replaced",
    "bearing_replacement": "a bearing was replaced",
    "part_replacement": "any other part was replaced (liner, screen, motor, pad, sensor, hose)",
    "lubrication": "oil or grease was changed, topped up or flushed",
    "recalibration": "a setting, pre-charge, sensor or alignment was adjusted or recalibrated",
    "pressure_test": "a pressure or function test was the main action",
    "cleaning": "a component was cleaned, flushed or unblocked",
    "inspection": "inspected or monitored only, nothing changed",
    "other": "none of the above",
}

EQUIPMENT = {
    "mud_pump": ["MUD-PUMP-01", "MUD-PUMP-02", "MUD-PUMP-03", "MUD-PUMP-04"],
    "top_drive": ["TOP-DRIVE-01", "TOP-DRIVE-02"],
    "bop": ["BOP-STACK-01"],
    "shaker": ["SHALE-SHAKER-01", "SHALE-SHAKER-02", "SHALE-SHAKER-03"],
    "drawworks": ["DRAWWORKS-01"],
}

# code -> (equipment family, meaning)
FAULT_CODES = {
    "FLT-0392": ("mud_pump", "Piston seal leak at the fluid end"),
    "FLT-0417": ("mud_pump", "Liner wear causing low discharge pressure"),
    "FLT-0455": ("mud_pump", "Pulsation dampener pre-charge low"),
    "FLT-0521": ("top_drive", "Gearbox oil over-temperature"),
    "FLT-0538": ("top_drive", "Main bearing vibration high"),
    "FLT-0610": ("bop", "Accumulator pressure low"),
    "FLT-0633": ("bop", "Annular preventer element leak"),
    "FLT-0704": ("shaker", "Screen torn or blinded"),
    "FLT-0719": ("shaker", "Vibrator motor failure"),
    "FLT-0802": ("drawworks", "Brake pad wear beyond limit"),
    "FLT-0815": ("drawworks", "Drum encoder signal fault"),
}
