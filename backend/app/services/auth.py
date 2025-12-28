"""Authentication service using Supabase Auth."""

import logging
from typing import Optional, Dict
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from supabase import create_client

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthService:
    """Handle authentication with Supabase."""

    def __init__(self):
        self.client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )

    async def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify a JWT token and return user data.

        Args:
            token: JWT access token

        Returns:
            User data or None if invalid
        """
        try:
            # Verify the token with Supabase
            response = self.client.auth.get_user(token)

            if response and response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "role": response.user.role,
                    "created_at": str(response.user.created_at) if response.user.created_at else None,
                }

            return None

        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile from profiles table."""
        try:
            response = self.client.table("profiles").select("*").eq("id", user_id).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Get profile error: {e}")
            return None

    async def create_user_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        preferences: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Create or update user profile."""
        try:
            data = {
                "id": user_id,
                "display_name": display_name,
                "preferences": preferences or {}
            }

            response = self.client.table("profiles").upsert(data).execute()
            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Create profile error: {e}")
            return None


# Singleton instance
auth_service = AuthService()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict]:
    """
    FastAPI dependency to get current authenticated user.

    Returns None for unauthenticated requests (allows anonymous access).
    """
    if not credentials:
        return None

    user = await auth_service.verify_token(credentials.credentials)
    return user


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    FastAPI dependency that requires authentication.

    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = await auth_service.verify_token(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


class UserThreadService:
    """Manage user-specific conversation threads."""

    def __init__(self):
        self.client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )

    async def get_user_threads(
        self,
        user_id: str,
        limit: int = 20
    ) -> list:
        """Get all threads for a user."""
        try:
            response = (
                self.client.table("threads")
                .select("id, title, created_at, updated_at")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []

        except Exception as e:
            logger.error(f"Get user threads error: {e}")
            return []

    async def create_user_thread(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> Optional[Dict]:
        """Create a new thread for a user."""
        try:
            response = (
                self.client.table("threads")
                .insert({"user_id": user_id, "title": title})
                .execute()
            )
            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Create user thread error: {e}")
            return None

    async def delete_user_thread(
        self,
        user_id: str,
        thread_id: str
    ) -> bool:
        """Delete a thread (only if owned by user)."""
        try:
            response = (
                self.client.table("threads")
                .delete()
                .eq("id", thread_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(response.data) > 0

        except Exception as e:
            logger.error(f"Delete user thread error: {e}")
            return False

    async def get_thread_with_messages(
        self,
        user_id: str,
        thread_id: str
    ) -> Optional[Dict]:
        """Get a thread with all its messages (only if owned by user)."""
        try:
            # Get thread
            thread_response = (
                self.client.table("threads")
                .select("*")
                .eq("id", thread_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            if not thread_response.data:
                return None

            # Get messages
            messages_response = (
                self.client.table("messages")
                .select("*")
                .eq("thread_id", thread_id)
                .order("created_at")
                .execute()
            )

            return {
                "thread": thread_response.data,
                "messages": messages_response.data or []
            }

        except Exception as e:
            logger.error(f"Get thread with messages error: {e}")
            return None


# Singleton instance
user_thread_service = UserThreadService()
