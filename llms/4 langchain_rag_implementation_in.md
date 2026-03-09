# Langchain rag implementation in notebooklm-agent
_Exported on 3/8/2026 at 10:15:17 EDT from Cursor (2.6.11)_

---

**User**

In @backend/agents/notebooklm-agent.py create a Langchain rag
Use this model:
@notebookllm.py (6-10) 

The rag is a chroma@backend/embedding/vectordb.py (The idea is to crate a rag like notebooklm, where you can ask about documents content)

use langchain, the rag need to reference like perplexity

for example 

Anwser context [0] 

Reference:
[0]  document-name.extension


I tink that we need to add document name in the database @backend/services/upload_service.py @db.py (45-50) 

use good practices make it clean

---

**Cursor**

I’ll quickly inspect the existing `agent`, `vectordb`, `upload_service`, and `db` flow to map the current architecture, then I’ll draft a concrete implementation plan for the RAG and citation format before making any changes.

I found the key gaps: `notebooklm-agent.py` is empty, current `notebookllm.py` is an arithmetic demo, and metadata currently stores only URL/thread_id. I’m now checking `main.py` and dependencies to ensure the RAG plan fits your API structure cleanly.

**RAG implementation choices**

> **Which RAG architecture do you want in `backend/agents/notebooklm-agent.py`?**
> - Simple LangChain RAG chain (retriever + prompt + model), no LangGraph loop ✔
> - LangGraph agent with retriever tool (more extensible for future tools)

> **For adding document name to DB, how should we handle existing SQLite data?**
> - Keep existing data and run a safe ALTER TABLE/add-column migration path
> - It is okay to recreate/reset local DB for now (simpler implementation) ✔

Thanks — I have what I need: we’ll build a simple LangChain RAG chain (no LangGraph loop), and we can use a reset-friendly DB update path. I’ll now draft a concise implementation plan with exact file changes and data flow.

---

**User**

Build NotebookLM-Style RAG with Citations

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I’m starting implementation now and will work through each existing todo in order, updating status as I go. First I’ll build `backend/agents/notebooklm-agent.py`, then wire metadata and API changes.

I finished the RAG module and moved to DB/upload changes. Next I’ll add `documentName` in `db.py` and propagate it through `upload_service.py` responses and insert flow.

I’ve propagated `document_name` into Chroma metadata. Next I’m wiring `main.py` to call the new RAG function from `notebooklm-agent.py` and removing dependency on the old arithmetic agent.

Implemented the NotebookLM-style RAG end-to-end with citations, using the model from `notebookllm.py`, and completed all todos.

### What changed

- Built a clean RAG module in `backend/agents/notebooklm-agent.py`:
  - Uses `ChatOpenRouter(model="stepfun/step-3.5-flash:free", temperature=0)`.
  - Retrieves from Chroma filtered by `thread_id`.
  - Formats context and deduplicates sources.
  - Returns answer with inline citations like `[0]` plus:
    - `Reference:`
    - `[0] document-name.extension`

- Wired API to new RAG in `backend/main.py`:
  - Replaced arithmetic-agent call with `ask_rag(question, thread_id)`.

- Added filename persistence in DB schema in `backend/database/db.py`:
  - New `documents.documentName` column.
  - Updated `documentAdd` and `document` Pydantic models with `documentName`.

- Updated upload flow in `backend/services/upload_service.py`:
  - Captures `UploadFile.filename` as `document_name`.
  - Stores `documentName` in DB insert.
  - Returns `documentName` in upload/list responses.
  - Passes `document_name` to embedding step.

- Propagated document name into Chroma metadata in `backend/embedding/vectordb.py`:
  - `embed_and_store(...)` now accepts `document_name`.
  - Saves `document_name` in each chunk metadata for citation rendering.

- Added compatibility export in `backend/agents/__init__.py`:
  - Loads `notebooklm-agent.py` (hyphenated filename) safely and exports `ask_rag`.

### Validation

- `ReadLints` on all edited files: no linter errors.
- I also attempted a runtime import smoke test; it failed in this environment due to missing installed module (`langchain_core`) in the active Python runtime, not due to code syntax.

### Important note for your setup

- Since you chose reset-friendly schema changes, recreate/reset your local `backend/database.db` so the new `documentName` column exists before running the updated API.

