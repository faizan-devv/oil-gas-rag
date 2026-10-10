# RAG evaluation

| # | Type | Question | Rank of expected chunk, dense (top 5) | Rank, hybrid (top 5) | Expected chunks cited | Expected facts in answer | Numbers not in cited passages | Confidence |
|---|---|---|---|---|---|---|---|---|
| Q1 | well report (txt) | What were the issues during completion of WELL-2847-NX? | 2 | 3 | 1/1 | 6/6 | none | high |
| Q2 | manual | What does the manual say about replacing the mud pump seal? | 1 | 1 | 0/1 | 0/4 | none | high |
| Q3 | maintenance log, exact ID | What happened to MUD-PUMP-04 in the maintenance logs? | 5 | 1 | 1/1 | 2/2 | none | high |
| Q4 | well report (PDF) | Why was WELL-1975-NW only partially completed? | 1 | 1 | 1/1 | 3/3 | none | high |
| Q5 | aggregation across reports | Which wells had H2S detected during clean-up? | 3, 5, 1, 4 | 4, 2, 1, 3 | 4/4 | 4/4 | none | high |
| N1 | negative control (not in corpus) | What is the daily production rate of WELL-2847-NX in barrels? | n/a | n/a | 0/0 | 1/1 | none | low |

## Full outputs

### Q1: What were the issues during completion of WELL-2847-NX?

**Answer:** The issues during the completion of WELL-2847-NX included poor cement bonding in the interval from 1256 to 1360 m MD, which was resolved by a remedial squeeze of 34 bbl, and a fault with MUD-PUMP-04 (FLT-0392) due to a piston seal leak, causing an 8-hour delay [3].

**Cited:** [3] WELL-2847-NX.txt#03 (0.627)

**Retrieved (hybrid, top 5):** WELL-2847-NX.txt#01 (0.664), WELL-2847-NX.txt#02 (0.626), WELL-2847-NX.txt#03 (0.627), WELL-2847-NX.txt#00 (0.593), WELL-4033-NW.txt#03 (0.491)

**Expected facts missing from the answer:** none

**Confidence:** high: Answer cites 1 passage(s); best match similarity 0.63.

### Q2: What does the manual say about replacing the mud pump seal?

**Answer:** The manual states that mud pump piston seals must be replaced every 500 operating hours or immediately upon the occurrence of fault FLT-0392, whichever occurs first [3]. Additionally, it is recommended to replace the mud pump piston seals ahead of critical displacement operations rather than waiting until they reach the 500-hour limit to reduce the risk of unexpected failures [4].

**Cited:** [3] drilling_equipment_reference_guide.md#15 (0.619), [4] WELL-2261-SX.txt#04 (0.601)

**Retrieved (hybrid, top 5):** drilling_equipment_reference_guide.md#09 (0.666), drilling_equipment_reference_guide.md#04 (0.623), drilling_equipment_reference_guide.md#15 (0.619), WELL-2261-SX.txt#04 (0.601), drilling_equipment_reference_guide.md#00 (0.538)

**Expected facts missing from the answer:** 1350 Nm, 40 strokes per minute, 15 minutes, pressure side

**Confidence:** high: Answer cites 2 passage(s); best match similarity 0.62.

### Q3: What happened to MUD-PUMP-04 in the maintenance logs?

**Answer:** MUD-PUMP-04 had a fault FLT-0392, which was a leaking piston seal at the fluid end. The issue was resolved by replacing the seal, and the fault has cleared [1]. Additionally, it tripped on fault FLT-0392 during the displacement to completion brine, causing an 8-hour delay while the seal was replaced [2].

**Cited:** [1] maintenance_log_2025-01.jsonl#LOG-0036 (0.667), [2] WELL-2847-NX.txt#03 (0.54)

**Retrieved (hybrid, top 5):** maintenance_log_2025-01.jsonl#LOG-0036 (0.667), WELL-2847-NX.txt#03 (0.54), drilling_equipment_reference_guide.md#01 (0.517), drilling_equipment_reference_guide.md#09 (0.533), maintenance_log_2025-03.jsonl#LOG-0027 (0.7)

**Expected facts missing from the answer:** none

**Confidence:** high: Answer cites 2 passage(s); best match similarity 0.67.

### Q4: Why was WELL-1975-NW only partially completed?

**Answer:** WELL-1975-NW was only partially completed because the lower zone was isolated using a bridge plug at 3785 m MD, while only the upper zone was successfully completed [1]. This partial completion was likely due to challenges encountered during the completion process, such as cement bond issues and a tubing hanger seal leak, which required further action for full production [1].

**Cited:** [1] WELL-1975-NW.pdf#01 (0.664)

**Retrieved (hybrid, top 5):** WELL-1975-NW.pdf#01 (0.664), WELL-1975-NW.pdf#02 (0.58), WELL-1975-NW.pdf#00 (0.602), WELL-3589-NX.pdf#01 (0.497), WELL-1975-NW.pdf#04 (0.491)

**Expected facts missing from the answer:** none

**Confidence:** high: Answer cites 1 passage(s); best match similarity 0.66.

### Q5: Which wells had H2S detected during clean-up?

**Answer:** The wells that had H2S detected during clean-up are:

- WELL-4033-NW with 52 ppm [1]
- WELL-2261-SX with 16 ppm [2]
- WELL-4406-EA with 32 ppm [3]
- WELL-1402-SE with 47 ppm [4]

**Cited:** [1] WELL-4033-NW.txt#03 (0.635), [2] WELL-2261-SX.txt#03 (0.542), [3] WELL-4406-EA.txt#03 (0.544), [4] WELL-1402-SE.txt#03 (0.559)

**Retrieved (hybrid, top 5):** WELL-4033-NW.txt#03 (0.635), WELL-2261-SX.txt#03 (0.542), WELL-4406-EA.txt#03 (0.544), WELL-1402-SE.txt#03 (0.559), WELL-4033-NW.txt#04 (0.539)

**Expected facts missing from the answer:** none

**Confidence:** high: Answer cites 4 passage(s); best match similarity 0.64.

### N1: What is the daily production rate of WELL-2847-NX in barrels?

**Answer:** Not found in the documents.

**Cited:** none

**Retrieved (hybrid, top 5):** WELL-2847-NX.txt#01 (0.6), WELL-2847-NX.txt#02 (0.59), WELL-2847-NX.txt#04 (0.463), WELL-2847-NX.txt#03 (0.494), WELL-2847-NX.txt#00 (0.599)

**Expected facts missing from the answer:** none

**Confidence:** low: The retrieved passages do not answer this question (best similarity 0.60).
