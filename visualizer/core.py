"""Interactive step-by-step visualizer for LeetCode-style Python code."""

from __future__ import annotations

import inspect
import linecache
import pprint
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:  # Optional Rich dependency
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    RICH_AVAILABLE = False
    Console = Layout = Live = Panel = Syntax = Table = Text = None  # type: ignore[misc,assignment]


@dataclass
class RenderSettings:
    context_lines: int = 3
    max_value_repr: int = 120
    watch: Sequence[str] = field(default_factory=list)
    use_rich: bool = True
    rich_theme: str = "monokai"


class Visualizer:
    """Trace a callable and present line-by-line execution details."""

    def __init__(self, *, settings: Optional[RenderSettings] = None) -> None:
        self.settings = settings or RenderSettings()
        if self.settings.use_rich and not RICH_AVAILABLE:
            print(
                "Rich is not installed; falling back to plain-text output.",
                file=sys.stderr,
            )
        self._use_rich = bool(self.settings.use_rich and RICH_AVAILABLE)
        self._continue_until_return = False
        self._target_filename: Optional[str] = None
        self._root_frame: Optional[FrameType] = None
        self._active = False
        self._source_path: Optional[Path] = None
        self._source_total_lines: int = 0
        self._console: Optional[Console] = None
        self._layout: Optional[Layout] = None
        self._live: Optional[Live] = None

    def run(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute `func` while interactively visualizing each step."""

        if self._active:
            raise RuntimeError("Visualizer is already running")

        self._active = True
        try:
            self._prepare(func)
            sys.settrace(self._trace)
            try:
                result = func(*args, **kwargs)
            finally:
                sys.settrace(None)
            return result
        finally:
            if self._use_rich:
                self._teardown_rich_ui()
            self._active = False
            self._root_frame = None
            self._target_filename = None
            self._continue_until_return = False

    # ------------------------------------------------------------------
    # Trace plumbing
    # ------------------------------------------------------------------
    def _prepare(self, func: Callable[..., Any]) -> None:
        filename = inspect.getsourcefile(func)
        if filename is None:
            raise ValueError("Cannot locate source for callable")
        self._target_filename = filename
        self._source_path = Path(filename)
        try:
            self._source_total_lines = len(
                self._source_path.read_text(encoding="utf-8").splitlines()
            )
        except OSError:
            self._source_total_lines = 0
        if self._use_rich:
            self._setup_rich_ui()

    def _trace(self, frame: FrameType, event: str, arg: Any):
        if self._target_filename is None:
            return None

        if frame.f_code.co_filename != self._target_filename:
            return self._trace

        if self._root_frame is None and event == "call":
            self._root_frame = frame

        if not self._should_handle(frame, event):
            return self._trace

        self._render(frame, event, arg)

        if not self._continue_until_return or frame is self._root_frame and event == "return":
            self._prompt()

        return self._trace

    def _should_handle(self, frame: FrameType, event: str) -> bool:
        if self._root_frame is None:
            return event == "call"

        if self._continue_until_return and frame is not self._root_frame:
            return False

        return event in {"call", "line", "return", "exception"}

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _render(self, frame: FrameType, event: str, arg: Any) -> None:
        if self._use_rich:
            self._render_rich(frame, event, arg)
        else:
            self._render_plain(frame, event, arg)

    def _render_plain(self, frame: FrameType, event: str, arg: Any) -> None:
        payload = self._build_event_payload(frame, event, arg)
        header = self._format_plain_header(payload)
        code_block = self._format_plain_code(frame.f_lineno)
        watch_items, locals_items = self._gather_locals(frame)
        locals_block = self._format_plain_locals(watch_items, locals_items)

        segments = [header, code_block]
        if locals_block:
            segments.append(locals_block)

        print("\n".join(segments), flush=True)

    def _render_rich(self, frame: FrameType, event: str, arg: Any) -> None:
        assert self._layout is not None
        payload = self._build_event_payload(frame, event, arg)
        watch_items, locals_items = self._gather_locals(frame)
        self._layout["header"].update(self._rich_header(payload))
        self._layout["code"].update(self._rich_code_panel(frame.f_lineno))
        self._layout["watch"].update(self._rich_table_panel("Watch", watch_items))
        self._layout["locals"].update(self._rich_table_panel("Locals", locals_items))
        self._layout["footer"].update(self._rich_footer(payload))
        assert self._live is not None
        self._live.refresh()

    def _build_event_payload(self, frame: FrameType, event: str, arg: Any) -> Dict[str, Any]:
        func_name = frame.f_code.co_name
        lineno = frame.f_lineno
        label = event.upper()
        if event == "call":
            details = self._format_call_details(frame)
            line_display = frame.f_code.co_firstlineno
        elif event == "return":
            details = f"return value = {self._safe_repr(arg)}"
            line_display = lineno
        elif event == "exception":
            exc_type, exc_value, _ = arg
            details = f"exception {exc_type.__name__}: {self._safe_repr(exc_value)}"
            line_display = lineno
        else:
            details = ""
            line_display = lineno
        return {
            "func_name": func_name,
            "lineno": lineno,
            "label": label,
            "details": details,
            "line_display": line_display,
        }

    def _format_plain_header(self, payload: Dict[str, Any]) -> str:
        line_info = f"line {payload['line_display']}"
        header = f"[{payload['label']}] {payload['func_name']} ({line_info})"
        if payload["details"]:
            header = f"{header} {payload['details']}"
        return header.rstrip()

    def _format_plain_code(self, lineno: int) -> str:
        assert self._target_filename is not None
        start = max(1, lineno - self.settings.context_lines)
        end = lineno + self.settings.context_lines
        lines: List[str] = []
        for idx in range(start, end + 1):
            raw_line = linecache.getline(self._target_filename, idx)
            if not raw_line:
                continue
            marker = "->" if idx == lineno else "  "
            lines.append(f"{marker} {idx:>4}: {raw_line.rstrip()}")
        return "\n".join(lines)

    def _format_plain_locals(
        self,
        watch_items: List[Tuple[str, Any]],
        locals_items: List[Tuple[str, Any]],
    ) -> str:
        items: List[str] = []
        if watch_items:
            items.append("* Watch vars")
            for name, value in watch_items:
                items.append(f"    {name} = {self._safe_repr(value)}")
        if locals_items:
            items.append("* Locals")
            for name, value in locals_items:
                items.append(f"    {name} = {self._safe_repr(value)}")
        return "\n".join(items)

    def _rich_header(self, payload: Dict[str, Any]) -> Panel:
        assert RICH_AVAILABLE
        text = Text()
        text.append(payload["label"], style="bold magenta")
        text.append("  ")
        text.append(payload["func_name"], style="bold white")
        text.append(f"  (line {payload['line_display']})", style="dim")
        if payload["details"]:
            text.append("\n")
            text.append(payload["details"], style="cyan")
        return Panel(text, title="Event", border_style="magenta")

    def _rich_code_panel(self, lineno: int) -> Panel:
        assert self._target_filename is not None and RICH_AVAILABLE
        start = max(1, lineno - self.settings.context_lines)
        max_line = self._source_total_lines or lineno + self.settings.context_lines
        end = min(max_line, lineno + self.settings.context_lines)
        source_lines: List[str] = []
        for idx in range(start, end + 1):
            raw_line = linecache.getline(self._target_filename, idx)
            if not raw_line:
                continue
            source_lines.append(raw_line.rstrip("\n"))
        if not source_lines:
            source_lines = ["<source unavailable>"]
        code = "\n".join(source_lines)
        line_range = (start, start + len(source_lines) - 1)
        highlight = {lineno} if source_lines and "<source unavailable>" not in source_lines else set()
        syntax = Syntax(
            code,
            "python",
            line_numbers=True,
            highlight_lines=highlight,
            line_range=line_range,
            theme=self.settings.rich_theme,
            indent_guides=True,
        )
        title = f"{self._source_path.name}:{lineno}" if self._source_path else f"line {lineno}"
        return Panel(syntax, title=title, border_style="green")

    def _rich_table_panel(self, title: str, items: List[Tuple[str, Any]]) -> Panel:
        assert RICH_AVAILABLE
        table = Table(show_header=False, expand=True, box=None, pad_edge=False)
        table.add_column(style="bold cyan", no_wrap=True)
        table.add_column(overflow="fold")
        if items:
            for name, value in items:
                table.add_row(name, self._safe_repr(value))
        else:
            table.add_row("[dim]--[/dim]", "[dim]empty[/dim]")
        return Panel(table, title=title, border_style="blue")

    def _rich_footer(self, payload: Dict[str, Any]) -> Panel:
        assert RICH_AVAILABLE
        text = Text("Step: Enter | Continue: c | Quit: q", style="bold")
        text.append(
            f"\nLast event: {payload['label']} at line {payload['lineno']}",
            style="dim",
        )
        return Panel(text, border_style="magenta", title="Controls")

    def _setup_rich_ui(self) -> None:
        assert RICH_AVAILABLE
        self._console = Console()
        self._layout = self._build_layout()
        self._live = Live(
            self._layout,
            console=self._console,
            screen=True,
            auto_refresh=False,
        )
        self._live.start()

    def _build_layout(self) -> Layout:
        assert RICH_AVAILABLE
        layout = Layout(name="root")
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="code", ratio=3),
            Layout(name="sidebar", ratio=2),
        )
        layout["sidebar"].split(
            Layout(name="watch", ratio=1),
            Layout(name="locals", ratio=2),
        )
        layout["header"].update(Panel(Text("Waiting for trace"), title="Event"))
        layout["code"].update(Panel(Text("--"), title="Source"))
        layout["watch"].update(Panel(Text("No watch vars"), title="Watch"))
        layout["locals"].update(Panel(Text("Locals will appear here"), title="Locals"))
        layout["footer"].update(
            Panel(
                Text("Step: Enter | Continue: c | Quit: q", style="bold"),
                title="Controls",
            )
        )
        return layout

    def _teardown_rich_ui(self) -> None:
        if self._live is not None:
            self._live.stop()
        self._live = None
        self._layout = None
        self._console = None

    def _gather_locals(
        self, frame: FrameType
    ) -> Tuple[List[Tuple[str, Any]], List[Tuple[str, Any]]]:
        locals_view: Dict[str, Any] = {
            k: v for k, v in frame.f_locals.items() if not k.startswith("__")
        }
        watch_items: List[Tuple[str, Any]] = []
        watch_set = set(self.settings.watch)
        for name in self.settings.watch:
            if name in locals_view:
                watch_items.append((name, locals_view[name]))
        locals_items = [
            (name, value)
            for name, value in sorted(locals_view.items())
            if name not in watch_set
        ]
        return watch_items, locals_items

    def _format_call_details(self, frame: FrameType) -> str:
        arg_info = inspect.getargvalues(frame)
        pairs = []
        for name in arg_info.args:
            if name in frame.f_locals:
                pairs.append(f"{name}={self._safe_repr(frame.f_locals[name])}")
        if arg_info.varargs and arg_info.varargs in frame.f_locals:
            pairs.append(
                f"*{arg_info.varargs}={self._safe_repr(frame.f_locals[arg_info.varargs])}"
            )
        if arg_info.keywords and arg_info.keywords in frame.f_locals:
            pairs.append(
                f"**{arg_info.keywords}={self._safe_repr(frame.f_locals[arg_info.keywords])}"
            )
        return "(" + ", ".join(pairs) + ")"

    def _safe_repr(self, value: Any) -> str:
        try:
            formatted = pprint.pformat(value, width=80, compact=True)
        except Exception:
            formatted = repr(value)

        if len(formatted) > self.settings.max_value_repr:
            return formatted[: self.settings.max_value_repr - 3] + "..."
        return formatted

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    def _prompt(self) -> None:
        prompt_text = "step [Enter] | continue [c] | quit [q]: "
        while True:
            if self._use_rich and self._live is not None:
                user_input = (
                    self._live.console.input(
                        f"[bold cyan]{prompt_text}[/bold cyan]"
                    )
                    .strip()
                    .lower()
                )
            else:
                user_input = input(prompt_text).strip().lower()
            if user_input in {"", "s", "n"}:
                self._continue_until_return = False
                return
            if user_input == "c":
                self._continue_until_return = True
                return
            if user_input == "q":
                raise KeyboardInterrupt("Visualization aborted by user")
            if self._use_rich and self._live is not None:
                self._live.console.print("[red]Unrecognized input. Use Enter, c, or q.[/red]")
            else:
                print("Unrecognized input. Use Enter, c, or q.")
