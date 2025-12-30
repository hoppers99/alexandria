"""Admin settings API endpoints."""

import logging
import os
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from librarian.db.models import SystemSettings
from web.auth.dependencies import CurrentAdmin
from web.database import get_db
from web.tts.generator import CHATTERBOX_VOICES, COQUI_VOICES, list_voices

logger = logging.getLogger(__name__)

# TTS service URLs from environment
COQUI_TTS_URL = os.environ.get("COQUI_TTS_URL", "http://localhost:5002")
CHATTERBOX_TTS_URL = os.environ.get("CHATTERBOX_TTS_URL", "http://localhost:4123")

router = APIRouter(prefix="/api/admin/settings", tags=["admin", "settings"])


# =============================================================================
# Request/Response Models
# =============================================================================


class TTSSettingsResponse(BaseModel):
    """TTS configuration settings."""

    engine: Literal["coqui", "chatterbox"]
    voice: str
    exaggeration: float = Field(ge=0.25, le=2.0)
    cfg_weight: float = Field(ge=0.0, le=1.0)
    temperature: float = Field(ge=0.05, le=5.0)


class TTSSettingsUpdate(BaseModel):
    """Update TTS configuration."""

    engine: Literal["coqui", "chatterbox"] | None = None
    voice: str | None = None
    exaggeration: float | None = Field(None, ge=0.25, le=2.0)
    cfg_weight: float | None = Field(None, ge=0.0, le=1.0)
    temperature: float | None = Field(None, ge=0.05, le=5.0)


class VoiceInfo(BaseModel):
    """Voice metadata for UI."""

    voice_id: str
    description: str
    gender: str | None = None
    accent: str | None = None
    age: str | None = None


class AvailableVoicesResponse(BaseModel):
    """Available voices for the current engine."""

    engine: Literal["coqui", "chatterbox"]
    voices: list[VoiceInfo]


class EngineStatus(BaseModel):
    """Status of a TTS engine."""

    engine: Literal["coqui", "chatterbox"]
    available: bool
    error: str | None = None


class TTSAvailabilityResponse(BaseModel):
    """Availability status of all TTS engines."""

    engines: list[EngineStatus]


# =============================================================================
# Helper Functions
# =============================================================================


def get_setting(db: DBSession, key: str, default: str | None = None) -> str | None:
    """Get a system setting value."""
    stmt = select(SystemSettings).where(SystemSettings.key == key)
    setting = db.execute(stmt).scalar_one_or_none()
    return setting.value if setting else default


def set_setting(db: DBSession, key: str, value: str) -> None:
    """Set a system setting value."""
    stmt = select(SystemSettings).where(SystemSettings.key == key)
    setting = db.execute(stmt).scalar_one_or_none()

    if setting:
        setting.value = value
    else:
        setting = SystemSettings(key=key, value=value)
        db.add(setting)

    db.commit()


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/tts", response_model=TTSSettingsResponse)
async def get_tts_settings(
    db: Annotated[DBSession, Depends(get_db)],
    admin: CurrentAdmin,
) -> TTSSettingsResponse:
    """Get current TTS configuration (admin only).

    Args:
        db: Database session
        admin: Current admin user

    Returns:
        Current TTS settings
    """
    engine = get_setting(db, "tts.engine", "chatterbox")
    voice = get_setting(db, "tts.voice", "alloy")
    exaggeration = float(get_setting(db, "tts.exaggeration", "0.5"))
    cfg_weight = float(get_setting(db, "tts.cfg_weight", "0.4"))
    temperature = float(get_setting(db, "tts.temperature", "0.9"))

    return TTSSettingsResponse(
        engine=engine,  # type: ignore
        voice=voice,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        temperature=temperature,
    )


@router.patch("/tts", response_model=TTSSettingsResponse)
async def update_tts_settings(
    update: TTSSettingsUpdate,
    db: Annotated[DBSession, Depends(get_db)],
    admin: CurrentAdmin,
) -> TTSSettingsResponse:
    """Update TTS configuration (admin only).

    Args:
        update: Settings to update
        db: Database session
        admin: Current admin user

    Returns:
        Updated TTS settings
    """
    # Get current settings
    current_engine = get_setting(db, "tts.engine", "chatterbox")
    current_voice = get_setting(db, "tts.voice", "alloy")

    # Update engine if provided
    if update.engine is not None:
        set_setting(db, "tts.engine", update.engine)
        current_engine = update.engine

        # If engine changed, validate and potentially change voice
        if update.voice is None:
            # Reset to default voice for new engine
            voices = CHATTERBOX_VOICES if update.engine == "chatterbox" else COQUI_VOICES
            if current_voice not in voices:
                current_voice = "alloy" if update.engine == "chatterbox" else "p225"
                set_setting(db, "tts.voice", current_voice)

    # Update voice if provided
    if update.voice is not None:
        # Validate voice exists for current engine
        voices = CHATTERBOX_VOICES if current_engine == "chatterbox" else COQUI_VOICES
        if update.voice not in voices:
            raise HTTPException(
                status_code=400,
                detail=f"Voice '{update.voice}' not available for engine '{current_engine}'",
            )
        set_setting(db, "tts.voice", update.voice)

    # Update Chatterbox parameters if provided
    if update.exaggeration is not None:
        set_setting(db, "tts.exaggeration", str(update.exaggeration))

    if update.cfg_weight is not None:
        set_setting(db, "tts.cfg_weight", str(update.cfg_weight))

    if update.temperature is not None:
        set_setting(db, "tts.temperature", str(update.temperature))

    # Return updated settings
    return await get_tts_settings(db, admin)


@router.get("/tts/voices", response_model=AvailableVoicesResponse)
async def get_available_voices(
    db: Annotated[DBSession, Depends(get_db)],
    admin: CurrentAdmin,
    engine: Literal["coqui", "chatterbox"] | None = None,
) -> AvailableVoicesResponse:
    """Get available voices for the current or specified engine (admin only).

    Args:
        db: Database session
        admin: Current admin user
        engine: Engine to get voices for (defaults to current engine)

    Returns:
        List of available voices
    """
    # Get current engine if not specified
    if engine is None:
        engine = get_setting(db, "tts.engine", "chatterbox")  # type: ignore

    # Get voices for the engine
    voices_dict = list_voices(engine, gender="all")  # type: ignore

    # Convert to response format
    voices = [
        VoiceInfo(
            voice_id=vid,
            description=info["description"],
            gender=info.get("gender"),
            accent=info.get("accent"),
            age=info.get("age"),
        )
        for vid, info in voices_dict.items()
    ]

    return AvailableVoicesResponse(engine=engine, voices=voices)  # type: ignore


@router.get("/tts/availability", response_model=TTSAvailabilityResponse)
async def get_tts_availability(
    admin: CurrentAdmin,
) -> TTSAvailabilityResponse:
    """Check which TTS engines are available (admin only).

    Tests connectivity to each TTS service and returns their status.

    Args:
        admin: Current admin user

    Returns:
        Availability status of each TTS engine
    """
    engines: list[EngineStatus] = []

    # Check Coqui TTS
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Coqui TTS has a /api/tts endpoint, but we can just check if the server responds
            response = await client.get(f"{COQUI_TTS_URL}/")
            # Any response means the server is running
            engines.append(EngineStatus(engine="coqui", available=True))
    except httpx.ConnectError:
        engines.append(EngineStatus(
            engine="coqui",
            available=False,
            error="Service not running"
        ))
    except httpx.TimeoutException:
        engines.append(EngineStatus(
            engine="coqui",
            available=False,
            error="Service timeout"
        ))
    except Exception as e:
        engines.append(EngineStatus(
            engine="coqui",
            available=False,
            error=str(e)
        ))

    # Check Chatterbox TTS
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Chatterbox has an OpenAI-compatible API, check the models endpoint
            response = await client.get(f"{CHATTERBOX_TTS_URL}/v1/models")
            if response.status_code == 200:
                engines.append(EngineStatus(engine="chatterbox", available=True))
            else:
                engines.append(EngineStatus(
                    engine="chatterbox",
                    available=False,
                    error=f"HTTP {response.status_code}"
                ))
    except httpx.ConnectError:
        engines.append(EngineStatus(
            engine="chatterbox",
            available=False,
            error="Service not running"
        ))
    except httpx.TimeoutException:
        engines.append(EngineStatus(
            engine="chatterbox",
            available=False,
            error="Service timeout"
        ))
    except Exception as e:
        engines.append(EngineStatus(
            engine="chatterbox",
            available=False,
            error=str(e)
        ))

    return TTSAvailabilityResponse(engines=engines)
