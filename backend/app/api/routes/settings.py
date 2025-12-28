"""User settings endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from app.services.supabase import supabase_service
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class UserSettings(BaseModel):
    """User settings model."""
    theme: str = "light"
    soundEnabled: bool = True
    notificationsEnabled: bool = True
    streamingSpeed: str = "medium"


class SettingsResponse(BaseModel):
    """Settings response model."""
    success: bool
    settings: Optional[UserSettings] = None
    message: Optional[str] = None


async def get_user_from_token(authorization: str = Header(None)) -> Optional[str]:
    """Extract user ID from authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    try:
        # Verify the token with Supabase
        from supabase import create_client
        from app.config import settings

        client = create_client(settings.supabase_url, settings.supabase_anon_key)
        user = client.auth.get_user(token)
        if user and user.user:
            return user.user.id
    except Exception as e:
        logger.error(f"Token verification failed: {e}")

    return None


@router.get("", response_model=SettingsResponse)
async def get_settings(authorization: str = Header(None)):
    """Get user settings."""
    user_id = await get_user_from_token(authorization)

    if not user_id:
        # Return default settings for anonymous users
        return SettingsResponse(
            success=True,
            settings=UserSettings(),
            message="Using default settings (not logged in)"
        )

    try:
        settings_data = await supabase_service.get_user_settings(user_id)

        if settings_data:
            return SettingsResponse(
                success=True,
                settings=UserSettings(
                    theme=settings_data.get("theme", "light"),
                    soundEnabled=settings_data.get("sound_enabled", True),
                    notificationsEnabled=settings_data.get("notifications_enabled", True),
                    streamingSpeed=settings_data.get("streaming_speed", "medium"),
                )
            )
        else:
            # No settings found, return defaults
            return SettingsResponse(
                success=True,
                settings=UserSettings(),
                message="No settings found, using defaults"
            )
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        return SettingsResponse(
            success=False,
            settings=UserSettings(),
            message=str(e)
        )


@router.post("", response_model=SettingsResponse)
async def save_settings(
    settings: UserSettings,
    authorization: str = Header(None)
):
    """Save user settings."""
    user_id = await get_user_from_token(authorization)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to save settings"
        )

    try:
        await supabase_service.upsert_user_settings(
            user_id=user_id,
            settings={
                "theme": settings.theme,
                "soundEnabled": settings.soundEnabled,
                "notificationsEnabled": settings.notificationsEnabled,
                "streamingSpeed": settings.streamingSpeed,
            }
        )

        return SettingsResponse(
            success=True,
            settings=settings,
            message="Settings saved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
