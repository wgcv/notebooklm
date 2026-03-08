import os

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

import tempfile
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter


CHROMA_PERSIST_DIR = "./chroma_db"

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    base_url="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
)

vectorstore = Chroma(
    persist_directory=CHROMA_PERSIST_DIR,
    embedding_function=embeddings,
)


async def embed_and_store(
    file_bytes: bytes,
    extension: str,
    thread_id: str,
    object_key: str,
    s3_url: str,
    document_id: int,
    document_name: str,
) -> list[str]:
    """Parse file → split into chunks → embed → store in ChromaDB."""

    # Write to a temp file so LangChain loaders can read it
    with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        loader_map = {
            "pdf": PyPDFLoader,
            "txt": TextLoader,
            "docx": Docx2txtLoader,
        }
        loader = loader_map[extension](tmp_path)
        docs = loader.load()
    finally:
        os.unlink(tmp_path)  # always clean up

    # Attach metadata so you can filter by thread later
    for doc in docs:
        doc.metadata.update({
            "thread_id": thread_id,
            "s3_key": object_key,
            "s3_url": s3_url,
            "document_id": document_id,
            "document_name": document_name,
        })

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3200,
        chunk_overlap=500,
        separators=["\n\n", "\n", ".", " ", ""]

    )
    chunks = splitter.split_documents(docs)

    if not chunks:
        return []

    # add_documents returns the list of IDs assigned by Chroma
    ids = vectorstore.add_documents(chunks)
    return ids


async def delete_by_document_id(document_id: int) -> list[str]:
    """Delete all vector chunks tied to a document id and return deleted ids."""
    matches = vectorstore.get(where={"document_id": document_id})
    ids = matches.get("ids", [])

    if not ids:
        return []

    vectorstore.delete(ids=ids)
    return ids