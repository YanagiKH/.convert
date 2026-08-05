from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotconvert.debug import configure_logging
from dotconvert.engine import ConversionEngine
from dotconvert.errors import DotConvertError
from dotconvert.models import ConversionMode, ConversionPlan
from dotconvert.registry import supported_formats

LOGGER = logging.getLogger("dotconvert.cli")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dotconvert",
        description="Safely convert compatible file formats.",
    )
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        help="Source file. Omit to open the desktop window.",
    )
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        help="Destination file for command-line mode.",
    )
    parser.add_argument(
        "--replace-source",
        action="store_true",
        help="Move the original to the recycle bin after success.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing destination.",
    )
    parser.add_argument("--quality", type=int, default=92, help="Image quality from 1 to 100.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Accept conversion warnings without an interactive prompt.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug logging.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Write logs to this path instead of the platform default.",
    )
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="List supported desktop formats and exit.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    debug_enabled = args.debug or os.environ.get("DOTCONVERT_DEBUG", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    log_path = configure_logging(debug=debug_enabled, log_path=args.log_file)
    LOGGER.debug("Parsed arguments: %s", args)

    if args.list_formats:
        for item in supported_formats():
            print(f"{item.family.value:8} {item.extension:9} {item.label}")
        return 0
    if args.source is None:
        from dotconvert.app import run_app

        run_app()
        return 0
    if args.destination is None:
        print("error: destination is required in command-line mode", file=sys.stderr)
        return 2
    plan = ConversionPlan(
        source=args.source,
        target_extension=(
            "".join(args.destination.suffixes[-2:])
            if args.destination.name.lower().endswith(
                (".tar.gz", ".tar.bz2", ".tar.xz")
            )
            else args.destination.suffix
        ),
        destination=args.destination,
        mode=(
            ConversionMode.REPLACE_SOURCE if args.replace_source else ConversionMode.SAVE_AS
        ),
        overwrite_existing=args.overwrite,
        image_quality=args.quality,
    )
    engine = ConversionEngine()
    try:
        warnings = engine.warnings_for(plan)
        if warnings and not args.yes:
            print("Conversion warnings:", file=sys.stderr)
            for warning in warnings:
                print(f"- {warning.message}", file=sys.stderr)
            print("Re-run with --yes after reviewing the warnings.", file=sys.stderr)
            return 3
        result = engine.convert(plan)
    except DotConvertError as exc:
        LOGGER.warning("Conversion rejected: %s", exc)
        print(f"error: {exc}", file=sys.stderr)
        if debug_enabled:
            print(f"debug log: {log_path}", file=sys.stderr)
        return 1
    print(result.destination)
    if debug_enabled:
        print(f"debug log: {log_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
