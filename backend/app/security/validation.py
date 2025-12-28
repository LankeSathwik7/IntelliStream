"""Input validation and sanitization for security hardening."""

import re
import html
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator, model_validator
from fastapi import HTTPException


class InputValidationError(Exception):
    """Custom exception for input validation errors."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


# Patterns for detecting potentially malicious input
SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\b.*\b(FROM|INTO|TABLE|WHERE|SET)\b)",
    re.IGNORECASE
)
COMMAND_INJECTION_PATTERN = re.compile(
    r"[;&|`$]|\b(rm|cat|wget|curl|bash|sh|python|perl|ruby|nc|netcat)\b",
    re.IGNORECASE
)
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.%2e/|%2e\./")

# Maximum lengths for various inputs
MAX_MESSAGE_LENGTH = 10000
MAX_TITLE_LENGTH = 500
MAX_CONTENT_LENGTH = 100000
MAX_URL_LENGTH = 2000
MAX_THREAD_ID_LENGTH = 100


def sanitize_html(text: str) -> str:
    """
    Sanitize HTML by escaping potentially dangerous characters.

    Args:
        text: Input text that may contain HTML

    Returns:
        Sanitized text with HTML entities escaped
    """
    if not text:
        return ""

    # Remove script tags entirely
    text = SCRIPT_PATTERN.sub('', text)

    # Escape HTML entities
    text = html.escape(text, quote=True)

    return text


def sanitize_text(text: str) -> str:
    """
    Sanitize plain text input for safe storage and display.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace('\x00', '')

    # Remove control characters except newlines and tabs
    text = ''.join(char for char in text if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) != 127))

    # Normalize whitespace
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double

    return text.strip()


def detect_injection_attempt(text: str) -> Optional[str]:
    """
    Detect potential injection attacks in input.

    Args:
        text: Input text to check

    Returns:
        Type of injection detected, or None if clean
    """
    if not text:
        return None

    if SQL_INJECTION_PATTERN.search(text):
        return "sql_injection"

    if COMMAND_INJECTION_PATTERN.search(text):
        return "command_injection"

    if PATH_TRAVERSAL_PATTERN.search(text):
        return "path_traversal"

    return None


def validate_url(url: str) -> bool:
    """
    Validate URL format and check for unsafe patterns.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False

    if len(url) > MAX_URL_LENGTH:
        return False

    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if not url_pattern.match(url):
        return False

    # Check for path traversal in URL
    if PATH_TRAVERSAL_PATTERN.search(url):
        return False

    return True


def validate_thread_id(thread_id: str) -> bool:
    """
    Validate thread ID format.

    Args:
        thread_id: Thread ID to validate

    Returns:
        True if valid UUID format
    """
    if not thread_id:
        return True  # Optional field

    if len(thread_id) > MAX_THREAD_ID_LENGTH:
        return False

    # UUID pattern
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    return bool(uuid_pattern.match(thread_id))


class ValidatedChatInput(BaseModel):
    """Validated chat input model with security checks."""

    message: str
    thread_id: Optional[str] = None
    sources: List[str] = ["news", "research"]

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")

        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH}")

        # Check for injection attempts
        injection = detect_injection_attempt(v)
        if injection:
            raise ValueError(f"Potentially unsafe input detected: {injection}")

        return sanitize_text(v)

    @field_validator('thread_id')
    @classmethod
    def validate_thread(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None

        if not validate_thread_id(v):
            raise ValueError("Invalid thread ID format")

        return v

    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v: List[str]) -> List[str]:
        allowed_sources = ["news", "research", "web", "wikipedia", "arxiv", "documents"]
        return [s for s in v if s in allowed_sources]


class ValidatedDocumentInput(BaseModel):
    """Validated document input model with security checks."""

    title: str
    content: str
    source_type: str = "general"
    source_url: Optional[str] = None
    metadata: Optional[dict] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")

        if len(v) > MAX_TITLE_LENGTH:
            raise ValueError(f"Title exceeds maximum length of {MAX_TITLE_LENGTH}")

        return sanitize_html(v.strip())

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")

        if len(v) > MAX_CONTENT_LENGTH:
            raise ValueError(f"Content exceeds maximum length of {MAX_CONTENT_LENGTH}")

        return sanitize_text(v)

    @field_validator('source_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None

        if not validate_url(v):
            raise ValueError("Invalid URL format")

        return v

    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed_types = ["general", "research", "news", "documentation", "other"]
        if v not in allowed_types:
            return "general"
        return v


def validate_chat_input(message: str, thread_id: Optional[str] = None) -> ValidatedChatInput:
    """
    Validate and sanitize chat input.

    Args:
        message: User message
        thread_id: Optional thread ID

    Returns:
        ValidatedChatInput object

    Raises:
        HTTPException: If validation fails
    """
    try:
        return ValidatedChatInput(message=message, thread_id=thread_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_document_input(
    title: str,
    content: str,
    source_type: str = "general",
    source_url: Optional[str] = None
) -> ValidatedDocumentInput:
    """
    Validate and sanitize document input.

    Args:
        title: Document title
        content: Document content
        source_type: Type of source
        source_url: Optional source URL

    Returns:
        ValidatedDocumentInput object

    Raises:
        HTTPException: If validation fails
    """
    try:
        return ValidatedDocumentInput(
            title=title,
            content=content,
            source_type=source_type,
            source_url=source_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_file_upload(filename: str, content_type: str, size: int) -> bool:
    """
    Validate file upload for security.

    Args:
        filename: Original filename
        content_type: MIME type
        size: File size in bytes

    Returns:
        True if valid

    Raises:
        HTTPException: If validation fails
    """
    # Allowed file types
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', '.json'}
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
        'application/json'
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    # Check file extension
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check MIME type
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type"
        )

    # Check file size
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # Check for path traversal in filename
    if PATH_TRAVERSAL_PATTERN.search(filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

    return True
