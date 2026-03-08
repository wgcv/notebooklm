"""NotebookLM-style RAG agent with Perplexity-like citations."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter

from embedding.vectordb import vectorstore

MODEL_NAME = "stepfun/step-3.5-flash:free"
DEFAULT_TOP_K = 6


model = ChatOpenRouter(
    model=MODEL_NAME,
    temperature=0,
)


@dataclass(frozen=True)
class SourceRef:
    """Stable source reference for citation rendering."""

    index: int
    name: str


def _source_name(doc: Document) -> str:
    """Return a readable source name from document metadata."""
    metadata = doc.metadata or {}
    return (
        metadata.get("document_name")
        or metadata.get("source")
        or metadata.get("s3_key")
        or "unknown-document"
    )


def dedupe_sources(docs: list[Document]) -> tuple[list[SourceRef], dict[str, int]]:
    """Build ordered unique source refs and a source-name to index map."""
    source_to_index: dict[str, int] = {}
    refs: list[SourceRef] = []
    for doc in docs:
        source_name = _source_name(doc)
        if source_name in source_to_index:
            continue
        source_index = len(refs)
        source_to_index[source_name] = source_index
        refs.append(SourceRef(index=source_index, name=source_name))
    return refs, source_to_index


def format_context(docs: list[Document], source_to_index: dict[str, int]) -> str:
    """Format retrieved chunks into a model-facing context block."""
    if not docs:
        return ""

    blocks: list[str] = []
    for idx, doc in enumerate(docs):
        source_name = _source_name(doc)
        source_index = source_to_index[source_name]
        text = (doc.page_content or "").strip()
        blocks.append(
            "\n".join(
                [
                    f"Chunk {idx}",
                    f"SourceRef: [{source_index}]",
                    "Content:",
                    text,
                ]
            )
        )
    return "\n\n".join(blocks)


def build_references(refs: list[SourceRef]) -> str:
    """Render final `Reference:` section."""
    if not refs:
        return "Reference:\n[0] unknown-document"

    lines = ["Reference:"]
    for ref in refs:
        lines.append(f"[{ref.index}] {ref.name}")
    return "\n".join(lines)


async def ask_rag(question: str, thread_id: str, top_k: int = DEFAULT_TOP_K) -> str:
    """Answer a question using thread-scoped Chroma retrieval with citations."""
    docs = vectorstore.similarity_search(
        question,
        k=top_k,
        filter={"thread_id": thread_id},
    )

    if not docs:
        return (
            "I could not find relevant content for this thread.\n\n"
            "Reference:\n"
            "[0] no-matching-documents"
        )

    refs, source_to_index = dedupe_sources(docs)
    context = format_context(docs, source_to_index)
    references = build_references(refs)

    system_prompt = (
        "You are NotebookLM-style assistant. Answer using only the provided context. "
        "When making factual statements, append citation markers like [0], [1]. "
        "Only cite source refs that exist in context. If information is missing, say so."
    )
    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Context:\n{context}\n\n"
        "Return plain text answer with inline citations."
    )

    response = await model.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )

    answer = response.content if isinstance(response.content, str) else str(response.content)
    return f"{answer.strip()}\n\n{references}"
