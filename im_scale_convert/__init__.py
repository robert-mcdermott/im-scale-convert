"""Utilities for scaling and converting batches of images.

This package provides tools for batch image processing including:
- Scaling images by percentage
- Converting between formats (including WebP)
- Optimizing images with various quality settings
- Parallel processing with configurable worker count
- Command-line interface and programmatic API

Example usage:
    Command line:
        $ im-scale-convert --percent 75 --input-dir photos --output-dir thumbs
    
    Programmatic:
        >>> from pathlib import Path
        >>> from im_scale_convert import run
        >>> result = run(
        ...     percent=50,
        ...     input_dir=Path("images"),
        ...     output_dir=Path("scaled")
        ... )

The package exposes both high-level functions for common use cases and
lower-level components for advanced usage.
"""

from __future__ import annotations

# Import main CLI functions
from .cli import cli, main, parse_args, run

# Import processing functions and exceptions
from .processing import (
    ImageProcessingError,
    InvalidParameterError, 
    ImageNotFoundError,
    ImageFormatError,
    run as process_images,
    find_images,
    resize_image,
)

# Version information
__version__ = "0.1.0"
__author__ = "Robert McDermott"
__email__ = "robert.c.mcdermott@gmail.com"

# Public API
__all__ = [
    # CLI functions
    "cli",
    "main", 
    "parse_args",
    "run",
    
    # Processing functions
    "process_images",
    "find_images",
    "resize_image",
    
    # Exceptions
    "ImageProcessingError",
    "InvalidParameterError",
    "ImageNotFoundError", 
    "ImageFormatError",
    
    # Metadata
    "__version__",
    "__author__",
    "__email__",
]
