from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    from im_scale_convert.processing import run as run_processing
else:  # pragma: no cover - exercised when imported as a package
    from .processing import run as run_processing


class CLIError(Exception):
    """Error raised for CLI usage problems."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="im-scale-convert",
        description="Scale images by a percent and write to an output directory.",
    )
    parser.add_argument(
        "--percent",
        "-p",
        type=int,
        required=True,
        help="Scale percent (e.g., 50 for 50%%.)",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("images"),
        help="Input images directory (default: images)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("images-scaled"),
        help="Output directory (default: images-scaled)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="Quality for JPEG/WEBP (default: 85)",
    )
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
    parser.add_argument(
        "--to-webp",
        action="store_true",
        help="Convert output to WEBP format",
    )
    parser.add_argument(
        "--webp-lossless",
        action="store_true",
        help="Save WEBP losslessly (ignores quality)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: CPU count)",
    )

    return parser.parse_args(argv)


def cli(
    argv: list[str] | None = None,
    *,
    logger: Callable[[str], None] | None = None,
) -> int:
    args = parse_args(argv)

    try:
        return run_processing(
            percent=args.percent,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            quality=args.quality,
            optimize=args.optimize,
            strip_metadata=args.strip_metadata,
            to_webp=args.to_webp,
            webp_lossless=args.webp_lossless,
            workers=args.workers,
            logger=logger,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise CLIError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    try:
        return cli(argv)
    except CLIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def run(argv: list[str] | None = None) -> int:  # pragma: no cover
    """Entry point compatible with `python -m im_scale_convert`."""
    return main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
