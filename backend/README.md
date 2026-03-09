# Backend

FastAPI backend for NotebookLM.

## Stack

- **FastAPI** — Async API framework with Pydantic validation, dependency injection, and streaming responses.
- **Chroma** — Vector store for document embeddings via LangChain; persists to `./chroma_db` and supports metadata filtering by `thread_id` and `document_id`.
- **ORM / Database** — SQLAlchemy for schema and metadata, `databases` for async SQLite access. Documents and thread metadata live in `database.db`.

## Run

```bash
uvicorn main:app --reload
```
