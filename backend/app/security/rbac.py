"""Role-Based Access Control (RBAC) for enterprise security."""

from enum import Enum
from typing import Optional, Dict, List, Set, Callable
from functools import wraps
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings


class Role(str, Enum):
    """User roles with hierarchical permissions."""

    ANONYMOUS = "anonymous"  # Unauthenticated users
    USER = "user"           # Basic authenticated users
    PREMIUM = "premium"     # Premium users with extended limits
    ADMIN = "admin"         # Administrators
    SUPERADMIN = "superadmin"  # Super administrators


class Permission(str, Enum):
    """Granular permissions for access control."""

    # Chat permissions
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    CHAT_STREAM = "chat:stream"
    CHAT_UNLIMITED = "chat:unlimited"

    # Document permissions
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_WRITE = "documents:write"
    DOCUMENTS_DELETE = "documents:delete"
    DOCUMENTS_UPLOAD = "documents:upload"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_LOGS = "admin:logs"
    ADMIN_RATE_LIMITS = "admin:rate_limits"

    # API permissions
    API_FULL_ACCESS = "api:full_access"
    API_EXTERNAL = "api:external"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ANONYMOUS: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.DOCUMENTS_READ,
    },
    Role.USER: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_STREAM,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_WRITE,
        Permission.DOCUMENTS_UPLOAD,
    },
    Role.PREMIUM: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_STREAM,
        Permission.CHAT_UNLIMITED,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_WRITE,
        Permission.DOCUMENTS_DELETE,
        Permission.DOCUMENTS_UPLOAD,
        Permission.API_EXTERNAL,
    },
    Role.ADMIN: {
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_STREAM,
        Permission.CHAT_UNLIMITED,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_WRITE,
        Permission.DOCUMENTS_DELETE,
        Permission.DOCUMENTS_UPLOAD,
        Permission.ADMIN_USERS,
        Permission.ADMIN_LOGS,
        Permission.ADMIN_RATE_LIMITS,
        Permission.API_EXTERNAL,
    },
    Role.SUPERADMIN: {
        # All permissions
        permission for permission in Permission
    },
}

# Rate limits per role
ROLE_RATE_LIMITS: Dict[Role, Dict[str, int]] = {
    Role.ANONYMOUS: {
        "requests_per_minute": 10,
        "requests_per_hour": 50,
        "requests_per_day": 200,
    },
    Role.USER: {
        "requests_per_minute": 20,
        "requests_per_hour": 200,
        "requests_per_day": 2000,
    },
    Role.PREMIUM: {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "requests_per_day": 10000,
    },
    Role.ADMIN: {
        "requests_per_minute": 120,
        "requests_per_hour": 2000,
        "requests_per_day": 20000,
    },
    Role.SUPERADMIN: {
        "requests_per_minute": 1000,
        "requests_per_hour": 10000,
        "requests_per_day": 100000,
    },
}


security = HTTPBearer(auto_error=False)


def get_role_from_user(user: Optional[Dict]) -> Role:
    """
    Determine user role from user data.

    Args:
        user: User data from authentication

    Returns:
        User's role
    """
    if not user:
        return Role.ANONYMOUS

    # Check for role in user metadata
    user_role = user.get("role", "authenticated")
    email = user.get("email", "")

    # Map Supabase roles to our roles
    if user_role == "service_role":
        return Role.SUPERADMIN

    # Check for admin emails (configure in settings)
    admin_emails = getattr(settings, 'admin_emails', [])
    if email in admin_emails:
        return Role.ADMIN

    # Check for premium status in user metadata
    metadata = user.get("user_metadata", {})
    if metadata.get("premium", False):
        return Role.PREMIUM

    return Role.USER


def get_permissions_for_role(role: Role) -> Set[Permission]:
    """
    Get all permissions for a role.

    Args:
        role: User role

    Returns:
        Set of permissions
    """
    return ROLE_PERMISSIONS.get(role, set())


def check_permission(user: Optional[Dict], permission: Permission) -> bool:
    """
    Check if user has a specific permission.

    Args:
        user: User data
        permission: Permission to check

    Returns:
        True if user has permission
    """
    role = get_role_from_user(user)
    permissions = get_permissions_for_role(role)
    return permission in permissions


def get_rate_limits_for_user(user: Optional[Dict]) -> Dict[str, int]:
    """
    Get rate limits for user based on their role.

    Args:
        user: User data

    Returns:
        Rate limit configuration
    """
    role = get_role_from_user(user)
    return ROLE_RATE_LIMITS.get(role, ROLE_RATE_LIMITS[Role.ANONYMOUS])


async def get_current_user_with_role(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    Get current user with role information.

    Returns user dict with 'role' field populated.
    """
    from app.services.auth import auth_service

    if not credentials:
        return {"role": Role.ANONYMOUS, "id": None, "email": None}

    user = await auth_service.verify_token(credentials.credentials)

    if not user:
        return {"role": Role.ANONYMOUS, "id": None, "email": None}

    user["role"] = get_role_from_user(user)
    return user


def require_permission(permission: Permission):
    """
    Decorator to require a specific permission.

    Usage:
        @router.get("/admin")
        @require_permission(Permission.ADMIN_USERS)
        async def admin_endpoint(user = Depends(get_current_user_with_role)):
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (injected by Depends)
            user = kwargs.get("user") or kwargs.get("current_user")

            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            if not check_permission(user, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission.value}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(minimum_role: Role):
    """
    Decorator to require a minimum role level.

    Usage:
        @router.get("/premium")
        @require_role(Role.PREMIUM)
        async def premium_endpoint(user = Depends(get_current_user_with_role)):
            pass
    """
    # Role hierarchy (higher index = more permissions)
    ROLE_HIERARCHY = [Role.ANONYMOUS, Role.USER, Role.PREMIUM, Role.ADMIN, Role.SUPERADMIN]

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user") or kwargs.get("current_user")

            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            user_role = user.get("role", Role.ANONYMOUS)
            if isinstance(user_role, str):
                try:
                    user_role = Role(user_role)
                except ValueError:
                    user_role = Role.USER

            user_level = ROLE_HIERARCHY.index(user_role) if user_role in ROLE_HIERARCHY else 0
            required_level = ROLE_HIERARCHY.index(minimum_role)

            if user_level < required_level:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role '{minimum_role.value}' or higher required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RBACMiddleware:
    """
    Middleware to attach user role and permissions to request state.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Will be populated by dependency injection
            scope["state"]["user_role"] = Role.ANONYMOUS
            scope["state"]["permissions"] = get_permissions_for_role(Role.ANONYMOUS)

        await self.app(scope, receive, send)
