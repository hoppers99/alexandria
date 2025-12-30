"""Text-to-Speech API endpoints."""

import logging
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from librarian.db.models import Item, SystemSettings, TTSCache
from web.auth.dependencies import CurrentUser, CurrentUserOptional
from web.config import settings
from web.database import get_db
from web.tts.extractors import EPUBExtractor, get_extractor
from web.tts.generator import (
    CHATTERBOX_VOICES,
    COQUI_VOICES,
    DEFAULT_CHATTERBOX_VOICE,
    DEFAULT_COQUI_VOICE,
    list_voices,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])


# =============================================================================
# Settings Helpers
# =============================================================================


def get_setting(db: DBSession, key: str, default: str | None = None) -> str | None:
    """Get a system setting value."""
    stmt = select(SystemSettings).where(SystemSettings.key == key)
    setting = db.execute(stmt).scalar_one_or_none()
    return setting.value if setting else default


def get_tts_config(db: DBSession) -> dict:
    """Get all TTS configuration from database."""
    engine = get_setting(db, "tts.engine", "coqui")
    voice = get_setting(db, "tts.voice", "p225" if engine == "coqui" else "alloy")

    return {
        "engine": engine,
        "voice": voice,
        "exaggeration": float(get_setting(db, "tts.exaggeration", "0.5")),
        "cfg_weight": float(get_setting(db, "tts.cfg_weight", "0.4")),
        "temperature": float(get_setting(db, "tts.temperature", "0.9")),
    }


# =============================================================================
# Request/Response Models
# =============================================================================


class ChapterInfo(BaseModel):
    """Information about a book chapter."""

    number: int
    title: str
    word_count: int
    estimated_duration_seconds: float
    has_audio: bool = False
    audio_duration_seconds: float | None = None
    voice_id: str | None = None


class ChaptersResponse(BaseModel):
    """List of chapters for an item."""

    item_id: int
    title: str
    total_chapters: int
    chapters: list[ChapterInfo]


class VoiceInfo(BaseModel):
    """Voice metadata."""

    voice_id: str
    gender: Literal["male", "female"]
    accent: str
    age: str
    description: str


class VoicesResponse(BaseModel):
    """List of available voices."""

    voices: list[VoiceInfo]
    default_voice: str


class GenerateRequest(BaseModel):
    """Request to generate TTS for a chapter."""

    # Voice is now optional - uses system default if not provided
    voice_id: str | None = Field(default=None, description="Voice ID to use (uses system default if not provided)")


class GenerateResponse(BaseModel):
    """Response for TTS generation request."""

    success: bool
    message: str
    chapter_number: int
    voice_id: str
    estimated_duration_seconds: float | None = None
    task_id: str | None = None  # Celery task ID for tracking


class AudioStatus(BaseModel):
    """Status of audio generation for a chapter."""

    chapter_number: int
    has_audio: bool
    voice_id: str | None = None
    duration_seconds: float | None = None
    file_size_mb: float | None = None
    generated_at: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/voices", response_model=VoicesResponse)
async def get_voices(
    db: Annotated[DBSession, Depends(get_db)],
    gender: Literal["male", "female", "neutral", "all"] = "all",
) -> VoicesResponse:
    """Get list of available TTS voices for the current engine.

    Args:
        db: Database session
        gender: Filter by gender (male, female, neutral, or all)

    Returns:
        List of available voices with metadata
    """
    # Get current engine and voice from settings
    config = get_tts_config(db)
    engine = config["engine"]
    default_voice = config["voice"]

    # Get voices for the current engine
    voices_dict = list_voices(engine, gender)

    voices = [
        VoiceInfo(
            voice_id=vid,
            gender=info.get("gender", "neutral"),
            accent=info.get("accent", "Standard"),
            age=info.get("age", ""),
            description=info["description"],
        )
        for vid, info in voices_dict.items()
    ]

    return VoicesResponse(voices=voices, default_voice=default_voice)


@router.get("/items/{item_id}/chapters", response_model=ChaptersResponse)
async def get_item_chapters(
    item_id: int,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUser,
    voice_id: str | None = None,
) -> ChaptersResponse:
    """Get list of chapters for an item with TTS status.

    Args:
        item_id: Item ID
        db: Database session
        user: Current user
        voice_id: Voice ID to check for cached audio (uses system default if not provided)

    Returns:
        List of chapters with TTS availability status
    """
    # Get system TTS config
    config = get_tts_config(db)
    voice_id = voice_id or config["voice"]

    # Get item
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get first file for the item
    if not item.files:
        raise HTTPException(status_code=400, detail="Item has no files")

    first_file = item.files[0]
    file_path = Path(settings.library_root) / first_file.file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Extract chapters using appropriate extractor
    try:
        extractor = get_extractor(file_path)
        chapters_data = extractor.get_chapters()
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format or extraction error: {e}"
        )

    # Check which chapters have cached audio
    stmt = select(TTSCache).where(
        TTSCache.item_id == item_id, TTSCache.voice_id == voice_id
    )
    cached_audio = {cache.chapter_number: cache for cache in db.execute(stmt).scalars()}

    # Build chapter info list
    chapters = []
    for ch in chapters_data:
        cache = cached_audio.get(ch["number"])
        chapters.append(
            ChapterInfo(
                number=ch["number"],
                title=ch["title"],
                word_count=ch["word_count"],
                estimated_duration_seconds=ch["estimated_duration_seconds"],
                has_audio=cache is not None,
                audio_duration_seconds=cache.duration_seconds if cache else None,
                voice_id=cache.voice_id if cache else None,
            )
        )

    return ChaptersResponse(
        item_id=item_id,
        title=item.title,
        total_chapters=len(chapters),
        chapters=chapters,
    )


@router.post(
    "/items/{item_id}/chapters/{chapter_number}/generate", response_model=GenerateResponse
)
async def generate_chapter_audio(
    item_id: int,
    chapter_number: int,
    request: GenerateRequest,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUser,
) -> GenerateResponse:
    """Generate TTS audio for a specific chapter.

    Args:
        item_id: Item ID
        chapter_number: Chapter number (1-indexed)
        request: Generation request with voice preference
        db: Database session
        user: Current user

    Returns:
        Generation status and task information
    """
    # Get system TTS config
    config = get_tts_config(db)
    voice_id = request.voice_id or config["voice"]

    # Verify item exists
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check if already cached
    stmt = select(TTSCache).where(
        TTSCache.item_id == item_id,
        TTSCache.chapter_number == chapter_number,
        TTSCache.voice_id == voice_id,
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        return GenerateResponse(
            success=True,
            message="Audio already generated",
            chapter_number=chapter_number,
            voice_id=voice_id,
            estimated_duration_seconds=existing.duration_seconds,
        )

    # Get file
    if not item.files:
        raise HTTPException(status_code=400, detail="Item has no files")

    first_file = item.files[0]
    file_path = Path(settings.library_root) / first_file.file_path

    # Extract chapter text
    try:
        extractor = get_extractor(file_path)
        chapter_data = extractor.get_chapter(chapter_number)

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate audio using system-configured TTS engine
    try:
        from web.tts.generator import TTSGenerator

        # Initialize generator with system settings
        coqui_url = os.environ.get("COQUI_TTS_URL", "http://localhost:5002")
        chatterbox_url = os.environ.get("CHATTERBOX_TTS_URL", "http://localhost:4123")
        cache_dir = Path(settings.library_root) / "tts-cache" / str(item_id)
        cache_dir.mkdir(parents=True, exist_ok=True)

        generator = TTSGenerator(
            engine=config["engine"],
            coqui_url=coqui_url,
            chatterbox_url=chatterbox_url,
            cache_dir=cache_dir,
            exaggeration=config["exaggeration"],
            cfg_weight=config["cfg_weight"],
            temperature=config["temperature"],
        )

        # Generate audio
        output_path = cache_dir / f"ch{chapter_number}_{voice_id}.mp3"

        file_path_result, duration = generator.generate_chapter(
            text=chapter_data["text"],
            voice=voice_id,
            output_path=output_path,
        )

        # Save to cache database
        tts_cache = TTSCache(
            item_id=item_id,
            chapter_number=chapter_number,
            voice_id=voice_id,
            file_path=str(file_path_result.relative_to(settings.library_root)),
            duration_seconds=duration,
            file_size_bytes=file_path_result.stat().st_size,
        )
        db.add(tts_cache)
        db.commit()

        return GenerateResponse(
            success=True,
            message="Audio generated successfully",
            chapter_number=chapter_number,
            voice_id=voice_id,
            estimated_duration_seconds=duration,
        )

    except Exception as e:
        logger.error(f"Error generating TTS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/items/{item_id}/chapters/{chapter_number}/audio")
async def stream_chapter_audio(
    item_id: int,
    chapter_number: int,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUser,
    voice_id: str | None = None,
) -> FileResponse:
    """Stream generated audio for a chapter.

    Args:
        item_id: Item ID
        chapter_number: Chapter number
        db: Database session
        user: Current user
        voice_id: Voice ID (uses system default if not provided)

    Returns:
        Audio file stream
    """
    # Get system TTS config
    config = get_tts_config(db)
    voice_id = voice_id or config["voice"]

    # Get cached audio
    stmt = select(TTSCache).where(
        TTSCache.item_id == item_id,
        TTSCache.chapter_number == chapter_number,
        TTSCache.voice_id == voice_id,
    )
    cache = db.execute(stmt).scalar_one_or_none()

    if not cache:
        raise HTTPException(
            status_code=404, detail="Audio not generated yet. Generate it first."
        )

    # Get file path
    audio_path = Path(settings.library_root) / cache.file_path

    if not audio_path.exists():
        # Cache entry exists but file is missing - clean up cache
        db.delete(cache)
        db.commit()
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Return file
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"chapter_{chapter_number}.mp3",
    )


@router.get("/items/{item_id}/chapters/{chapter_number}/status", response_model=AudioStatus)
async def get_chapter_audio_status(
    item_id: int,
    chapter_number: int,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUser,
    voice_id: str | None = None,
) -> AudioStatus:
    """Check if audio is available for a chapter.

    Args:
        item_id: Item ID
        chapter_number: Chapter number
        db: Database session
        user: Current user
        voice_id: Voice ID to check (uses system default if not provided)

    Returns:
        Audio availability status
    """
    # Get system TTS config
    config = get_tts_config(db)
    voice_id = voice_id or config["voice"]

    stmt = select(TTSCache).where(
        TTSCache.item_id == item_id,
        TTSCache.chapter_number == chapter_number,
        TTSCache.voice_id == voice_id,
    )
    cache = db.execute(stmt).scalar_one_or_none()

    if not cache:
        return AudioStatus(chapter_number=chapter_number, has_audio=False)

    return AudioStatus(
        chapter_number=chapter_number,
        has_audio=True,
        voice_id=cache.voice_id,
        duration_seconds=cache.duration_seconds,
        file_size_mb=cache.file_size_bytes / (1024 * 1024) if cache.file_size_bytes else None,
        generated_at=cache.generated_at.isoformat(),
    )


@router.delete("/items/{item_id}/chapters/{chapter_number}/audio")
async def delete_chapter_audio(
    item_id: int,
    chapter_number: int,
    db: Annotated[DBSession, Depends(get_db)],
    user: CurrentUser,
    voice_id: str | None = None,
) -> dict:
    """Delete cached audio for a chapter.

    Args:
        item_id: Item ID
        chapter_number: Chapter number
        db: Database session
        user: Current user
        voice_id: Voice ID (uses system default if not provided)

    Returns:
        Success message
    """
    # Only admins can delete cached audio
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get system TTS config
    config = get_tts_config(db)
    voice_id = voice_id or config["voice"]

    stmt = select(TTSCache).where(
        TTSCache.item_id == item_id,
        TTSCache.chapter_number == chapter_number,
        TTSCache.voice_id == voice_id,
    )
    cache = db.execute(stmt).scalar_one_or_none()

    if not cache:
        raise HTTPException(status_code=404, detail="Audio not found")

    # Delete file
    audio_path = Path(settings.library_root) / cache.file_path
    if audio_path.exists():
        audio_path.unlink()

    # Delete cache entry
    db.delete(cache)
    db.commit()

    return {"success": True, "message": "Audio deleted successfully"}


@router.post("/preview")
async def preview_voice(
    text: str,
    db: Annotated[DBSession, Depends(get_db)],
    voice_id: str | None = None,
    user: CurrentUserOptional = None,
) -> StreamingResponse:
    """Generate a short preview of a voice.

    Args:
        text: Sample text to synthesize (first ~500 chars)
        db: Database session
        voice_id: Voice ID (uses system default if not provided)
        user: Current user (optional)

    Returns:
        Audio preview stream
    """
    # Get system TTS config
    config = get_tts_config(db)
    engine = config["engine"]
    voice_id = voice_id or config["voice"]

    # Validate voice for current engine
    available_voices = CHATTERBOX_VOICES if engine == "chatterbox" else COQUI_VOICES
    if voice_id not in available_voices:
        raise HTTPException(status_code=400, detail=f"Invalid voice ID for engine {engine}")

    try:
        from web.tts.generator import TTSGenerator

        coqui_url = os.environ.get("COQUI_TTS_URL", "http://localhost:5002")
        chatterbox_url = os.environ.get("CHATTERBOX_TTS_URL", "http://localhost:4123")

        generator = TTSGenerator(
            engine=engine,
            coqui_url=coqui_url,
            chatterbox_url=chatterbox_url,
            exaggeration=config["exaggeration"],
            cfg_weight=config["cfg_weight"],
            temperature=config["temperature"],
        )

        # Generate preview (async)
        audio_data, duration = await generator.generate_preview_async(text, voice_id)

        # Return as streaming response
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"inline; filename=preview_{voice_id}.wav",
                "X-Audio-Duration": str(duration),
            },
        )

    except Exception as e:
        logger.error(f"Error generating preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")
