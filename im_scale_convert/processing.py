"""Image processing utilities for scaling and converting batches of images.

This module provides functionality to process images in batch, including:
- Scaling images by percentage
- Converting between formats (including WebP)
- Optimizing images with various quality settings
- Parallel processing with configurable worker count
- Progress tracking and comprehensive error handling

Example:
    >>> from pathlib import Path
    >>> from im_scale_convert.processing import run
    >>> result = run(
    ...     percent=75,
    ...     input_dir=Path("source_images"),
    ...     output_dir=Path("scaled_images"),
    ...     quality=90,
    ...     optimize=True
    ... )
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Generator, Protocol

from PIL import Image, ImageOps

# Constants
SUPPORTED_EXTS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"})
MIN_PERCENT = 1
MAX_PERCENT = 1000
MIN_QUALITY = 1
MAX_QUALITY = 100
DEFAULT_QUALITY = 85
DEFAULT_WEBP_METHOD = 6
MIN_DIMENSION = 1

# Make Pillow more robust for large images
Image.MAX_IMAGE_PIXELS = None

# Set up module logger
logger = logging.getLogger(__name__)


class LoggerProtocol(Protocol):
    """Protocol for logger callable."""
    
    def __call__(self, message: str) -> None:
        """Log a message."""
        ...


class ImageProcessingError(Exception):
    """Base exception for image processing errors."""
    pass


class InvalidParameterError(ImageProcessingError):
    """Exception raised for invalid input parameters."""
    pass


class ImageNotFoundError(ImageProcessingError):
    """Exception raised when input directory or images are not found."""
    pass


class ImageFormatError(ImageProcessingError):
    """Exception raised for unsupported image formats."""
    pass


def validate_parameters(
    percent: int,
    quality: int,
    workers: int | None = None,
) -> None:
    """Validate input parameters.
    
    Args:
        percent: Scale percentage (1-1000)
        quality: Image quality (1-100)
        workers: Optional worker count (must be positive)
        
    Raises:
        InvalidParameterError: If any parameter is invalid
    """
    if not MIN_PERCENT <= percent <= MAX_PERCENT:
        raise InvalidParameterError(
            f"Percent must be between {MIN_PERCENT} and {MAX_PERCENT}, got {percent}"
        )
    
    if not MIN_QUALITY <= quality <= MAX_QUALITY:
        raise InvalidParameterError(
            f"Quality must be between {MIN_QUALITY} and {MAX_QUALITY}, got {quality}"
        )
    
    if workers is not None and workers < 1:
        raise InvalidParameterError(f"Workers must be positive, got {workers}")


def find_images(input_dir: Path) -> Generator[Path, None, None]:
    """Find all supported image files in the input directory recursively.
    
    Args:
        input_dir: Directory to search for images
        
    Yields:
        Path objects for supported image files
        
    Raises:
        ImageNotFoundError: If input directory doesn't exist
    """
    if not input_dir.exists():
        raise ImageNotFoundError(f"Input directory not found: {input_dir}")
    
    if not input_dir.is_dir():
        raise ImageNotFoundError(f"Input path is not a directory: {input_dir}")
    
    for path in input_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            yield path


def ensure_dir(path: Path) -> None:
    """Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path to create
        
    Raises:
        OSError: If directory cannot be created
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ImageProcessingError(f"Cannot create directory {path}: {exc}") from exc


def derive_output_path(
    src: Path, 
    input_dir: Path, 
    output_dir: Path, 
    to_webp: bool
) -> Path:
    """Derive the output path for a source image.
    
    Args:
        src: Source image path
        input_dir: Base input directory
        output_dir: Base output directory
        to_webp: Whether to convert to WebP format
        
    Returns:
        Output path for the processed image
    """
    try:
        relative = src.relative_to(input_dir)
    except ValueError as exc:
        raise ImageProcessingError(
            f"Source path {src} is not relative to input directory {input_dir}"
        ) from exc
    
    if to_webp:
        return (output_dir / relative).with_suffix(".webp")
    return output_dir / relative


def resize_image(image: Image.Image, percent: int) -> Image.Image:
    """Resize an image by a percentage, preserving EXIF orientation.
    
    Args:
        image: PIL Image object to resize
        percent: Scale percentage (1-1000)
        
    Returns:
        Resized PIL Image object
        
    Raises:
        InvalidParameterError: If percent is invalid
        ImageProcessingError: If resize operation fails
    """
    if not MIN_PERCENT <= percent <= MAX_PERCENT:
        raise InvalidParameterError(f"Invalid percent: {percent}")
    
    try:
        # Handle EXIF orientation
        image = ImageOps.exif_transpose(image)
        width, height = image.size
        
        # Calculate new dimensions
        new_width = max(MIN_DIMENSION, (width * percent) // 100)
        new_height = max(MIN_DIMENSION, (height * percent) // 100)
        
        # Skip resize if dimensions haven't changed
        if (new_width, new_height) == (width, height):
            logger.debug(f"No resize needed for {width}x{height} image")
            return image
        
        logger.debug(f"Resizing from {width}x{height} to {new_width}x{new_height}")
        return image.resize(
            (new_width, new_height), 
            resample=Image.Resampling.LANCZOS
        )
    except Exception as exc:
        raise ImageProcessingError(f"Failed to resize image: {exc}") from exc


def build_save_params(
    fmt: str,
    quality: int,
    optimize: bool,
    strip_metadata: bool,
    webp_lossless: bool,
) -> dict[str, Any]:
    """Build save parameters for PIL Image.save().
    
    Args:
        fmt: Image format (JPEG, PNG, WEBP, etc.)
        quality: Image quality (1-100)
        optimize: Whether to optimize the image
        strip_metadata: Whether to strip metadata
        webp_lossless: Whether to save WebP losslessly
        
    Returns:
        Dictionary of save parameters for PIL
    """
    save_kwargs: dict[str, Any] = {}
    fmt_lower = fmt.lower()

    if fmt_lower in {"jpeg", "jpg"}:
        save_kwargs.update({
            "format": "JPEG",
            "quality": quality,
            "optimize": optimize,
            "progressive": True,
        })
    elif fmt_lower == "png":
        save_kwargs.update({
            "format": "PNG",
            "optimize": optimize,
        })
    elif fmt_lower == "webp":
        save_kwargs.update({
            "format": "WEBP",
            "lossless": webp_lossless,
            "quality": quality,
            "method": DEFAULT_WEBP_METHOD,
        })
    else:
        save_kwargs.update({"format": fmt})

    return save_kwargs


def save_image(
    image: Image.Image,
    destination: Path,
    original: Image.Image,
    fmt: str,
    quality: int,
    optimize: bool,
    strip_metadata: bool,
    webp_lossless: bool,
) -> None:
    """Save a processed image to disk.
    
    Args:
        image: Processed PIL Image to save
        destination: Output file path
        original: Original PIL Image (for metadata)
        fmt: Target image format
        quality: Image quality setting
        optimize: Whether to optimize the image
        strip_metadata: Whether to strip metadata
        webp_lossless: Whether to save WebP losslessly
        
    Raises:
        ImageProcessingError: If save operation fails
    """
    try:
        ensure_dir(destination.parent)
        
        save_kwargs = build_save_params(
            fmt, quality, optimize, strip_metadata, webp_lossless
        )

        # Handle metadata preservation
        if not strip_metadata:
            if "exif" in original.info:
                save_kwargs["exif"] = original.info["exif"]
            if "icc_profile" in original.info:
                save_kwargs["icc_profile"] = original.info["icc_profile"]

        # Handle color mode conversion for specific formats
        suffix = destination.suffix.lower()
        target_fmt = "webp" if suffix == ".webp" else fmt.lower()

        if target_fmt in {"jpeg", "jpg", "webp"} and image.mode not in ("RGB", "L"):
            logger.debug(f"Converting image mode from {image.mode} to RGB")
            image = image.convert("RGB")

        logger.debug(f"Saving image to {destination} with format {target_fmt}")
        image.save(destination, **save_kwargs)
        
    except Exception as exc:
        raise ImageProcessingError(
            f"Failed to save image to {destination}: {exc}"
        ) from exc


def process_one(
    source: Path,
    input_dir: Path,
    output_dir: Path,
    percent: int,
    quality: int,
    optimize: bool,
    strip_metadata: bool,
    to_webp: bool,
    webp_lossless: bool,
) -> tuple[Path, str]:
    """Process a single image file.
    
    Args:
        source: Source image path
        input_dir: Base input directory
        output_dir: Base output directory
        percent: Scale percentage
        quality: Image quality
        optimize: Whether to optimize
        strip_metadata: Whether to strip metadata
        to_webp: Whether to convert to WebP
        webp_lossless: Whether to save WebP losslessly
        
    Returns:
        Tuple of (destination_path, status_message)
    """
    destination = derive_output_path(source, input_dir, output_dir, to_webp)
    
    try:
        logger.debug(f"Processing {source} -> {destination}")
        
        with Image.open(source) as original:
            resized = resize_image(original, percent)
            fmt = (
                "WEBP"
                if to_webp
                else (original.format or source.suffix.lstrip(".").upper())
            )
            
            save_image(
                resized,
                destination,
                original,
                fmt,
                quality,
                optimize,
                strip_metadata,
                webp_lossless,
            )
            
        return destination, "ok"
        
    except Exception as exc:
        error_msg = f"error: {exc}"
        logger.error(f"Failed to process {source}: {error_msg}")
        return destination, error_msg


def run(
    percent: int,
    input_dir: Path,
    output_dir: Path,
    *,
    quality: int = DEFAULT_QUALITY,
    optimize: bool = False,
    strip_metadata: bool = False,
    to_webp: bool = False,
    webp_lossless: bool = False,
    workers: int | None = None,
    logger_func: LoggerProtocol | None = None,
) -> int:
    """Run the bulk image conversion process.

    Args:
        percent: Scale percentage (1-1000)
        input_dir: Input directory containing images
        output_dir: Output directory for processed images
        quality: JPEG/WebP quality (1-100, default: 85)
        optimize: Enable optimization (default: False)
        strip_metadata: Strip EXIF/ICC metadata (default: False)
        to_webp: Convert to WebP format (default: False)
        webp_lossless: Save WebP losslessly (default: False)
        workers: Number of worker threads (default: CPU count)
        logger_func: Optional logging function (default: print)

    Returns:
        Exit code: 0 on success, 1 if there were processing errors
        
    Raises:
        InvalidParameterError: If parameters are invalid
        ImageNotFoundError: If input directory is not found
        ImageProcessingError: If processing fails critically
    """
    # Parameter validation
    validate_parameters(percent, quality, workers)
    
    # Resolve paths
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    
    # Set up logging
    log = logger_func or print
    
    try:
        # Ensure output directory exists
        ensure_dir(output_dir)
        
        # Find images
        log(f"Scanning for images in: {input_dir}")
        images = list(find_images(input_dir))
        
        if not images:
            log("No supported images found.")
            return 0

        # Determine worker count
        worker_count = workers or os.cpu_count() or 4
        log(f"Found {len(images)} images. Processing with {worker_count} workers...")

        # Process images in parallel
        results: list[tuple[Path, str]] = []
        
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            # Submit all tasks
            futures = [
                executor.submit(
                    process_one,
                    src,
                    input_dir,
                    output_dir,
                    percent,
                    quality,
                    optimize,
                    strip_metadata,
                    to_webp,
                    webp_lossless,
                )
                for src in images
            ]
            
            # Collect results as they complete
            for i, fut in enumerate(as_completed(futures), 1):
                result = fut.result()
                results.append(result)
                
                # Simple progress indication
                if i % 10 == 0 or i == len(images):
                    log(f"Processed {i}/{len(images)} images...")

        # Report results
        successes = sum(1 for _, status in results if status == "ok")
        errors = [(dst, status) for dst, status in results if status != "ok"]

        log(f"Done. Succeeded: {successes}, Failed: {len(errors)}")
        
        if errors:
            log("Failures:")
            # Show first 20 errors to avoid overwhelming output
            for dst, status in errors[:20]:
                log(f"- {dst}: {status}")
            if len(errors) > 20:
                log(f"... and {len(errors) - 20} more failures")

        return 0 if not errors else 1
        
    except (InvalidParameterError, ImageNotFoundError) as exc:
        # Re-raise parameter and file errors
        raise
    except Exception as exc:
        # Wrap unexpected errors
        raise ImageProcessingError(f"Unexpected error during processing: {exc}") from exc
