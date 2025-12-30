"""TTS audio generation using Coqui TTS or Chatterbox via HTTP API."""

import io
import logging
import re
from pathlib import Path
from typing import Callable, Literal

import httpx

logger = logging.getLogger(__name__)


# Available voices in VCTK model (Coqui)
# Gender labels verified by user testing
COQUI_VOICES = {
    "p225": {
        "gender": "female",
        "accent": "English",
        "age": "23",
        "description": "Female, English accent",
    },
    "p226": {
        "gender": "male",
        "accent": "English",
        "age": "22",
        "description": "Male, English accent",
    },
    "p227": {
        "gender": "female",
        "accent": "English",
        "age": "38",
        "description": "Female, English accent (mature voice)",
    },
    "p228": {
        "gender": "male",
        "accent": "English",
        "age": "22",
        "description": "Male, English accent",
    },
    "p229": {
        "gender": "male",
        "accent": "English",
        "age": "23",
        "description": "Male, English accent",
    },
    "p230": {
        "gender": "male",
        "accent": "English",
        "age": "22",
        "description": "Male, English accent",
    },
    "p231": {
        "gender": "male",
        "accent": "English",
        "age": "23",
        "description": "Male, English accent",
    },
    "p232": {
        "gender": "male",
        "accent": "English",
        "age": "23",
        "description": "Male, English accent",
    },
    "p233": {
        "gender": "male",
        "accent": "English",
        "age": "23",
        "description": "Male, English accent",
    },
    "p234": {
        "gender": "male",
        "accent": "Scottish",
        "age": "22",
        "description": "Male, Scottish accent",
    },
}

# Available voices in Chatterbox (OpenAI-compatible names)
CHATTERBOX_VOICES = {
    "alloy": {
        "gender": "neutral",
        "description": "Neutral, balanced voice",
    },
    "echo": {
        "gender": "male",
        "description": "Male, clear and articulate",
    },
    "fable": {
        "gender": "male",
        "description": "Male, warm and expressive",
    },
    "onyx": {
        "gender": "male",
        "description": "Male, deep and authoritative",
    },
    "nova": {
        "gender": "female",
        "description": "Female, warm and friendly",
    },
    "shimmer": {
        "gender": "female",
        "description": "Female, bright and energetic",
    },
}

# Default voices per engine
DEFAULT_COQUI_VOICE = "p225"
DEFAULT_CHATTERBOX_VOICE = "alloy"

# For backwards compatibility
AVAILABLE_VOICES = COQUI_VOICES
DEFAULT_VOICE = DEFAULT_COQUI_VOICE


class TTSGenerator:
    """Generate high-quality TTS audio using Coqui TTS or Chatterbox HTTP API."""

    def __init__(
        self,
        engine: Literal["coqui", "chatterbox"] = "chatterbox",
        coqui_url: str = "http://localhost:5002",
        chatterbox_url: str = "http://localhost:4123",
        cache_dir: Path | None = None,
        # Chatterbox parameters
        exaggeration: float = 0.5,
        cfg_weight: float = 0.4,
        temperature: float = 0.9,
    ):
        """Initialize TTS generator.

        Args:
            engine: TTS engine to use ("coqui" or "chatterbox")
            coqui_url: URL of Coqui TTS service
            chatterbox_url: URL of Chatterbox TTS service
            cache_dir: Directory to cache generated audio
            exaggeration: Emotion intensity for Chatterbox (0.25-2.0)
            cfg_weight: Pace control for Chatterbox (0.0-1.0)
            temperature: Sampling variance for Chatterbox (0.05-5.0)
        """
        self.engine = engine
        self.coqui_url = coqui_url.rstrip("/")
        self.chatterbox_url = chatterbox_url.rstrip("/")
        self.cache_dir = cache_dir or Path("/tmp/tts-cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=300.0)  # 5 minute timeout for long generations

        # Chatterbox parameters
        self.exaggeration = max(0.25, min(2.0, exaggeration))
        self.cfg_weight = max(0.0, min(1.0, cfg_weight))
        self.temperature = max(0.05, min(5.0, temperature))

    async def generate_chapter_async(
        self,
        text: str,
        voice: str | None = None,
        output_path: Path | str | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> tuple[Path, float]:
        """Generate audio for a chapter (async version).

        Args:
            text: Cleaned chapter text
            voice: Voice ID (engine-specific). If None, uses engine default.
            output_path: Where to save the audio file (MP3/WAV)
            progress_callback: Optional callback for progress updates (0.0 to 1.0)

        Returns:
            Tuple of (output_file_path, duration_seconds)
        """
        if self.engine == "chatterbox":
            return await self._generate_chatterbox_async(
                text, voice, output_path, progress_callback
            )
        else:
            return await self._generate_coqui_async(
                text, voice, output_path, progress_callback
            )

    async def _generate_chatterbox_async(
        self,
        text: str,
        voice: str | None,
        output_path: Path | str | None,
        progress_callback: Callable[[float], None] | None,
    ) -> tuple[Path, float]:
        """Generate audio using Chatterbox TTS."""
        voice = voice or DEFAULT_CHATTERBOX_VOICE

        if voice not in CHATTERBOX_VOICES:
            logger.warning(
                f"Unknown voice {voice}, using default {DEFAULT_CHATTERBOX_VOICE}"
            )
            voice = DEFAULT_CHATTERBOX_VOICE

        # Create output path if not provided
        if output_path is None:
            output_path = self.cache_dir / f"chapter_{voice}.wav"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Split into sentences for better processing and progress tracking
        sentences = self._split_into_sentences(text)
        total_sentences = len(sentences)

        logger.info(
            f"Generating audio for {total_sentences} sentences with Chatterbox voice {voice}"
        )

        audio_parts = []
        total_duration = 0.0

        # Use async httpx client
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Generate audio for each sentence
            for i, sentence in enumerate(sentences):
                # Skip very short sentences (likely fragments)
                if len(sentence.strip()) < 10:
                    continue

                try:
                    # Call Chatterbox API (OpenAI-compatible)
                    response = await client.post(
                        f"{self.chatterbox_url}/v1/audio/speech",
                        json={
                            "input": sentence,
                            "voice": voice,
                            "exaggeration": self.exaggeration,
                            "cfg_weight": self.cfg_weight,
                            "temperature": self.temperature,
                        },
                    )
                    response.raise_for_status()

                    # Get WAV audio data
                    audio_data = response.content
                    audio_parts.append(audio_data)

                    # Estimate duration (rough - WAV header + data)
                    total_duration += len(sentence.split()) / 2.5  # ~150 wpm

                    # Update progress
                    if progress_callback:
                        progress = (i + 1) / total_sentences
                        await progress_callback(progress)

                    # Log progress every 10%
                    if (i + 1) % max(1, total_sentences // 10) == 0:
                        logger.info(f"Progress: {i + 1}/{total_sentences} sentences")

                except Exception as e:
                    logger.error(f"Error generating audio for sentence {i}: {e}")
                    # Continue with next sentence rather than failing entirely
                    continue

        if not audio_parts:
            raise ValueError("No audio generated - all sentences failed")

        # Combine audio parts and save
        final_path = await self._combine_audio_parts(audio_parts, output_path)

        # Get actual duration from file
        duration_seconds = self._get_audio_duration(final_path)

        logger.info(
            f"Generated audio: {final_path} ({duration_seconds:.1f}s, "
            f"{final_path.stat().st_size / 1024 / 1024:.1f}MB)"
        )

        return final_path, duration_seconds

    async def _generate_coqui_async(
        self,
        text: str,
        voice: str | None,
        output_path: Path | str | None,
        progress_callback: Callable[[float], None] | None,
    ) -> tuple[Path, float]:
        """Generate audio using Coqui TTS (original implementation)."""
        voice = voice or DEFAULT_COQUI_VOICE

        if voice not in COQUI_VOICES:
            logger.warning(
                f"Unknown voice {voice}, using default {DEFAULT_COQUI_VOICE}"
            )
            voice = DEFAULT_COQUI_VOICE

        # Create output path if not provided
        if output_path is None:
            output_path = self.cache_dir / f"chapter_{voice}.wav"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Split into sentences for better processing and progress tracking
        sentences = self._split_into_sentences(text)
        total_sentences = len(sentences)

        logger.info(
            f"Generating audio for {total_sentences} sentences with Coqui voice {voice}"
        )

        audio_parts = []
        total_duration = 0.0

        # Use async httpx client
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Generate audio for each sentence
            for i, sentence in enumerate(sentences):
                # Skip very short sentences (likely fragments)
                if len(sentence.strip()) < 10:
                    continue

                try:
                    # Call Coqui TTS API (expects query parameters)
                    response = await client.post(
                        f"{self.coqui_url}/api/tts",
                        params={
                            "text": sentence,
                            "speaker_id": voice,
                        },
                    )
                    response.raise_for_status()

                    # Get WAV audio data
                    audio_data = response.content
                    audio_parts.append(audio_data)

                    # Estimate duration (rough - WAV header + data)
                    total_duration += len(sentence.split()) / 2.5  # ~150 wpm

                    # Update progress
                    if progress_callback:
                        progress = (i + 1) / total_sentences
                        await progress_callback(progress)

                    # Log progress every 10%
                    if (i + 1) % max(1, total_sentences // 10) == 0:
                        logger.info(f"Progress: {i + 1}/{total_sentences} sentences")

                except Exception as e:
                    logger.error(f"Error generating audio for sentence {i}: {e}")
                    # Continue with next sentence rather than failing entirely
                    continue

        if not audio_parts:
            raise ValueError("No audio generated - all sentences failed")

        # Combine audio parts and save
        final_path = await self._combine_audio_parts(audio_parts, output_path)

        # Get actual duration from file
        duration_seconds = self._get_audio_duration(final_path)

        logger.info(
            f"Generated audio: {final_path} ({duration_seconds:.1f}s, "
            f"{final_path.stat().st_size / 1024 / 1024:.1f}MB)"
        )

        return final_path, duration_seconds

    def generate_chapter(
        self,
        text: str,
        voice: str | None = None,
        output_path: Path | str | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> tuple[Path, float]:
        """Generate audio for a chapter (sync version).

        Args:
            text: Cleaned chapter text
            voice: Voice ID (engine-specific)
            output_path: Where to save the audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (output_file_path, duration_seconds)
        """
        import asyncio

        return asyncio.run(
            self.generate_chapter_async(text, voice, output_path, progress_callback)
        )

    async def generate_preview_async(
        self, text: str, voice: str | None = None, max_chars: int = 500
    ) -> tuple[bytes, float]:
        """Generate a short preview of a voice (async).

        Args:
            text: Sample text (will be truncated to max_chars)
            voice: Voice ID (engine-specific)
            max_chars: Maximum characters to synthesize

        Returns:
            Tuple of (audio_bytes, duration_seconds)
        """
        # Truncate to first sentence or max_chars
        preview_text = text[:max_chars]
        sentences = self._split_into_sentences(preview_text)
        if sentences:
            preview_text = sentences[0]

        if self.engine == "chatterbox":
            voice = voice or DEFAULT_CHATTERBOX_VOICE
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.chatterbox_url}/v1/audio/speech",
                    json={
                        "input": preview_text,
                        "voice": voice,
                        "exaggeration": self.exaggeration,
                        "cfg_weight": self.cfg_weight,
                        "temperature": self.temperature,
                    },
                )
                response.raise_for_status()
                audio_data = response.content
                duration = len(preview_text.split()) / 2.5
                return audio_data, duration
        else:
            voice = voice or DEFAULT_COQUI_VOICE
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.coqui_url}/api/tts",
                    params={
                        "text": preview_text,
                        "speaker_id": voice,
                    },
                )
                response.raise_for_status()
                audio_data = response.content
                duration = len(preview_text.split()) / 2.5
                return audio_data, duration

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences for processing.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Split on sentence boundaries
        # This regex handles:
        # - Period, exclamation, question mark followed by space/newline
        # - But not abbreviations like "Mr." or "Dr."
        pattern = r"(?<=[.!?])\s+(?=[A-Z])"
        sentences = re.split(pattern, text)

        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        # Merge very short sentences with previous one
        merged = []
        for sentence in sentences:
            if merged and len(sentence) < 20:
                merged[-1] = merged[-1] + " " + sentence
            else:
                merged.append(sentence)

        return merged

    async def _combine_audio_parts(
        self, audio_parts: list[bytes], output_path: Path
    ) -> Path:
        """Combine multiple audio WAV files into one.

        Args:
            audio_parts: List of WAV audio data
            output_path: Output file path

        Returns:
            Path to combined audio file
        """
        try:
            from pydub import AudioSegment

            # Load all audio segments
            segments = []
            for part_data in audio_parts:
                segment = AudioSegment.from_wav(io.BytesIO(part_data))
                segments.append(segment)

            # Combine all segments
            combined = sum(segments)

            # Export as MP3 for better compression
            if output_path.suffix.lower() == ".mp3":
                combined.export(str(output_path), format="mp3", bitrate="128k")
            else:
                # Export as WAV
                combined.export(str(output_path), format="wav")

            return output_path

        except ImportError:
            # Fallback: just save first part if pydub not available
            logger.warning("pydub not available, saving only first audio part")
            output_path.write_bytes(audio_parts[0] if audio_parts else b"")
            return output_path

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # milliseconds to seconds

        except ImportError:
            # Rough estimate based on file size
            # WAV: ~176KB per second (44.1kHz, 16-bit, stereo)
            file_size = audio_path.stat().st_size
            return file_size / (176 * 1024)


def get_voice_info(
    voice_id: str, engine: Literal["coqui", "chatterbox"] = "chatterbox"
) -> dict | None:
    """Get information about a voice.

    Args:
        voice_id: Voice identifier
        engine: TTS engine

    Returns:
        Voice metadata or None if not found
    """
    if engine == "chatterbox":
        return CHATTERBOX_VOICES.get(voice_id)
    else:
        return COQUI_VOICES.get(voice_id)


def list_voices(
    engine: Literal["coqui", "chatterbox"] = "chatterbox",
    gender: Literal["male", "female", "neutral", "all"] = "all",
) -> dict[str, dict]:
    """List available voices.

    Args:
        engine: TTS engine
        gender: Filter by gender

    Returns:
        Dictionary of voice_id -> metadata
    """
    voices = CHATTERBOX_VOICES if engine == "chatterbox" else COQUI_VOICES

    if gender == "all":
        return voices

    return {
        vid: info for vid, info in voices.items() if info.get("gender") == gender
    }
