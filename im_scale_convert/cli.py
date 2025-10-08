"""Command-line interface for the im-scale-convert tool.

This module provides the CLI functionality for batch image processing,
including argument parsing, validation, and integration with the processing
engine. It supports various image operations like scaling, format conversion,
and optimization.

Example:
    $ im-scale-convert --percent 75 --input-dir photos --output-dir thumbnails
    $ python -m im_scale_convert --percent 50 --to-webp --optimize
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

if (__package__ in {None, ""}) or (__name__ == "__main__"):
    # Handle direct execution and package imports
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    from im_scale_convert.processing import (
        ImageProcessingError,
        InvalidParameterError,
        ImageNotFoundError,
        run as run_processing,
    )
else:  # pragma: no cover - exercised when imported as a package
    from .processing import (
        ImageProcessingError,
        InvalidParameterError,
        ImageNotFoundError,
        run as run_processing,
    )

# CLI Constants
DEFAULT_INPUT_DIR = "images"
DEFAULT_OUTPUT_DIR = "images-scaled"
DEFAULT_QUALITY = 85
MIN_PERCENT = 1
MAX_PERCENT = 1000
MIN_QUALITY = 1
MAX_QUALITY = 100
MIN_WORKERS = 1
MAX_WORKERS = 64

# Set up module logger
logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Error raised for CLI usage problems.
    
    This exception is used to wrap errors that should be displayed
    to the user in a friendly way, without stack traces.
    """
    pass


class PercentAction(argparse.Action):
    """Custom argparse action to validate percentage values."""
    
    def __call__(
        self, 
        parser: argparse.ArgumentParser, 
        namespace: argparse.Namespace, 
        values: str, 
        option_string: str | None = None
    ) -> None:
        try:
            percent = int(values)
            if not MIN_PERCENT <= percent <= MAX_PERCENT:
                raise argparse.ArgumentTypeError(
                    f"Percent must be between {MIN_PERCENT} and {MAX_PERCENT}, got {percent}"
                )
            setattr(namespace, self.dest, percent)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid percent value: {values}") from exc


class QualityAction(argparse.Action):
    """Custom argparse action to validate quality values."""
    
    def __call__(
        self, 
        parser: argparse.ArgumentParser, 
        namespace: argparse.Namespace, 
        values: str, 
        option_string: str | None = None
    ) -> None:
        try:
            quality = int(values)
            if not MIN_QUALITY <= quality <= MAX_QUALITY:
                raise argparse.ArgumentTypeError(
                    f"Quality must be between {MIN_QUALITY} and {MAX_QUALITY}, got {quality}"
                )
            setattr(namespace, self.dest, quality)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid quality value: {values}") from exc


class WorkersAction(argparse.Action):
    """Custom argparse action to validate worker count."""
    
    def __call__(
        self, 
        parser: argparse.ArgumentParser, 
        namespace: argparse.Namespace, 
        values: str, 
        option_string: str | None = None
    ) -> None:
        try:
            workers = int(values)
            if not MIN_WORKERS <= workers <= MAX_WORKERS:
                raise argparse.ArgumentTypeError(
                    f"Workers must be between {MIN_WORKERS} and {MAX_WORKERS}, got {workers}"
                )
            setattr(namespace, self.dest, workers)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid workers value: {values}") from exc


def validate_directory_path(path_str: str) -> Path:
    """Validate and convert a directory path string.
    
    Args:
        path_str: Directory path as string
        
    Returns:
        Validated Path object
        
    Raises:
        argparse.ArgumentTypeError: If path is invalid
    """
    try:
        path = Path(path_str).resolve()
        # Don't check existence here - let the processing module handle it
        return path
    except (OSError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"Invalid directory path '{path_str}': {exc}") from exc


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.
    
    Args:
        verbose: Enable debug logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        argv: Optional argument list (defaults to sys.argv)
        
    Returns:
        Parsed arguments namespace
        
    Raises:
        SystemExit: If argument parsing fails
    """
    parser = argparse.ArgumentParser(
        prog="im-scale-convert",
        description="Scale images by percentage and optionally convert to different formats.",
        epilog="""Examples:
  %(prog)s --percent 50 --input-dir photos --output-dir thumbnails
  %(prog)s -p 75 --to-webp --optimize --strip-metadata
  %(prog)s --percent 25 --quality 95 --workers 8
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Required arguments
    parser.add_argument(
        "--percent",
        "-p",
        action=PercentAction,
        required=True,
        metavar=f"{MIN_PERCENT}-{MAX_PERCENT}",
        help=f"Scale percentage ({MIN_PERCENT}-{MAX_PERCENT}%%). Example: 50 for 50%%.",
    )
    
    # Input/Output directories
    parser.add_argument(
        "--input-dir",
        type=validate_directory_path,
        default=Path(DEFAULT_INPUT_DIR),
        metavar="PATH",
        help=f"Input images directory (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=validate_directory_path,
        default=Path(DEFAULT_OUTPUT_DIR),
        metavar="PATH",
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    
    # Image quality options
    parser.add_argument(
        "--quality",
        action=QualityAction,
        default=DEFAULT_QUALITY,
        metavar=f"{MIN_QUALITY}-{MAX_QUALITY}",
        help=f"Quality for JPEG/WEBP ({MIN_QUALITY}-{MAX_QUALITY}, default: {DEFAULT_QUALITY})",
    )
    
    # Optimization flags
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Enable lossless optimizer where supported (JPEG/PNG)",
    )
    parser.add_argument(
        "--strip-metadata",
        action="store_true",
        help="Strip metadata (EXIF/ICC) for smaller files (lossless)",
    )
    
    # WebP conversion options
    webp_group = parser.add_argument_group("WebP conversion")
    webp_group.add_argument(
        "--to-webp",
        action="store_true",
        help="Convert output to WebP format",
    )
    webp_group.add_argument(
        "--webp-lossless",
        action="store_true",
        help="Save WebP losslessly (ignores quality setting)",
    )
    
    # Performance options
    parser.add_argument(
        "--workers",
        action=WorkersAction,
        default=None,
        metavar=f"{MIN_WORKERS}-{MAX_WORKERS}",
        help=f"Number of parallel workers ({MIN_WORKERS}-{MAX_WORKERS}, default: CPU count)",
    )
    
    # Verbose logging
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    # Version information
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args(argv)
    
    # Post-parsing validation
    if args.webp_lossless and not args.to_webp:
        parser.error("--webp-lossless requires --to-webp")
    
    return args


def cli(
    argv: list[str] | None = None,
    *,
    logger_func: Callable[[str], None] | None = None,
) -> int:
    """Main CLI entry point with error handling.

    Args:
        argv: Optional command-line arguments
        logger_func: Optional custom logging function

    Returns:
        Exit code: 0 on success, non-zero on error
        
    Raises:
        CLIError: For user-facing errors that should be displayed nicely
    """
    try:
        args = parse_args(argv)
        
        # Set up logging based on verbosity
        if not logger_func:
            setup_logging(args.verbose)
        
        logger.info(f"Starting im-scale-convert with {args.percent}% scaling")
        logger.debug(f"Arguments: {args}")
        
        # Run the processing engine
        result = run_processing(
            percent=args.percent,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            quality=args.quality,
            optimize=args.optimize,
            strip_metadata=args.strip_metadata,
            to_webp=args.to_webp,
            webp_lossless=args.webp_lossless,
            workers=args.workers,
            logger_func=logger_func,
        )
        
        logger.info(f"Processing completed with exit code {result}")
        return result
        
    except (InvalidParameterError, ImageNotFoundError) as exc:
        # User input errors - show nicely formatted message
        raise CLIError(str(exc)) from exc
    except ImageProcessingError as exc:
        # Processing errors - show with context
        raise CLIError(f"Processing failed: {exc}") from exc
    except KeyboardInterrupt:
        # User cancelled - clean exit
        raise CLIError("Operation cancelled by user") from None
    except Exception as exc:
        # Unexpected errors - show with debugging info
        logger.exception("Unexpected error occurred")
        raise CLIError(f"Unexpected error: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    """Main entry point with user-friendly error handling.
    
    Args:
        argv: Optional command-line arguments
        
    Returns:
        Exit code: 0 on success, 1-2 on various errors
    """
    try:
        return cli(argv)
    except CLIError as exc:
        # Print user-friendly error message
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        # Handle argparse SystemExit (--help, --version, parse errors)
        return exc.code or 0
    except Exception as exc:  # pragma: no cover
        # Final safety net for truly unexpected errors
        print(f"fatal error: {exc}", file=sys.stderr)
        return 1


def run(argv: list[str] | None = None) -> int:  # pragma: no cover
    """Entry point compatible with `python -m im_scale_convert`.
    
    Args:
        argv: Optional command-line arguments
        
    Returns:
        Exit code from main()
    """
    return main(argv)


def _handle_exit(exit_code: int) -> NoReturn:
    """Handle program exit with proper cleanup.
    
    Args:
        exit_code: Exit code to use
        
    Raises:
        SystemExit: Always raised with the given exit code
    """
    sys.exit(exit_code)


if __name__ == "__main__":  # pragma: no cover
    _handle_exit(main())
