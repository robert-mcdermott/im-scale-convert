"""Standalone shim for backwards compatibility when running `python main.py`."""

from __future__ import annotations

from im_scale_convert.cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

