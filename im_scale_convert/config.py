"""Configuration constants and settings for im-scale-convert.

This module centralizes configuration values, constants, and default settings
used throughout the application. It provides a single source of truth for
configuration parameters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

# Version information
VERSION: Final[str] = "0.1.0"
AUTHOR: Final[str] = "Robert McDermott"
EMAIL: Final[str] = "robert.c.mcdermott@gmail.com"

# Supported image file extensions
SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"
})

# Processing limits and defaults
MIN_PERCENT: Final[int] = 1
MAX_PERCENT: Final[int] = 1000
DEFAULT_PERCENT: Final[int] = 75

MIN_QUALITY: Final[int] = 1
MAX_QUALITY: Final[int] = 100
DEFAULT_QUALITY: Final[int] = 85

MIN_DIMENSION: Final[int] = 1
DEFAULT_WEBP_METHOD: Final[int] = 6

# Worker limits
MIN_WORKERS: Final[int] = 1
MAX_WORKERS: Final[int] = 64
DEFAULT_WORKERS_FALLBACK: Final[int] = 4

# Default directories
DEFAULT_INPUT_DIR: Final[str] = "images"
DEFAULT_OUTPUT_DIR: Final[str] = "images-scaled"

# Progress reporting
PROGRESS_UPDATE_INTERVAL: Final[int] = 10
MAX_ERROR_DISPLAY: Final[int] = 20

# Logging configuration
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# PIL/Pillow configuration
# Set to None to remove the limit on image pixels (for large images)
PIL_MAX_IMAGE_PIXELS: Final[int | None] = None

# File I/O settings
FILE_CHUNK_SIZE: Final[int] = 8192  # For future file streaming operations
MAX_FILENAME_LENGTH: Final[int] = 255

# Format-specific settings
JPEG_PROGRESSIVE: Final[bool] = True
JPEG_OPTIMIZE_DEFAULT: Final[bool] = False

PNG_OPTIMIZE_DEFAULT: Final[bool] = False

WEBP_LOSSLESS_DEFAULT: Final[bool] = False
WEBP_METHOD_RANGE: Final[tuple[int, int]] = (0, 6)

# CLI-specific constants
CLI_PROG_NAME: Final[str] = "im-scale-convert"
CLI_EXIT_SUCCESS: Final[int] = 0
CLI_EXIT_FAILURE: Final[int] = 1
CLI_EXIT_USAGE_ERROR: Final[int] = 2

# Error messages
ERROR_MESSAGES: Final[dict[str, str]] = {
    "invalid_percent": f"Percent must be between {MIN_PERCENT} and {MAX_PERCENT}",
    "invalid_quality": f"Quality must be between {MIN_QUALITY} and {MAX_QUALITY}", 
    "invalid_workers": f"Workers must be between {MIN_WORKERS} and {MAX_WORKERS}",
    "directory_not_found": "Directory not found",
    "not_a_directory": "Path is not a directory", 
    "cannot_create_directory": "Cannot create directory",
    "no_images_found": "No supported images found",
    "processing_failed": "Image processing failed",
    "unexpected_error": "An unexpected error occurred",
    "user_cancelled": "Operation cancelled by user",
}

# Help text templates
HELP_TEMPLATES: Final[dict[str, str]] = {
    "percent": f"Scale percentage ({MIN_PERCENT}-{MAX_PERCENT}%%). Example: 50 for 50%%.",
    "quality": f"Quality for JPEG/WEBP ({MIN_QUALITY}-{MAX_QUALITY}, default: {DEFAULT_QUALITY})",
    "workers": f"Number of parallel workers ({MIN_WORKERS}-{MAX_WORKERS}, default: CPU count)",
    "input_dir": f"Input images directory (default: {DEFAULT_INPUT_DIR})",
    "output_dir": f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
}


def get_default_input_dir() -> Path:
    """Get the default input directory as a Path object.
    
    Returns:
        Path object for the default input directory
    """
    return Path(DEFAULT_INPUT_DIR)


def get_default_output_dir() -> Path:
    """Get the default output directory as a Path object.
    
    Returns:
        Path object for the default output directory
    """
    return Path(DEFAULT_OUTPUT_DIR)


def is_supported_extension(extension: str) -> bool:
    """Check if a file extension is supported.
    
    Args:
        extension: File extension to check (with or without leading dot)
        
    Returns:
        True if the extension is supported, False otherwise
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    return extension.lower() in SUPPORTED_EXTENSIONS


def validate_percentage(percent: int) -> bool:
    """Validate a percentage value.
    
    Args:
        percent: Percentage value to validate
        
    Returns:
        True if valid, False otherwise
    """
    return MIN_PERCENT <= percent <= MAX_PERCENT


def validate_quality(quality: int) -> bool:
    """Validate a quality value.
    
    Args:
        quality: Quality value to validate
        
    Returns:
        True if valid, False otherwise
    """
    return MIN_QUALITY <= quality <= MAX_QUALITY


def validate_workers(workers: int) -> bool:
    """Validate a worker count value.
    
    Args:
        workers: Worker count to validate
        
    Returns:
        True if valid, False otherwise
    """
    return MIN_WORKERS <= workers <= MAX_WORKERS
