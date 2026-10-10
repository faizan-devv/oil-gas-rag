# Prompt strategy comparison (Task 3, Option A)

## Five test inputs

| Strategy | Total score | equipment_id | fault_code | fault_description | action_taken | engineer_name | date | resolution_status | Valid JSON | Avg prompt tokens | Avg output tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | **33/35** | 4/5 | 5/5 | 5/5 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 | 486 | 95 |
| few_shot | **33/35** | 4/5 | 5/5 | 5/5 | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 | 762 | 85 |
| chain_of_thought | **32/35** | 5/5 | 5/5 | 5/5 | 4/5 | 3/5 | 5/5 | 5/5 | 5/5 | 535 | 352 |

### Score per input

| Input | Why it is hard | zero_shot | few_shot | chain_of_thought |
|---|---|---|---|---|
| LOG-0003 | note form, dd/mm/yyyy date, initials only, escalated | 7/7 | 7/7 | 7/7 |
| LOG-0011 | no equipment tag in the text (must return null, not guess one) | 6/7 (lost: equipment_id) | 6/7 (lost: equipment_id) | 7/7 |
| LOG-0016 | 'annular element' swap must map to seal_replacement; US-style date | 6/7 (lost: action_taken) | 6/7 (lost: action_taken) | 5/7 (lost: action_taken, engineer_name) |
| LOG-0028 | no fault code, initials only, ungrammatical action phrase | 7/7 | 7/7 | 7/7 |
| LOG-0029 | no calendar date ('this shift'), so the date must be null | 7/7 | 7/7 | 6/7 (lost: engineer_name) |

## Sanity check: all 42 corpus entries

| Strategy | Total score | equipment_id | fault_code | fault_description | action_taken | engineer_name | date | resolution_status | Valid JSON | Avg prompt tokens | Avg output tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | **286/294** | 41/42 | 42/42 | 42/42 | 38/42 | 39/42 | 42/42 | 42/42 | 42/42 | 486 | 97 |
| few_shot | **289/294** | 41/42 | 42/42 | 42/42 | 38/42 | 42/42 | 42/42 | 42/42 | 42/42 | 762 | 87 |
| chain_of_thought | **277.5/294** | 41/42 | 42/42 | 40.5/42 | 37/42 | 33/42 | 42/42 | 42/42 | 42/42 | 535 | 340 |

## Test inputs and raw outputs

### LOG-0003

**Input:** DRAWWORKS-01, 17/03/2025, FLT-0802, brake pads worn beyond limit, new brake pads fitted. Fault came back and has been escalated to the OEM for support. SM

**Expected:** `{"equipment_id": "DRAWWORKS-01", "fault_code": "FLT-0802", "fault_description": "brake pads worn beyond limit", "action_taken": "new brake pads fitted", "engineer_name": "SM", "date": "2025-03-17", "resolution_status": "escalated", "action_category": "part_replacement"}`

**zero_shot** (7/7):

```
{
  "equipment_id": "DRAWWORKS-01",
  "fault_code": "FLT-0802",
  "fault_description": "brake pads worn beyond limit",
  "action_taken": "new brake pads fitted",
  "action_category": "part_replacement",
  "engineer_name": "SM",
  "date": "17/03/2025",
  "resolution_status": "escalated"
}
```

**few_shot** (7/7):

```
{"equipment_id": "DRAWWORKS-01", "fault_code": "FLT-0802", "fault_description": "brake pads worn beyond limit", "action_taken": "new brake pads fitted", "action_category": "part_replacement", "engineer_name": "SM", "date": "17/03/2025", "resolution_status": "escalated"}
```

**chain_of_thought** (7/7):

```
### REASONING

- **equipment_id**: The entry starts with "DRAWWORKS-01", which is the equipment tag. This is taken directly from the log.
- **fault_code**: The entry includes "FLT-0802", which is the fault code. This is taken directly from the log.
- **fault_description**: The entry states "brake pads worn beyond limit", which describes the fault.
- **action_taken**: The entry says "new brake pads fitted", which is the action taken.
- **action_category**: The action is "new brake pads fitted", which falls under **part_replacement** (brake pads are a part).
- **engineer_name**: The entry ends with "SM", which is the engineer's initials. This is taken directly from the log.
- **date**: The entry includes "17/03/2025", which is the date of the work.
- **resolution_status**: The entry states "Fault came back and has been escalated to the OEM for support", which indicates the status is **escalated**.

### FINAL JSON
```json
{
  "equipment_id": "DRAWWORKS-01",
  "fault_code": "FLT-0802",
  "fault_description": "brake pads worn beyond limit",
  "action_taken": "new brake pads fitted",
  "action_category": "part_replacement",
  "engineer_name": "SM",
  "date": "17/03/2025",
  "resolution_status": "escalated"
}
```
```

### LOG-0011

**Input:** On 17/01/2025, the top drive displayed fault code FLT-0521 due to gearbox oil running over temperature. A gearbox oil change was carried out to address the issue. After the maintenance, the top drive was tested and found to be functioning correctly, returning to service. Logged by Lars Eriksen.

**Expected:** `{"equipment_id": null, "fault_code": "FLT-0521", "fault_description": "gearbox oil running over temperature", "action_taken": "gearbox oil change carried out", "engineer_name": "Lars Eriksen", "date": "2025-01-17", "resolution_status": "resolved", "action_category": "lubrication"}`

**zero_shot** (6/7):

```
{
  "equipment_id": "TOP-DRIVE",
  "fault_code": "FLT-0521",
  "fault_description": "gearbox oil running over temperature",
  "action_taken": "gearbox oil change",
  "action_category": "lubrication",
  "engineer_name": "Lars Eriksen",
  "date": "17/01/2025",
  "resolution_status": "resolved"
}
```

**few_shot** (6/7):

```
{"equipment_id": "TOP-DRIVE-01", "fault_code": "FLT-0521", "fault_description": "gearbox oil running over temperature", "action_taken": "gearbox oil change", "action_category": "lubrication", "engineer_name": "Lars Eriksen", "date": "17/01/2025", "resolution_status": "resolved"}
```

**chain_of_thought** (7/7):

```
### REASONING

- **equipment_id**: The log entry does not mention an equipment tag or ID. The term "top drive" is used, but it is not a specific equipment tag. Therefore, it is null.
- **fault_code**: The log entry explicitly states "fault code FLT-0521". This is the exact fault code as written.
- **fault_description**: The log entry states "gearbox oil running over temperature". This is the description of the fault.
- **action_taken**: The log entry states "a gearbox oil change was carried out to address the issue". This is the action taken.
- **action_category**: The action taken is "gearbox oil change", which falls under the category of **lubrication**.
- **engineer_name**: The log entry states "Logged by Lars Eriksen". The engineer's name is "Lars Eriksen".
- **date**: The log entry states "On 17/01/2025". This is the exact date as written.
- **resolution_status**: The log entry states "the top drive was tested and found to be functioning correctly, returning to service". This indicates the issue was resolved, so the status is **resolved**.

### FINAL JSON

```json
{
  "equipment_id": null,
  "fault_code": "FLT-0521",
  "fault_description": "gearbox oil running over temperature",
  "action_taken": "gearbox oil change",
  "action_category": "lubrication",
  "engineer_name": "Lars Eriksen",
  "date": "17/01/2025",
  "resolution_status": "resolved"
}
```
```

### LOG-0016

**Input:** BOP-STACK-01 was worked on February 1, 2025. Fault code FLT-0633 was shown on the panel indicating an annular preventer element was leaking. An annular element swap was carried out but it is beyond what can be done on site and has been escalated to onshore engineering. TH

**Expected:** `{"equipment_id": "BOP-STACK-01", "fault_code": "FLT-0633", "fault_description": "annular preventer element leaking", "action_taken": "annular element swap carried out", "engineer_name": "TH", "date": "2025-02-01", "resolution_status": "escalated", "action_category": "seal_replacement"}`

**zero_shot** (6/7):

```
{
  "equipment_id": "BOP-STACK-01",
  "fault_code": "FLT-0633",
  "fault_description": "annular preventer element was leaking",
  "action_taken": "annular element swap was carried out",
  "action_category": "part_replacement",
  "engineer_name": "TH",
  "date": "February 1, 2025",
  "resolution_status": "escalated"
}
```

**few_shot** (6/7):

```
{"equipment_id": "BOP-STACK-01", "fault_code": "FLT-0633", "fault_description": "annular preventer element was leaking", "action_taken": "annular element swap", "action_category": "part_replacement", "engineer_name": "TH", "date": "February 1, 2025", "resolution_status": "escalated"}
```

**chain_of_thought** (5/7):

```
### REASONING

- **equipment_id**: The entry states "BOP-STACK-01" which is the equipment tag. This is taken directly from the log.
- **fault_code**: The entry mentions "Fault code FLT-0633" which is the exact fault code.
- **fault_description**: The log says "annular preventer element was leaking" which describes the issue.
- **action_taken**: The entry states "An annular element swap was carried out" which is the action taken.
- **action_category**: The action is "annular element swap" which is a type of part replacement. Therefore, the category is **part_replacement**.
- **engineer_name**: The log does not mention the name or initials of the engineer, so this is **null**.
- **date**: The log states "February 1, 2025" which is the exact date of the work.
- **resolution_status**: The log says "it is beyond what can be done on site and has been escalated to onshore engineering" which indicates the issue has been **escalated**.

### FINAL JSON

```json
{
  "equipment_id": "BOP-STACK-01",
  "fault_code": "FLT-0633",
  "fault_description": "annular preventer element was leaking",
  "action_taken": "An annular element swap was carried out",
  "action_category": "part_replacement",
  "engineer_name": null,
  "date": "February 1, 2025",
  "resolution_status": "escalated"
}
```
```

### LOG-0028

**Input:** March 12, 2025, I worked on DRAWWORKS-01 and found the drive chain running dry. I chain lubricated it, but the problem persists and has been escalated to the maintenance supervisor. MK

**Expected:** `{"equipment_id": "DRAWWORKS-01", "fault_code": null, "fault_description": "drive chain running dry", "action_taken": "chain lubricated", "engineer_name": "MK", "date": "2025-03-12", "resolution_status": "escalated", "action_category": "lubrication"}`

**zero_shot** (7/7):

```
{
  "equipment_id": "DRAWWORKS-01",
  "fault_code": null,
  "fault_description": "drive chain running dry",
  "action_taken": "chain lubricated",
  "action_category": "lubrication",
  "engineer_name": "MK",
  "date": "March 12, 2025",
  "resolution_status": "escalated"
}
```

**few_shot** (7/7):

```
{"equipment_id": "DRAWWORKS-01", "fault_code": null, "fault_description": "drive chain running dry", "action_taken": "chain lubricated", "action_category": "lubrication", "engineer_name": "MK", "date": "March 12, 2025", "resolution_status": "escalated"}
```

**chain_of_thought** (7/7):

```
### REASONING

- **equipment_id**: The log entry mentions "DRAWWORKS-01", which is the exact equipment tag.  
  → `DRAWWORKS-01`

- **fault_code**: The entry does not mention any fault code.  
  → `null`

- **fault_description**: The entry states "the drive chain running dry", which describes the issue.  
  → `"drive chain running dry"`

- **action_taken**: The engineer "chain lubricated it", which is the action taken.  
  → `"chain lubricated it"`

- **action_category**: The action "chain lubricated it" falls under the category of **lubrication**.  
  → `"lubrication"`

- **engineer_name**: The entry ends with "MK", which is the engineer's initials.  
  → `"MK"`

- **date**: The log entry starts with "March 12, 2025", which is the exact date.  
  → `"March 12, 2025"`

- **resolution_status**: The entry states "the problem persists and has been escalated to the maintenance supervisor", which indicates the issue is **escalated**.  
  → `"escalated"`

---

### FINAL JSON

```json
{
  "equipment_id": "DRAWWORKS-01",
  "fault_code": null,
  "fault_description": "drive chain running dry",
  "action_taken": "chain lubricated it",
  "action_category": "lubrication",
  "engineer_name": "MK",
  "date": "March 12, 2025",
  "resolution_status": "escalated"
}
```
```

### LOG-0029

**Input:** Worked on MUD-PUMP-01 this shift, fault code FLT-0392 showed up on the panel indicating a piston seal leak at the fluid end. Changed out the piston seal as per the issue, got the unit running again but still waiting on parts to finish the job. LE

**Expected:** `{"equipment_id": "MUD-PUMP-01", "fault_code": "FLT-0392", "fault_description": "piston seal leaking at the fluid end", "action_taken": "changed out the piston seal", "engineer_name": "LE", "date": "2025-01-13", "resolution_status": "pending", "action_category": "seal_replacement"}`

**zero_shot** (7/7):

```
{
  "equipment_id": "MUD-PUMP-01",
  "fault_code": "FLT-0392",
  "fault_description": "piston seal leak at the fluid end",
  "action_taken": "changed out the piston seal",
  "action_category": "seal_replacement",
  "engineer_name": "LE",
  "date": null,
  "resolution_status": "pending"
}
```

**few_shot** (7/7):

```
{"equipment_id": "MUD-PUMP-01", "fault_code": "FLT-0392", "fault_description": "piston seal leak at the fluid end", "action_taken": "changed out the piston seal", "action_category": "seal_replacement", "engineer_name": "LE", "date": null, "resolution_status": "pending"}
```

**chain_of_thought** (6/7):

```
### REASONING

- **equipment_id**: The log entry states "Worked on MUD-PUMP-01 this shift", so the equipment ID is **MUD-PUMP-01**.
- **fault_code**: The log mentions "fault code FLT-0392 showed up on the panel", so the fault code is **FLT-0392**.
- **fault_description**: The log says "fault code FLT-0392 showed up on the panel indicating a piston seal leak at the fluid end", so the fault description is **piston seal leak at the fluid end**.
- **action_taken**: The log states "Changed out the piston seal as per the issue", so the action taken is **changed out the piston seal**.
- **action_category**: The action was replacing a seal, so the category is **seal_replacement**.
- **engineer_name**: The log does not mention the engineer's name or initials, so it is **null**.
- **date**: The log says "this shift" but does not provide a specific calendar date, so the date is **null**.
- **resolution_status**: The log states "got the unit running again but still waiting on parts to finish the job", which indicates the job is not fully resolved yet, so the status is **pending**.

### FINAL JSON
```json
{
  "equipment_id": "MUD-PUMP-01",
  "fault_code": "FLT-0392",
  "fault_description": "piston seal leak at the fluid end",
  "action_taken": "changed out the piston seal",
  "action_category": "seal_replacement",
  "engineer_name": null,
  "date": null,
  "resolution_status": "pending"
}
```
```

