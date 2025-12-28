"""Document management endpoints."""

import asyncio
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.rag.chunker import chunker
from app.rag.retriever import retriever
from app.services.supabase import supabase_service
from app.services.document_processor import document_processor

logger = logging.getLogger(__name__)

router = APIRouter()


class Document(BaseModel):
    """Document model."""

    id: str
    title: str
    content: str
    source_url: Optional[str] = None
    source_type: str = "general"


class DocumentCreate(BaseModel):
    """Document creation model."""

    title: str
    content: str
    source_url: Optional[str] = None
    source_type: str = "general"


class DocumentSearch(BaseModel):
    """Document search request."""

    query: str
    top_k: int = 10
    source_type: Optional[str] = None


@router.get("", response_model=List[Document])
async def list_documents(
    limit: int = 10,
    offset: int = 0,
    source_type: Optional[str] = None,
):
    """List documents with pagination."""
    try:
        docs = await supabase_service.get_documents(
            limit=limit,
            offset=offset,
            source_type=source_type,
        )
        return [
            Document(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"],
                source_url=doc.get("source_url"),
                source_type=doc.get("source_type", "custom"),
            )
            for doc in docs
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Document)
async def create_document(doc: DocumentCreate):
    """Create a new document with automatic embedding generation."""
    try:
        result = await retriever.add_document(
            title=doc.title,
            content=doc.content,
            source_url=doc.source_url,
            source_type=doc.source_type,
        )

        return Document(
            id=result.get("id", str(uuid.uuid4())),
            title=doc.title,
            content=doc.content,
            source_url=doc.source_url,
            source_type=doc.source_type,
        )
    except Exception as e:
        logger.error(f"Error creating document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk")
async def create_documents_bulk(docs: List[DocumentCreate]):
    """Create multiple documents with chunking."""
    try:
        created = []
        for doc in docs:
            # Chunk the document
            chunks = chunker.chunk_text(doc.content, doc.title)

            for i, chunk in enumerate(chunks):
                chunk_title = (
                    f"{doc.title} (Part {i + 1}/{len(chunks)})"
                    if len(chunks) > 1
                    else doc.title
                )

                result = await retriever.add_document(
                    title=chunk_title,
                    content=chunk["content"],
                    source_url=doc.source_url,
                    source_type=doc.source_type,
                    metadata={
                        "chunk_index": chunk["chunk_index"],
                        "total_chunks": chunk["total_chunks"],
                        "parent_title": doc.title,
                    },
                )
                created.append(result)

        return {"status": "success", "documents_created": len(created)}
    except Exception as e:
        logger.error(f"Error bulk creating documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(search: DocumentSearch):
    """Search documents using hybrid retrieval."""
    try:
        results = await retriever.retrieve(
            query=search.query,
            top_k=search.top_k,
            source_type=search.source_type,
        )

        return {
            "query": search.query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Error searching documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document file (PDF, DOCX, TXT, MD)."""
    try:
        # Read file content
        content = await file.read()
        filename = file.filename or "document.txt"

        # Check file extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        # Process based on file type
        if ext in ["pdf", "docx"]:
            # Use document processor for PDF and DOCX
            result = await document_processor.process_file(
                file_content=content,
                filename=filename
            )

            if not result.get("success"):
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", "Failed to process document")
                )

            title = result.get("title", filename.rsplit(".", 1)[0])
            chunks = result.get("chunks", [])

            logger.info(f"[UPLOAD] Processing {filename}: {len(chunks)} chunks to embed")
            print(f"[UPLOAD] Processing {filename}: {len(chunks)} chunks to embed")

            # Prepare all documents for batch processing
            documents_to_add = []
            for idx, chunk in enumerate(chunks):
                chunk_title = (
                    f"{title} (Part {chunk['chunk_index'] + 1}/{len(chunks)})"
                    if len(chunks) > 1
                    else title
                )
                documents_to_add.append({
                    "title": chunk_title,
                    "content": chunk["content"],
                    "source_type": "research",
                    "metadata": {
                        "filename": filename,
                        "format": result.get("format"),
                        "chunk_index": chunk["chunk_index"],
                        "total_chunks": len(chunks),
                        "page_count": result.get("page_count"),
                        **result.get("metadata", {})
                    },
                })

            # Batch process all chunks at once - much faster!
            print(f"[UPLOAD] Starting batch embedding for {len(documents_to_add)} documents...")
            created = await retriever.add_documents_batch(documents_to_add)
            print(f"[UPLOAD] Completed! {len(created)} documents stored.")

            return {
                "status": "success",
                "filename": filename,
                "format": result.get("format"),
                "title": title,
                "page_count": result.get("page_count"),
                "chunk_count": len(created),
            }

        else:
            # Plain text files
            text_content = content.decode("utf-8")
            title = filename.rsplit(".", 1)[0] if "." in filename else filename

            # Chunk the text
            chunks = chunker.chunk_text(text_content, title)

            # Prepare all documents for batch processing
            documents_to_add = []
            for i, chunk in enumerate(chunks):
                chunk_title = (
                    f"{title} (Part {i + 1}/{len(chunks)})"
                    if len(chunks) > 1
                    else title
                )
                documents_to_add.append({
                    "title": chunk_title,
                    "content": chunk["content"],
                    "source_type": "research",
                    "metadata": {
                        "filename": filename,
                        "chunk_index": chunk["chunk_index"],
                        "total_chunks": chunk["total_chunks"],
                    },
                })

            # Batch process all chunks at once - much faster!
            created = await retriever.add_documents_batch(documents_to_add)

            return {
                "status": "success",
                "filename": filename,
                "format": "text",
                "chunk_count": len(created),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document."""
    try:
        success = await supabase_service.delete_document(document_id)
        if success:
            return {"status": "deleted", "id": document_id}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = "Describe this image in detail and extract any relevant information."
):
    """
    Analyze an uploaded image using vision AI.

    Supported formats: JPEG, PNG, GIF, WebP
    Max file size: 10MB
    """
    from app.services.multimodal import vision_service

    try:
        # Read file content
        content = await file.read()
        filename = file.filename or "image.jpg"

        # Check file size (10MB limit)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

        # Check file extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        allowed_formats = ["jpg", "jpeg", "png", "gif", "webp"]
        if ext not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format. Allowed: {', '.join(allowed_formats)}"
            )

        # Map extensions to format
        format_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
        image_format = format_map.get(ext, "jpeg")

        # Analyze image
        analysis = await vision_service.analyze_image(
            image_data=content,
            prompt=prompt,
            image_format=image_format
        )

        if not analysis:
            raise HTTPException(status_code=500, detail="Failed to analyze image")

        return {
            "status": "success",
            "filename": filename,
            "analysis": analysis,
            "format": image_format
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
