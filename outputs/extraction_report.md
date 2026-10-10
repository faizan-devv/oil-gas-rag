# Extraction report (Task 2)

Prompt strategy: `few_shot` with schema-guided decoding.

- Entries processed: 42
- Clean records written: 36
- Quarantined: 6 (6 entries were made defective on purpose)

## Field accuracy against gold (42 entries)

| Field | Correct | Accuracy |
|---|---|---|
| equipment_id | 41/42 | 98% |
| fault_code | 42/42 | 100% |
| fault_description | 42/42 | 100% |
| action_taken | 38/42 | 90% |
| engineer_name | 42/42 | 100% |
| date | 42/42 | 100% |
| resolution_status | 42/42 | 100% |

`action_taken` is scored on the normalised `action_category`.

## Deliberately defective entries

| Entry | Defect planted | Expected reason | Reason codes raised | Result |
|---|---|---|---|---|
| LOG-0010 | malformed_fault_code | BAD_FAULT_CODE | BAD_FAULT_CODE | caught, expected code |
| LOG-0011 | missing_equipment_id | MISSING_FIELD | NOT_IN_SOURCE | caught, different code |
| LOG-0012 | future_date | BAD_DATE | BAD_DATE | caught, expected code |
| LOG-0019 | malformed_equipment_id | BAD_EQUIPMENT_ID | BAD_EQUIPMENT_ID | caught, expected code |
| LOG-0031 | missing_engineer | MISSING_FIELD | MISSING_FIELD | caught, expected code |
| LOG-0036 | unparseable_date | BAD_DATE | BAD_DATE | caught, expected code |

## Quarantined entries that were not defective

| Entry | Reason codes | Detail |
|---|---|---|
| none | | |

## Reason codes in the quarantine file

- BAD_DATE: 2
- BAD_EQUIPMENT_ID: 1
- BAD_FAULT_CODE: 1
- MISSING_FIELD: 1
- NOT_IN_SOURCE: 1
