from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable
from collections.abc import Callable

from PIL import Image, ImageOps

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Make Pillow more robust for large images
Image.MAX_IMAGE_PIXELS = None


def find_images(input_dir: Path) -> Iterable[Path]:
    return (
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def derive_output_path(src: Path, input_dir: Path, output_dir: Path, to_webp: bool) -> Path:
    relative = src.relative_to(input_dir)
    if to_webp:
        return (output_dir / relative).with_suffix(".webp")
    return output_dir / relative


def resize_image(image: Image.Image, percent: int) -> Image.Image:
    """Resize an image by a percentage, preserving EXIF orientation."""
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    new_width = max(1, (width * percent) // 100)
    new_height = max(1, (height * percent) // 100)
    if (new_width, new_height) == (width, height):
        return image
    return image.resize((new_width, new_height), resample=Image.Resampling.LANCZOS)


def build_save_params(
    fmt: str,
    quality: int,
    optimize: bool,
    strip_metadata: bool,
    webp_lossless: bool,
) -> dict:
    """Return save parameters for saving images."""

    save_kwargs = {}

    fmt_lower = fmt.lower()

    if fmt_lower in {"jpeg", "jpg"}:
        save_kwargs.update(
            {
                "format": "JPEG",
                "quality": quality,
                "optimize": optimize,
                "progressive": True,
            }
        )
        if not strip_metadata:
            pass
    elif fmt_lower == "png":
        save_kwargs.update(
            {
                "format": "PNG",
                "optimize": optimize,
            }
        )
    elif fmt_lower == "webp":
        save_kwargs.update(
            {
                "format": "WEBP",
                "lossless": webp_lossless,
                "quality": quality,
                "method": 6,
            }
        )
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
    ensure_dir(destination.parent)

    save_kwargs = build_save_params(fmt, quality, optimize, strip_metadata, webp_lossless)

    exif_bytes = (
        original.info.get("exif")
        if (not strip_metadata and "exif" in original.info)
        else None
    )
    icc_profile = (
        original.info.get("icc_profile")
        if (not strip_metadata and "icc_profile" in original.info)
        else None
    )

    if exif_bytes:
        save_kwargs["exif"] = exif_bytes
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile

    suffix = destination.suffix.lower()
    target_fmt = "webp" if suffix == ".webp" else fmt.lower()

    if target_fmt in {"jpeg", "jpg", "webp"} and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    image.save(destination, **save_kwargs)


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
    destination = derive_output_path(source, input_dir, output_dir, to_webp)
    try:
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
    except Exception as exc:  # pragma: no cover - defensive fallback
        return destination, f"error: {exc}"


def run(
    percent: int,
    input_dir: Path,
    output_dir: Path,
    *,
    quality: int = 85,
    optimize: bool = False,
    strip_metadata: bool = False,
    to_webp: bool = False,
    webp_lossless: bool = False,
    workers: int | None = None,
    logger: Callable[[str], None] | None = None,
) -> int:
    """Run the bulk image conversion.

    Returns the process exit code (0 on success, >0 on partial failures).
    """

    if percent <= 0:
        raise ValueError("percent must be greater than 0")

    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    ensure_dir(output_dir)

    log = logger or print
    log(f"Scanning for images in: {input_dir}")
    images = list(find_images(input_dir))
    if not images:
        log("No supported images found.")
        return 0

    worker_count = workers or os.cpu_count() or 4
    log(f"Found {len(images)} images. Processing with {worker_count} workers...")

    results = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
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
        for fut in as_completed(futures):
            results.append(fut.result())

    successes = sum(1 for _, status in results if status == "ok")
    errors = [(dst, status) for dst, status in results if status != "ok"]

    log(f"Done. Succeeded: {successes}, Failed: {len(errors)}")
    if errors:
        log("Failures:")
        for dst, status in errors[:20]:
            log(f"- {dst}: {status}")
        if len(errors) > 20:
            log(f"... and {len(errors) - 20} more")

    return 0 if not errors else 1
