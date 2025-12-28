"""Tests for security modules."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestInputValidation:
    """Tests for input validation and sanitization."""

    def test_sanitize_html_escapes_tags(self):
        """Test HTML tag escaping."""
        from app.security.validation import sanitize_html

        text = "<script>alert('xss')</script>Hello"
        result = sanitize_html(text)

        assert "<script>" not in result
        assert "Hello" in result

    def test_sanitize_html_handles_empty(self):
        """Test empty input handling."""
        from app.security.validation import sanitize_html

        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""

    def test_sanitize_text_removes_null_bytes(self):
        """Test null byte removal."""
        from app.security.validation import sanitize_text

        text = "Hello\x00World"
        result = sanitize_text(text)

        assert "\x00" not in result
        assert "HelloWorld" in result

    def test_detect_sql_injection(self):
        """Test SQL injection detection."""
        from app.security.validation import detect_injection_attempt

        assert detect_injection_attempt("SELECT * FROM users") == "sql_injection"
        assert detect_injection_attempt("DROP TABLE users") == "sql_injection"
        assert detect_injection_attempt("Hello world") is None

    def test_detect_command_injection(self):
        """Test command injection detection."""
        from app.security.validation import detect_injection_attempt

        assert detect_injection_attempt("test; rm -rf /") == "command_injection"
        assert detect_injection_attempt("test | cat /etc/passwd") == "command_injection"
        assert detect_injection_attempt("Hello world") is None

    def test_detect_path_traversal(self):
        """Test path traversal detection."""
        from app.security.validation import detect_injection_attempt

        assert detect_injection_attempt("../../../etc/passwd") == "path_traversal"
        assert detect_injection_attempt("..\\..\\windows") == "path_traversal"
        assert detect_injection_attempt("Hello world") is None

    def test_validate_url_valid(self):
        """Test valid URL validation."""
        from app.security.validation import validate_url

        assert validate_url("https://example.com") is True
        assert validate_url("http://localhost:8000") is True
        assert validate_url("https://api.example.com/path?query=1") is True

    def test_validate_url_invalid(self):
        """Test invalid URL rejection."""
        from app.security.validation import validate_url

        assert validate_url("") is False
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://example.com") is False

    def test_validate_thread_id_valid(self):
        """Test valid thread ID validation."""
        from app.security.validation import validate_thread_id

        assert validate_thread_id("550e8400-e29b-41d4-a716-446655440000") is True
        assert validate_thread_id(None) is True  # Optional field

    def test_validate_thread_id_invalid(self):
        """Test invalid thread ID rejection."""
        from app.security.validation import validate_thread_id

        assert validate_thread_id("not-a-uuid") is False
        assert validate_thread_id("x" * 200) is False

    def test_validated_chat_input_success(self):
        """Test valid chat input."""
        from app.security.validation import ValidatedChatInput

        input_data = ValidatedChatInput(message="Hello world")

        assert input_data.message == "Hello world"

    def test_validated_chat_input_empty_message(self):
        """Test empty message rejection."""
        from app.security.validation import ValidatedChatInput

        with pytest.raises(ValueError):
            ValidatedChatInput(message="")

    def test_validated_chat_input_injection_blocked(self):
        """Test injection attempts are blocked."""
        from app.security.validation import ValidatedChatInput

        with pytest.raises(ValueError):
            ValidatedChatInput(message="SELECT * FROM users WHERE 1=1")


class TestRBAC:
    """Tests for role-based access control."""

    def test_role_hierarchy(self):
        """Test role enum exists."""
        from app.security.rbac import Role

        assert Role.ANONYMOUS.value == "anonymous"
        assert Role.USER.value == "user"
        assert Role.PREMIUM.value == "premium"
        assert Role.ADMIN.value == "admin"

    def test_permission_enum(self):
        """Test permission enum exists."""
        from app.security.rbac import Permission

        assert Permission.CHAT_READ.value == "chat:read"
        assert Permission.ADMIN_USERS.value == "admin:users"

    def test_get_role_from_user_anonymous(self):
        """Test anonymous role for no user."""
        from app.security.rbac import get_role_from_user, Role

        assert get_role_from_user(None) == Role.ANONYMOUS

    def test_get_role_from_user_authenticated(self):
        """Test user role for authenticated user."""
        from app.security.rbac import get_role_from_user, Role

        user = {"id": "123", "email": "user@example.com", "role": "authenticated"}
        assert get_role_from_user(user) == Role.USER

    def test_get_permissions_for_role(self):
        """Test permission lookup by role."""
        from app.security.rbac import get_permissions_for_role, Role, Permission

        anonymous_perms = get_permissions_for_role(Role.ANONYMOUS)
        assert Permission.CHAT_READ in anonymous_perms
        assert Permission.ADMIN_USERS not in anonymous_perms

        admin_perms = get_permissions_for_role(Role.ADMIN)
        assert Permission.ADMIN_USERS in admin_perms

    def test_check_permission(self):
        """Test permission checking."""
        from app.security.rbac import check_permission, Permission

        user = {"id": "123", "role": "authenticated"}
        assert check_permission(user, Permission.CHAT_READ) is True
        assert check_permission(user, Permission.ADMIN_USERS) is False

    def test_rate_limits_by_role(self):
        """Test rate limits vary by role."""
        from app.security.rbac import get_rate_limits_for_user

        anonymous_limits = get_rate_limits_for_user(None)
        user_limits = get_rate_limits_for_user({"id": "123", "role": "authenticated"})

        assert anonymous_limits["requests_per_minute"] < user_limits["requests_per_minute"]


class TestRateLimitMiddleware:
    """Tests for rate limit middleware."""

    def test_get_client_ip_direct(self):
        """Test IP extraction from direct connection."""
        from app.security.rate_limit import get_client_ip

        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"

        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_forwarded(self):
        """Test IP extraction from X-Forwarded-For."""
        from app.security.rate_limit import get_client_ip

        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}

        ip = get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_real_ip(self):
        """Test IP extraction from X-Real-IP."""
        from app.security.rate_limit import get_client_ip

        request = MagicMock()
        request.headers = {"X-Real-IP": "10.0.0.2"}

        ip = get_client_ip(request)
        assert ip == "10.0.0.2"


class TestFileValidation:
    """Tests for file upload validation."""

    def test_validate_file_upload_valid_pdf(self):
        """Test valid PDF upload."""
        from app.security.validation import validate_file_upload

        result = validate_file_upload("document.pdf", "application/pdf", 1024 * 1024)
        assert result is True

    def test_validate_file_upload_invalid_extension(self):
        """Test invalid file extension."""
        from app.security.validation import validate_file_upload
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            validate_file_upload("script.exe", "application/octet-stream", 1024)
        assert exc.value.status_code == 400

    def test_validate_file_upload_too_large(self):
        """Test file size limit."""
        from app.security.validation import validate_file_upload
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            validate_file_upload("large.pdf", "application/pdf", 100 * 1024 * 1024)
        assert exc.value.status_code == 400
        assert "too large" in str(exc.value.detail).lower()

    def test_validate_file_upload_path_traversal(self):
        """Test path traversal in filename."""
        from app.security.validation import validate_file_upload
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            validate_file_upload("../../../etc/passwd.pdf", "application/pdf", 1024)
        assert exc.value.status_code == 400
