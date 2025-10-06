"""Command line entry point for the LeetCode visualizer."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any, List

from visualizer.core import RenderSettings, Visualizer


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step through Python code visually.")
    parser.add_argument("script", type=Path, help="Path to the Python script containing the target callable.")
    parser.add_argument("expr", help="Python expression that resolves to the callable to visualize.")
    parser.add_argument("--args", default="()", help="Tuple literal with positional arguments.")
    parser.add_argument("--kwargs", default="{}", help="Dict literal with keyword arguments.")
    parser.add_argument(
        "--watch",
        default="",
        help="Comma separated list of variable names to emphasize in the output.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    module = _load_module(args.script.resolve())

    try:
        callable_obj = eval(args.expr, module.__dict__)
    except Exception as exc:  # noqa: BLE001 - surface eval failures clearly
        raise SystemExit(f"Failed to evaluate expression '{args.expr}': {exc}")

    try:
        positional = ast.literal_eval(args.args)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"--args must be a valid Python literal tuple: {exc}")

    if not isinstance(positional, tuple):
        positional = (positional,)

    try:
        keyword = ast.literal_eval(args.kwargs)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"--kwargs must be a valid Python literal dict: {exc}")

    if not isinstance(keyword, dict):
        raise SystemExit("--kwargs must evaluate to a dict")

    watch_list = [name.strip() for name in args.watch.split(",") if name.strip()]
    settings = RenderSettings(watch=watch_list)
    visualizer = Visualizer(settings=settings)

    try:
        visualizer.run(callable_obj, *positional, **keyword)
    except KeyboardInterrupt:
        print("\nVisualization stopped.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
