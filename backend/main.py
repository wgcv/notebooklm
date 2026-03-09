import contextlib

from dotenv import load_dotenv
load_dotenv()  

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import ask_rag
from database.db import database
from services.upload_service import (
    delete_uploaded_file_from_storage,
    get_document_download_payload,
    list_documents_by_thread_id,
    upload_file_to_storage,
)



@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: connect DB on startup, disconnect on shutdown."""
    await database.connect()
    yield
    await database.disconnect()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http(s)?://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return "Hello"


class StreamRequest(BaseModel):
    thread_id: str
    message: str


async def token_stream(message: str, thread_id: str):
    async for chunk in ask_rag(question=message, thread_id=thread_id):
        yield chunk


@app.post("/stream")
async def stream_root(request: StreamRequest):
    return StreamingResponse(token_stream(request.message, request.thread_id), media_type="text/plain")


@app.post("/upload")
async def upload_file(thread_id: str = Form(...), file: UploadFile = File(...)):
    """Upload a file to S3 for use in the chat stream. Requires thread_id and file."""
    return await upload_file_to_storage(thread_id=thread_id, file=file)


@app.delete("/upload/{document_id}")
async def delete_upload_file(document_id: int):
    """Delete an uploaded file by document id."""
    return await delete_uploaded_file_from_storage(document_id=document_id)


@app.get("/upload/{document_id}/download")
async def download_upload_file(document_id: int):
    """Download an uploaded document by document id."""
    payload = await get_document_download_payload(document_id=document_id)
    return StreamingResponse(
        iter([payload["bytes"]]),
        media_type=payload["content_type"],
        headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
    )


@app.get("/documents")
async def get_documents_by_thread(thread_id: str = Query(...)):
    """Return all documents associated with a thread id."""
    return await list_documents_by_thread_id(thread_id=thread_id)