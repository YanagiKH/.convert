from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .engine import ConversionEngine
from .errors import DotConvertError
from .models import ConversionMode, ConversionPlan, ConversionResult, Severity
from .registry import display_label, extension_for_path
from .safety import resolve_destination


class DotConvertApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(".convert — 安全檔案格式轉換")
        self.geometry("760x620")
        self.minsize(680, 560)
        self.engine = ConversionEngine()
        self.source_path: Path | None = None
        self.result_queue: queue.Queue[ConversionResult | Exception] = queue.Queue()

        self.source_var = tk.StringVar(value="尚未選擇檔案")
        self.target_var = tk.StringVar()
        self.mode_var = tk.StringVar(value=ConversionMode.SAVE_AS.value)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.quality_var = tk.IntVar(value=92)
        self.status_var = tk.StringVar(value="選擇來源檔案以開始。")
        self._build_ui()
        self.after(120, self._poll_results)

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))

        root = ttk.Frame(self, padding=24)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text=".convert", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            root,
            text="實際重新編碼、相容格式限制、風險預警與原子寫入。",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(0, 18))

        source_frame = ttk.LabelFrame(root, text="1. 選擇來源", padding=14, style="Section.TLabelframe")
        source_frame.pack(fill="x", pady=(0, 12))
        source_frame.columnconfigure(0, weight=1)
        ttk.Label(source_frame, textvariable=self.source_var, wraplength=560).grid(row=0, column=0, sticky="w")
        ttk.Button(source_frame, text="選擇檔案", command=self._choose_source).grid(row=0, column=1, padx=(12, 0))

        target_frame = ttk.LabelFrame(root, text="2. 選擇輸出格式", padding=14, style="Section.TLabelframe")
        target_frame.pack(fill="x", pady=(0, 12))
        target_frame.columnconfigure(0, weight=1)
        self.target_combo = ttk.Combobox(target_frame, textvariable=self.target_var, state="disabled")
        self.target_combo.grid(row=0, column=0, sticky="ew")
        self.target_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_preview())
        self.ffmpeg_label = ttk.Label(target_frame, text="")
        self.ffmpeg_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        options = ttk.LabelFrame(root, text="3. 儲存與品質", padding=14, style="Section.TLabelframe")
        options.pack(fill="x", pady=(0, 12))
        ttk.Radiobutton(
            options,
            text="另存新檔（保留原始檔）",
            variable=self.mode_var,
            value=ConversionMode.SAVE_AS.value,
            command=self._refresh_preview,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            options,
            text="取代原始檔（成功後移至資源回收筒）",
            variable=self.mode_var,
            value=ConversionMode.REPLACE_SOURCE.value,
            command=self._refresh_preview,
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Checkbutton(
            options,
            text="允許覆蓋已存在的輸出檔案",
            variable=self.overwrite_var,
            command=self._refresh_preview,
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Label(options, text="圖片品質").grid(row=0, column=1, padx=(30, 8), sticky="e")
        ttk.Scale(options, from_=50, to=100, variable=self.quality_var, orient="horizontal", length=160).grid(
            row=0, column=2, sticky="ew"
        )
        self.quality_label = ttk.Label(options, text="92")
        self.quality_label.grid(row=0, column=3, padx=(8, 0))
        self.quality_var.trace_add("write", self._quality_changed)

        preview = ttk.LabelFrame(root, text="轉換預覽", padding=14, style="Section.TLabelframe")
        preview.pack(fill="both", expand=True, pady=(0, 12))
        self.preview_text = tk.Text(preview, height=8, wrap="word", state="disabled", relief="flat")
        self.preview_text.pack(fill="both", expand=True)

        footer = ttk.Frame(root)
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var).pack(side="left", fill="x", expand=True)
        self.convert_button = ttk.Button(footer, text="開始轉換", command=self._start_conversion, state="disabled")
        self.convert_button.pack(side="right")

    def _quality_changed(self, *_args: object) -> None:
        self.quality_label.configure(text=str(round(self.quality_var.get())))
        self._refresh_preview()

    def _choose_source(self) -> None:
        filename = filedialog.askopenfilename(title="選擇要轉換的檔案")
        if not filename:
            return
        source = Path(filename)
        try:
            targets = self.engine.targets_for(source)
            source_extension = extension_for_path(source)
        except DotConvertError as exc:
            messagebox.showerror("不支援的檔案", str(exc), parent=self)
            return
        self.source_path = source
        self.source_var.set(f"{source.name}\n{source}")
        labels = [display_label(item) for item in targets]
        self.target_combo.configure(values=labels, state="readonly" if labels else "disabled")
        self.target_combo._extension_map = dict(zip(labels, targets, strict=True))  # type: ignore[attr-defined]
        if labels:
            preferred = next((label for label, ext in zip(labels, targets, strict=True) if ext != source_extension), labels[0])
            self.target_var.set(preferred)
            self.convert_button.configure(state="normal")
            self.status_var.set("已就緒。開始前會顯示所有已知風險。")
        else:
            self.target_var.set("")
            self.convert_button.configure(state="disabled")
            self.status_var.set("這是媒體檔案，但系統找不到 FFmpeg。")
        if source_extension in {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".mp4", ".mkv", ".webm", ".mov", ".avi"}:
            self.ffmpeg_label.configure(
                text="FFmpeg 已偵測。" if self.engine.ffmpeg_available() else "需要安裝 FFmpeg，或設定 DOTCONVERT_FFMPEG。"
            )
        else:
            self.ffmpeg_label.configure(text="")
        self._refresh_preview()

    def _selected_extension(self) -> str | None:
        mapping = getattr(self.target_combo, "_extension_map", {})
        return mapping.get(self.target_var.get())

    def _make_plan(self, destination: Path | None = None) -> ConversionPlan:
        if self.source_path is None:
            raise DotConvertError("請先選擇來源檔案。")
        extension = self._selected_extension()
        if extension is None:
            raise DotConvertError("請選擇輸出格式。")
        return ConversionPlan(
            source=self.source_path,
            target_extension=extension,
            destination=destination,
            mode=ConversionMode(self.mode_var.get()),
            overwrite_existing=self.overwrite_var.get(),
            image_quality=round(self.quality_var.get()),
        )

    def _refresh_preview(self) -> None:
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        try:
            plan = self._make_plan()
            destination = resolve_destination(plan)
            warnings = self.engine.warnings_for(plan)
            lines = [f"來源：{plan.source}", f"預設輸出：{destination}", ""]
            if warnings:
                lines.append("已知風險：")
                for warning in warnings:
                    marker = "高風險" if warning.severity == Severity.DANGER else "注意"
                    lines.append(f"• [{marker}] {warning.message}")
            else:
                lines.append("未偵測到已知的有損轉換風險。")
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
                    title="選擇輸出位置",
                    initialdir=suggested.parent,
                    initialfile=suggested.name,
                    defaultextension=extension,
                    filetypes=[(display_label(extension), f"*{extension}"), ("所有檔案", "*.*")],
                )
                if not chosen:
                    return
                plan = self._make_plan(Path(chosen))
            warnings = self.engine.warnings_for(plan)
        except DotConvertError as exc:
            messagebox.showerror("無法開始", str(exc), parent=self)
            return

        if warnings:
            details = "\n".join(f"• {warning.message}" for warning in warnings)
            if not messagebox.askyesno(
                "轉換前確認",
                f"請確認以下風險：\n\n{details}\n\n仍要執行轉換嗎？",
                icon="warning",
                parent=self,
            ):
                return

        self.convert_button.configure(state="disabled")
        self.status_var.set("正在轉換；原始檔在完成前不會被修改。")
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
            message = str(result) if isinstance(result, DotConvertError) else "發生未預期的錯誤；原始檔未被修改。"
            self.status_var.set("轉換失敗。")
            messagebox.showerror("轉換失敗", message, parent=self)
        else:
            source_note = "原始檔已移至資源回收筒。" if result.source_recycled else "原始檔已保留。"
            extra = ""
            recycle_warning = next((w.message for w in result.warnings if w.code == "recycle-failed"), None)
            if recycle_warning:
                extra = f"\n\n{recycle_warning}"
            self.status_var.set(f"完成：{result.destination.name}")
            messagebox.showinfo(
                "轉換完成",
                f"輸出檔案：\n{result.destination}\n\n{source_note}{extra}",
                parent=self,
            )
        self.after(120, self._poll_results)


def run_app() -> None:
    app = DotConvertApp()
    app.mainloop()
