"""Cover image extraction and downloading."""

import io
from pathlib import Path

import ebooklib
import httpx
from ebooklib import epub
from PIL import Image
from rich.console import Console

from librarian.config import settings

console = Console()


def extract_cover(file_path: Path, file_format: str) -> bytes | None:
    """
    Extract cover image from a file.

    Args:
        file_path: Path to the file
        file_format: File format (epub, pdf, etc.)

    Returns:
        Cover image data as bytes, or None if extraction failed
    """
    if file_format == "epub":
        return _extract_epub_cover(file_path)
    elif file_format == "pdf":
        return _extract_pdf_cover(file_path)
    return None


def _extract_epub_cover(file_path: Path) -> bytes | None:
    """Extract cover from an EPUB file."""
    try:
        book = epub.read_epub(str(file_path), options={"ignore_ncx": True})

        # First, try to find the cover by ITEM_COVER type
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_COVER:
                return item.get_content()

        # Try to find cover from metadata
        cover_id = None
        for meta in book.get_metadata("OPF", "meta"):
            attrs = meta[1] if len(meta) > 1 else {}
            if attrs.get("name") == "cover":
                cover_id = attrs.get("content")
                break

        if cover_id:
            for item in book.get_items():
                if item.get_id() == cover_id:
                    return item.get_content()

        # Fallback: look for common cover image filenames
        cover_patterns = ["cover", "Cover", "COVER", "front", "Front"]
        for item in book.get_items():
            if item.media_type and item.media_type.startswith("image/"):
                name = item.get_name().lower()
                for pattern in cover_patterns:
                    if pattern.lower() in name:
                        return item.get_content()

        # Last resort: use the first image
        for item in book.get_items():
            if item.media_type and item.media_type.startswith("image/"):
                return item.get_content()

    except Exception as e:
        console.print(f"[yellow]Could not extract cover from {file_path.name}: {e}[/yellow]")

    return None


def _extract_pdf_cover(file_path: Path) -> bytes | None:
    """
    Extract cover from a PDF file.

    This renders the first page as an image.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        # PyMuPDF not installed, skip PDF cover extraction
        return None

    try:
        doc = fitz.open(str(file_path))
        if len(doc) == 0:
            return None

        # Render first page at reasonable resolution
        page = doc[0]
        # Scale to get approximately 600px width
        zoom = 600 / page.rect.width if page.rect.width > 0 else 1
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        return pix.tobytes("jpeg")
    except Exception as e:
        console.print(f"[yellow]Could not extract PDF cover from {file_path.name}: {e}[/yellow]")

    return None


async def download_cover(url: str, client: httpx.AsyncClient | None = None) -> bytes | None:
    """
    Download cover image from a URL.

    Args:
        url: URL of the cover image
        client: Optional httpx client to reuse

    Returns:
        Cover image data as bytes, or None if download failed
    """
    should_close = client is None
    if client is None:
        client = httpx.AsyncClient()

    try:
        response = await client.get(url, follow_redirects=True, timeout=30.0)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        console.print(f"[yellow]Could not download cover from {url}: {e}[/yellow]")
    finally:
        if should_close:
            await client.aclose()

    return None


def process_cover(cover_data: bytes, max_size: int = 800) -> bytes:
    """
    Process cover image: resize if needed, convert to JPEG.

    Args:
        cover_data: Raw image data
        max_size: Maximum width or height in pixels

    Returns:
        Processed JPEG image data
    """
    try:
        img = Image.open(io.BytesIO(cover_data))

        # Convert to RGB if needed (for JPEG output)
        if img.mode in ("RGBA", "P"):
            # Create white background for transparency
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if too large
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Save as JPEG
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()

    except Exception as e:
        console.print(f"[yellow]Could not process cover image: {e}[/yellow]")
        # Return original data if processing fails
        return cover_data


def save_cover(cover_data: bytes, item_uuid: str) -> Path:
    """
    Save cover image to the covers directory.

    Args:
        cover_data: Image data
        item_uuid: UUID of the item

    Returns:
        Path to the saved cover file
    """
    covers_dir = settings.covers_dir
    covers_dir.mkdir(parents=True, exist_ok=True)

    cover_path = covers_dir / f"{item_uuid}.jpg"
    cover_path.write_bytes(cover_data)

    return cover_path


async def get_cover(
    file_path: Path | None,
    file_format: str | None,
    cover_url: str | None,
    item_uuid: str,
) -> str | None:
    """
    Get cover for an item, trying extraction first then download.

    Args:
        file_path: Path to the source file (for extraction)
        file_format: Format of the source file
        cover_url: URL to download cover from (fallback)
        item_uuid: UUID of the item (for saving)

    Returns:
        Relative path to saved cover, or None if no cover available
    """
    cover_data: bytes | None = None

    # Try extraction first (for EPUBs)
    if file_path and file_format:
        cover_data = extract_cover(file_path, file_format)

    # Fall back to download
    if cover_data is None and cover_url:
        cover_data = await download_cover(cover_url)

    if cover_data is None:
        return None

    # Process and save
    processed = process_cover(cover_data)
    save_cover(processed, item_uuid)

    # Return relative path from library root
    return f".covers/{item_uuid}.jpg"
