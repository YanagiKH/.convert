from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .debug import configure_logging
from .engine import ConversionEngine
from .errors import DotConvertError
from .i18n import LANGUAGE_LABELS, tr, warning_text
from .models import ConversionMode, ConversionPlan, ConversionResult, Severity
from .registry import extension_for_path
from .safety import resolve_destination

LOGGER = logging.getLogger("dotconvert.app")
MEDIA_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".opus",
    ".aac",
    ".m4a",
    ".wma",
    ".aiff",
    ".mp4",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
    ".m4v",
    ".flv",
    ".mpeg",
    ".3gp",
    ".ogv",
    ".ts",
}


class DotConvertApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("820x720")
        self.minsize(720, 620)
        self.engine = ConversionEngine()
        self.source_path: Path | None = None
        self.target_extensions: tuple[str, ...] = ()
        self.selected_target_extension: str | None = None
        self.result_queue: queue.Queue[ConversionResult | Exception] = queue.Queue()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.log_lines: list[str] = []
        self.language = "en"
        self.logs_visible = False

        self.source_var = tk.StringVar(value=tr(self.language, "no_file"))
        self.target_var = tk.StringVar()
        self.mode_var = tk.StringVar(value=ConversionMode.SAVE_AS.value)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.quality_var = tk.IntVar(value=92)
        self.debug_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value=tr(self.language, "select_source_status"))
        self.log_path = configure_logging(debug=False, output_queue=self.log_queue)
        self.quality_var.trace_add("write", self._quality_changed)

        self._build_ui()
        self.after(120, self._poll_results)
        self.after(120, self._poll_logs)
        LOGGER.info("Desktop interface started")

    def _t(self, key: str) -> str:
        return tr(self.language, key)

    def _build_ui(self) -> None:
        self.title(self._t("window_title"))
        for child in self.winfo_children():
            child.destroy()

        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))

        root = ttk.Frame(self, padding=22)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x")
        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text=".convert", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_area, text=self._t("subtitle"), style="Sub.TLabel").pack(
            anchor="w", pady=(0, 14)
        )

        language_area = ttk.LabelFrame(header, text=self._t("language"), padding=5)
        language_area.pack(side="right", anchor="n")
        for index, (code, label) in enumerate(LANGUAGE_LABELS.items()):
            button = ttk.Button(
                language_area,
                text=label,
                width=9,
                command=lambda selected=code: self._set_language(selected),
            )
            button.grid(row=0, column=index, padx=2)

        source_frame = ttk.LabelFrame(
            root,
            text=self._t("source_section"),
            padding=12,
            style="Section.TLabelframe",
        )
        source_frame.pack(fill="x", pady=(0, 10))
        source_frame.columnconfigure(0, weight=1)
        ttk.Label(source_frame, textvariable=self.source_var, wraplength=590).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            source_frame,
            text=self._t("choose_file"),
            command=self._choose_source,
        ).grid(row=0, column=1, padx=(12, 0))

        target_frame = ttk.LabelFrame(
            root,
            text=self._t("target_section"),
            padding=12,
            style="Section.TLabelframe",
        )
        target_frame.pack(fill="x", pady=(0, 10))
        target_frame.columnconfigure(0, weight=1)
        self.target_combo = ttk.Combobox(target_frame, textvariable=self.target_var, state="disabled")
        self.target_combo.grid(row=0, column=0, sticky="ew")
        self.target_combo.bind("<<ComboboxSelected>>", self._target_selected)
        self.ffmpeg_label = ttk.Label(target_frame, text="")
        self.ffmpeg_label.grid(row=1, column=0, sticky="w", pady=(7, 0))

        options = ttk.LabelFrame(
            root,
            text=self._t("options_section"),
            padding=12,
            style="Section.TLabelframe",
        )
        options.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(
            options,
            text=self._t("save_as"),
            variable=self.mode_var,
            value=ConversionMode.SAVE_AS.value,
            command=self._refresh_preview,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            options,
            text=self._t("replace_source"),
            variable=self.mode_var,
            value=ConversionMode.REPLACE_SOURCE.value,
            command=self._refresh_preview,
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Checkbutton(
            options,
            text=self._t("overwrite"),
            variable=self.overwrite_var,
            command=self._refresh_preview,
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(options, text=self._t("image_quality")).grid(
            row=0, column=1, padx=(28, 8), sticky="e"
        )
        ttk.Scale(
            options,
            from_=50,
            to=100,
            variable=self.quality_var,
            orient="horizontal",
            length=150,
        ).grid(row=0, column=2, sticky="ew")
        self.quality_label = ttk.Label(options, text=str(round(self.quality_var.get())))
        self.quality_label.grid(row=0, column=3, padx=(8, 0))

        debug_row = ttk.Frame(options)
        debug_row.grid(row=1, column=1, columnspan=3, rowspan=2, padx=(28, 0), sticky="w")
        ttk.Checkbutton(
            debug_row,
            text=self._t("debug_mode"),
            variable=self.debug_var,
            command=self._toggle_debug,
        ).pack(anchor="w")
        self.logs_button = ttk.Button(
            debug_row,
            text=self._t("hide_logs") if self.logs_visible else self._t("show_logs"),
            command=self._toggle_logs,
        )
        self.logs_button.pack(anchor="w", pady=(5, 0))

        preview = ttk.LabelFrame(
            root,
            text=self._t("preview"),
            padding=12,
            style="Section.TLabelframe",
        )
        preview.pack(fill="both", expand=True, pady=(0, 10))
        self.preview_text = tk.Text(preview, height=8, wrap="word", state="disabled", relief="flat")
        self.preview_text.pack(fill="both", expand=True)

        self.log_frame = ttk.LabelFrame(
            root,
            text=f"{self._t('log_file')}: {self.log_path}",
            padding=8,
            style="Section.TLabelframe",
        )
        log_toolbar = ttk.Frame(self.log_frame)
        log_toolbar.pack(fill="x")
        ttk.Button(log_toolbar, text=self._t("clear_logs"), command=self._clear_log_view).pack(
            side="right"
        )
        self.log_text = tk.Text(
            self.log_frame,
            height=8,
            wrap="none",
            state="disabled",
            font=("Consolas", 9),
        )
        self.log_text.pack(fill="both", expand=True, pady=(5, 0))
        self._render_log_lines()
        if self.logs_visible:
            self.log_frame.pack(fill="both", expand=False, pady=(0, 10))

        footer = ttk.Frame(root)
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var).pack(side="left", fill="x", expand=True)
        self.convert_button = ttk.Button(
            footer,
            text=self._t("start"),
            command=self._start_conversion,
            state="normal" if self.source_path and self.target_extensions else "disabled",
        )
        self.convert_button.pack(side="right")

        self._populate_target_combo()
        self._refresh_ffmpeg_label()
        self._refresh_preview()

    def _set_language(self, language: str) -> None:
        if language == self.language:
            return
        self.language = language
        if self.source_path is None:
            self.source_var.set(self._t("no_file"))
            self.status_var.set(self._t("select_source_status"))
        elif self.target_extensions:
            self.status_var.set(self._t("ready"))
        else:
            self.status_var.set(self._t("ffmpeg_missing_status"))
        LOGGER.info("Interface language changed to %s", language)
        self._build_ui()

    def _populate_target_combo(self) -> None:
        if not hasattr(self, "target_combo"):
            return
        labels = [item.upper() for item in self.target_extensions]
        self.target_combo.configure(values=labels, state="readonly" if labels else "disabled")
        mapping = dict(zip(labels, self.target_extensions, strict=True))
        self.target_combo._extension_map = mapping  # type: ignore[attr-defined]
        if labels:
            selected = self.selected_target_extension
            if selected not in self.target_extensions:
                selected = self.target_extensions[0]
                self.selected_target_extension = selected
            self.target_var.set(selected.upper())
        else:
            self.target_var.set("")

    def _target_selected(self, _event: object) -> None:
        mapping = getattr(self.target_combo, "_extension_map", {})
        self.selected_target_extension = mapping.get(self.target_var.get())
        self._refresh_preview()

    def _quality_changed(self, *_args: object) -> None:
        if hasattr(self, "quality_label"):
            self.quality_label.configure(text=str(round(self.quality_var.get())))
        if hasattr(self, "preview_text"):
            self._refresh_preview()

    def _choose_source(self) -> None:
        filename = filedialog.askopenfilename(title=self._t("choose_file_title"))
        if not filename:
            return
        source = Path(filename)
        try:
            targets = self.engine.targets_for(source)
            source_extension = extension_for_path(source)
        except DotConvertError as exc:
            LOGGER.warning("Rejected source %s: %s", source, exc)
            messagebox.showerror(self._t("unsupported_file"), str(exc), parent=self)
            return
        self.source_path = source
        self.source_var.set(f"{source.name}\n{source}")
        self.target_extensions = targets
        self.selected_target_extension = next(
            (extension for extension in targets if extension != source_extension),
            targets[0] if targets else None,
        )
        self._populate_target_combo()
        if targets:
            self.convert_button.configure(state="normal")
            self.status_var.set(self._t("ready"))
        else:
            self.convert_button.configure(state="disabled")
            self.status_var.set(self._t("ffmpeg_missing_status"))
        self._refresh_ffmpeg_label()
        self._refresh_preview()
        LOGGER.info("Selected source: %s", source)

    def _refresh_ffmpeg_label(self) -> None:
        if not hasattr(self, "ffmpeg_label"):
            return
        if self.source_path is None:
            self.ffmpeg_label.configure(text="")
            return
        try:
            source_extension = extension_for_path(self.source_path)
        except DotConvertError:
            self.ffmpeg_label.configure(text="")
            return
        if source_extension in MEDIA_EXTENSIONS:
            self.ffmpeg_label.configure(
                text=self._t("ffmpeg_ready")
                if self.engine.ffmpeg_available()
                else self._t("ffmpeg_required")
            )
        else:
            self.ffmpeg_label.configure(text="")

    def _selected_extension(self) -> str | None:
        return self.selected_target_extension

    def _make_plan(self, destination: Path | None = None) -> ConversionPlan:
        if self.source_path is None:
            raise DotConvertError(self._t("select_source_error"))
        extension = self._selected_extension()
        if extension is None:
            raise DotConvertError(self._t("select_target_error"))
        return ConversionPlan(
            source=self.source_path,
            target_extension=extension,
            destination=destination,
            mode=ConversionMode(self.mode_var.get()),
            overwrite_existing=self.overwrite_var.get(),
            image_quality=round(self.quality_var.get()),
        )

    def _refresh_preview(self) -> None:
        if not hasattr(self, "preview_text"):
            return
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        try:
            plan = self._make_plan()
            destination = resolve_destination(plan)
            warnings = self.engine.warnings_for(plan)
            lines = [
                f"{self._t('source')}: {plan.source}",
                f"{self._t('default_output')}: {destination}",
                "",
            ]
            if warnings:
                lines.append(f"{self._t('known_risks')}:")
                for warning in warnings:
                    marker = self._t("danger") if warning.severity == Severity.DANGER else self._t("attention")
                    message = warning_text(self.language, warning.code, warning.message)
                    lines.append(f"• [{marker}] {message}")
            else:
                lines.append(self._t("no_known_risk"))
            self.preview_text.insert("1.0", "\n".join(lines))
        except DotConvertError as exc:
            self.preview_text.insert("1.0", str(exc))
        finally:
            self.preview_text.configure(state="disabled")

    def _start_conversion(self) -> None:
        try:
            plan = self._make_plan()
            suggested = resolve_destination(plan)
            if plan.mode == ConversionMode.SAVE_AS:
                extension = plan.normalized_extension()
                chosen = filedialog.asksaveasfilename(
                    title=self._t("choose_output"),
                    initialdir=suggested.parent,
                    initialfile=suggested.name,
                    defaultextension=extension,
                    filetypes=[(extension.upper(), f"*{extension}"), (self._t("all_files"), "*.*")],
                )
                if not chosen:
                    return
                plan = self._make_plan(Path(chosen))
            warnings = self.engine.warnings_for(plan)
        except DotConvertError as exc:
            LOGGER.warning("Unable to start conversion: %s", exc)
            messagebox.showerror(self._t("cannot_start"), str(exc), parent=self)
            return

        if warnings:
            details = "\n".join(
                f"• {warning_text(self.language, warning.code, warning.message)}"
                for warning in warnings
            )
            if not messagebox.askyesno(
                self._t("confirm_title"),
                self._t("confirm_body").format(details=details),
                icon="warning",
                parent=self,
            ):
                LOGGER.info("Conversion cancelled at warning confirmation")
                return

        self.convert_button.configure(state="disabled")
        self.status_var.set(self._t("converting"))
        threading.Thread(target=self._run_conversion, args=(plan,), daemon=True).start()

    def _run_conversion(self, plan: ConversionPlan) -> None:
        try:
            self.result_queue.put(self.engine.convert(plan))
        except Exception as exc:
            self.result_queue.put(exc)

    def _poll_results(self) -> None:
        try:
            result = self.result_queue.get_nowait()
        except queue.Empty:
            self.after(120, self._poll_results)
            return
        self.convert_button.configure(state="normal" if self.source_path else "disabled")
        if isinstance(result, Exception):
            message = (
                str(result)
                if isinstance(result, DotConvertError)
                else self._t("unexpected_error")
            )
            self.status_var.set(self._t("failed_status"))
            messagebox.showerror(self._t("failed_title"), message, parent=self)
        else:
            source_note = (
                self._t("source_recycled") if result.source_recycled else self._t("source_kept")
            )
            extra = ""
            recycle_warning = next(
                (warning.message for warning in result.warnings if warning.code == "recycle-failed"),
                None,
            )
            if recycle_warning:
                extra = f"\n\n{recycle_warning}"
            self.status_var.set(f"{self._t('complete_title')}: {result.destination.name}")
            messagebox.showinfo(
                self._t("complete_title"),
                f"{self._t('output_file')}:\n{result.destination}\n\n{source_note}{extra}",
                parent=self,
            )
        self.after(120, self._poll_results)

    def _toggle_debug(self) -> None:
        enabled = self.debug_var.get()
        self.log_path = configure_logging(
            debug=enabled,
            log_path=self.log_path,
            output_queue=self.log_queue,
        )
        LOGGER.info("%s", self._t("debug_enabled") if enabled else self._t("debug_disabled"))
        if enabled and not self.logs_visible:
            self._toggle_logs()

    def _toggle_logs(self) -> None:
        self.logs_visible = not self.logs_visible
        if self.logs_visible:
            self.log_frame.pack(fill="both", expand=False, pady=(0, 10), before=self.log_frame.master.winfo_children()[-1])
            self.logs_button.configure(text=self._t("hide_logs"))
            self.geometry("820x860")
        else:
            self.log_frame.pack_forget()
            self.logs_button.configure(text=self._t("show_logs"))
            self.geometry("820x720")

    def _clear_log_view(self) -> None:
        self.log_lines.clear()
        self._render_log_lines()

    def _poll_logs(self) -> None:
        changed = False
        while True:
            try:
                self.log_lines.append(self.log_queue.get_nowait())
                changed = True
            except queue.Empty:
                break
        if len(self.log_lines) > 500:
            self.log_lines = self.log_lines[-500:]
            changed = True
        if changed and hasattr(self, "log_text"):
            self._render_log_lines()
        self.after(120, self._poll_logs)

    def _render_log_lines(self) -> None:
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", "\n".join(self.log_lines))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def run_app() -> None:
    app = DotConvertApp()
    app.mainloop()
