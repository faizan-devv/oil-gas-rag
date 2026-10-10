Overview
This assignment is set in an oil and gas operational context. You will build a focused RAG pipeline over a small technical document corpus, extract structured information from maintenance logs, and wrap your core functionality in a lightweight API. Prioritise a working, well-documented system over breadth — a clean solution that covers three tasks well is far more valuable than four rushed ones.

You may use any open-source models and free-tier services. Local execution is fully acceptable.

Scenario
An oil and gas operator wants to make their technical documents queryable by field engineers. You are working with three document types: well completion report summaries (short PDFs or text files, 2–4 pages each), equipment maintenance logs (free-text paragraphs written by engineers), and a short drilling equipment reference guide (15–20 pages of technical prose).

Generate synthetic content following the schemas in the Appendix, or request sample files from HR. Keep the corpus small — 10 to 15 documents total is sufficient to demonstrate a working system.

Task 1 — RAG Pipeline
Build a question-answering system over the document corpus. An engineer should be able to ask a natural language question — for example "What were the issues during completion of Well X?" or "What does the manual say about replacing the mud pump seal?" — and receive a grounded, cited answer.

Your pipeline must ingest and lightly clean all three document types, implement a chunking strategy you justify briefly in your README (document your chunk size, overlap, and why), generate embeddings using a model of your choice (document your reasoning), store them in a vector database (FAISS, Chroma, or any free-tier option), and retrieve the most relevant chunks for a given query. Every answer must include the source document name and chunk reference so answers are auditable.

Run five test questions where you know the expected answer. For each, note whether the correct chunk was retrieved and whether the answer was faithful to the source. Include these results in your README as a short evaluation table — no formal scoring required, just honest notes on where it works and where it falls short.

Deliverables: RAG pipeline code, vector store setup, README covering architecture decisions and evaluation table.
Task 2 — Information Extraction
Build an extraction pipeline that processes maintenance log entries and outputs structured records. Each entry is a free-text paragraph written by a field engineer. Extract the following fields: equipment_id, fault_code (if present), fault_description, action_taken, engineer_name, date, and resolution_status (resolved, pending, or escalated).

Use spaCy, a Hugging Face NER model, or a prompted LLM — your choice, but justify it in one paragraph. Handle natural variation in phrasing — for example "replaced the seal", "seal swap carried out", and "new seal fitted" should map to a consistent normalised value. Output to a structured format (CSV, Parquet, or SQL table) that a data analyst can query directly.

Include two quality checks: a completeness check (are all required fields present?) and a consistency check (do dates parse, do equipment IDs follow the expected format?). Log failed records to a quarantine file with a reason code.

Deliverables: Extraction pipeline code, sample output of at least 15 records, quarantine logic, and a two to three sentence note on scaling to 500,000 entries.

Task 3 — Prompt Engineering (choose one task)
Pick one of the following and test three prompt strategies against it — zero-shot, few-shot with two examples, and chain-of-thought. Use any hosted or local LLM.

Option A: Extract structured maintenance data (the same fields as Task 2) from a free-text log entry using prompting alone.

Option B: Generate a three to five sentence executive summary of a well completion report.

For each strategy, run it against five test inputs and score the outputs using a simple rubric you define (for example accuracy of field extraction, or summary coverage and conciseness). Present results in a comparison table and write a short paragraph on which approach worked best and why.

Deliverables: Prompt variants, test inputs and outputs, comparison table, and a short reflection paragraph.

Task 4 — API Wrapper
Wrap your Task 1 RAG pipeline in a FastAPI application with two endpoints: POST /ask which accepts a JSON body with a question field and returns answer, sources, and a brief confidence note, and GET /health which returns system status and number of documents indexed. Include a Dockerfile so the application can be run locally with docker build and docker run. Write two pytest tests — one for the /ask response schema and one for /health.

Deliverables: FastAPI code, Dockerfile, two pytest tests, and three to five sentences in your README on how you would productionise this on Azure or AWS including how low-confidence answers would be flagged for human review.

What We Are Looking For
We want to see how you make engineering decisions under realistic time constraints. A well-explained system with honest notes on its limitations is far more impressive than an over-engineered one with no documentation. Your README is as important as your code — explain why you made each key choice, not just what you built.

Appendix — Synthetic Data Schemas


Well Completion Report (short text or PDF — key fields)

FieldFormatNoteswell_idSTRINGe.g. WELL-2847-NXoperatorSTRINGCompany namecompletion_dateDATEYYYY-MM-DDdepth_mdDECIMALMeasured depth in metresformationSTRINGe.g. Zechstein, Bunterissues_encounteredTEXTFree-text narrativecompletion_statusSTRINGSuccessful / Partial / AbandonedrecommendationsTEXTEngineer recommendations



Equipment Maintenance Log (free-text entries)



FieldFormatNoteslog_idSTRINGUnique entry IDequipment_idSTRINGe.g. MUD-PUMP-04fault_codeSTRINGe.g. FLT-0392 — may be absentlog_textTEXTFree-text written by field engineerengineer_nameSTRINGMay be abbreviated or initials onlytimestampDATETIMEISO 8601



Reference Manual (short technical prose — suggested sections)

System Overview, Component Specifications, Fault Diagnosis, Maintenance Schedules. Two to three paragraphs per section is sufficient for a working RAG demo.
