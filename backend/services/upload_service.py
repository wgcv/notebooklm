import os
from uuid import uuid4

import boto3
import sqlalchemy
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile

from embedding.vectordb import delete_by_document_id, embed_and_store
from database.db import database, documents

ALLOWED_FORMATS = ["txt", "pdf", "docx"]
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "notebooklm-documents")
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localstack:4566")
LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localstack:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

def _get_s3_client():
    """Create an S3 client configured for LocalStack."""
    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def _extract_extension(filename: str | None) -> str:
    """Return normalized file extension or raise for missing extension."""
    if not filename or "." not in filename:
        raise HTTPException(status_code=400, detail="File must include an extension.")
    return filename.rsplit(".", 1)[1].lower()


def _ensure_bucket_exists(client, bucket_name: str) -> None:
    """Ensure the target S3 bucket exists before upload."""
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code in {"404", "NoSuchBucket", "NotFound"}:
            client.create_bucket(Bucket=bucket_name)
            return
        raise


def _build_document_url(bucket_name: str, object_key: str) -> str:
    """Build a stable URL string to persist in the documents table."""
    return f"{LOCALSTACK_URL.rstrip('/')}/{bucket_name}/{object_key}"


async def _insert_document(thread_id: str, document_url: str, document_name: str) -> int:
    """Persist uploaded document metadata and return the new row id."""
    query = documents.insert().values(
        thread_id=thread_id,
        documentUrl=document_url,
        documentName=document_name,
    )
    document_id = await database.execute(query)
    return int(document_id)


async def _get_document_by_id(document_id: int):
    """Fetch a document row by id or raise if it does not exist."""
    select_query = documents.select().where(documents.c.id == document_id)
    document = await database.fetch_one(select_query)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


def _extract_bucket_and_key(document_url: str) -> tuple[str, str]:
    """Extract S3 bucket and object key from a persisted endpoint URL."""
    endpoint_prefix = f"{LOCALSTACK_URL.rstrip('/')}/"
    if not document_url.startswith(endpoint_prefix):
        raise HTTPException(status_code=500, detail="Stored document URL is not a valid S3 endpoint URL.")

    relative_path = document_url[len(endpoint_prefix) :]
    if "/" not in relative_path:
        raise HTTPException(status_code=500, detail="Stored document URL is missing object key.")

    bucket_name, object_key = relative_path.split("/", 1)
    return bucket_name, object_key


def _filename_from_key(object_key: str) -> str:
    """Extract filename from S3 object key."""
    return object_key.rsplit("/", 1)[-1]


async def delete_uploaded_file_from_storage(document_id: int) -> dict:
    """Delete a previously uploaded file from S3 and remove its DB record."""
    select_query = documents.select().where(documents.c.id == document_id)
    document = await database.fetch_one(select_query)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    document_url = document["documentUrl"]
    thread_id = document["thread_id"]
    bucket_name, object_key = _extract_bucket_and_key(document_url)
    s3_client = _get_s3_client()

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
    except (ClientError, BotoCoreError) as error:
        raise HTTPException(status_code=502, detail=f"Failed to delete file from S3: {error}") from error

    delete_query = documents.delete().where(documents.c.id == document_id)
    await database.execute(delete_query)
    # delete from chroma db
    await delete_by_document_id(document_id=document_id)
    return {
        "id": document_id,
        "thread_id": thread_id,
        "documentUrl": document_url,
        "documentName": document["documentName"],
        "bucket": bucket_name,
        "key": object_key,
        "deleted": True,
    }


async def get_document_download_payload(document_id: int) -> dict:
    """Fetch a document from S3 and return payload needed for HTTP download."""
    document = await _get_document_by_id(document_id=document_id)
    document_url = document["documentUrl"]
    bucket_name, object_key = _extract_bucket_and_key(document_url)
    s3_client = _get_s3_client()

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    except (ClientError, BotoCoreError) as error:
        raise HTTPException(status_code=502, detail=f"Failed to download file from S3: {error}") from error

    file_bytes = response["Body"].read()
    content_type = response.get("ContentType") or "application/octet-stream"

    return {
        "id": int(document["id"]),
        "thread_id": document["thread_id"],
        "documentName": document["documentName"],
        "filename": _filename_from_key(object_key),
        "content_type": content_type,
        "bytes": file_bytes,
    }


async def list_documents_by_thread_id(thread_id: str) -> list[dict]:
    """Return all documents associated with a given thread id."""
    select_query = (
        documents.select()
        .where(documents.c.thread_id == thread_id)
        .order_by(documents.c.createdAt.desc())
    )
    rows = await database.fetch_all(select_query)
    return [
        {
            "id": int(row["id"]),
            "thread_id": row["thread_id"],
            "documentUrl": row["documentUrl"],
            "documentName": row["documentName"],
            "createdAt": row["createdAt"],
            "updatedAt": row["updatedAt"],
        }
        for row in rows
    ]


async def upload_file_to_storage(thread_id: str, file: UploadFile) -> dict:
    """Upload an allowed file to S3 and persist its metadata in the database."""
    extension = _extract_extension(file.filename)
    if extension not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed formats: {ALLOWED_FORMATS}",
        )

    file_bytes = await file.read()
    document_name = file.filename or "uploaded-file"
    object_key = f"{thread_id}/{uuid4().hex}.{extension}"
    s3_client = _get_s3_client()

    try:
        _ensure_bucket_exists(s3_client, S3_BUCKET_NAME)
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=file_bytes,
            ContentType=file.content_type or "application/octet-stream",
        )
    except (ClientError, BotoCoreError) as error:
        raise HTTPException(status_code=502, detail=f"Failed to upload file to S3: {error}") from error
    
    document_url = _build_document_url(S3_BUCKET_NAME, object_key)
    document_id = await _insert_document(
        thread_id=thread_id,
        document_url=document_url,
        document_name=document_name,
    )


    # --- Embedding + ChromaDB ---
    try:
        chunk_ids = await embed_and_store(
            file_bytes=file_bytes,
            extension=extension,
            thread_id=thread_id,
            object_key=object_key,
            s3_url=document_url,
            document_id=document_id,
            document_name=document_name,
        )
    except Exception as error:
        # Embedding failed but file is already in S3 — log and continue
        # In production you'd want to handle this more carefully
        print(f"[WARN] Embedding failed for {object_key}: {error}")
        chunk_ids = []
    return {
        "id": document_id,
        "thread_id": thread_id,
        "documentUrl": document_url,
        "documentName": document_name,
        "bucket": S3_BUCKET_NAME,
        "key": object_key,
        "chunk_ids": chunk_ids,
    }
