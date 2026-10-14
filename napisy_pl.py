from __future__ import annotations

import json
import queue
import shutil
import subprocess
import threading
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Napisy PL"
VIDEO_TYPES = [
    ("Pliki wideo", "*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.mpeg *.mpg"),
    ("Wszystkie pliki", "*.*"),
]

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None


def srt_time(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def translate_segment(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    translator = GoogleTranslator(source="auto", target="pl")
    # Keep individual requests modest and preserve words at split boundaries.
    chunks = []
    while len(text) > 3500:
        cut = text.rfind(" ", 0, 3500)
        if cut < 1:
            cut = 3500
        chunks.append(text[:cut])
        text = text[cut:].strip()
    if text:
        chunks.append(text)
    return " ".join((translator.translate(chunk) or chunk) for chunk in chunks)


class NapisyPLApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Napisy PL")
        self.root.geometry("800x590")
        self.root.minsize(700, 520)
        self.events: queue.Queue = queue.Queue()
        self.worker = None
        self.cancel_event = threading.Event()
        self.video = tk.StringVar()
        self.model_size = tk.StringVar(value="small")
        self.device = tk.StringVar(value="cpu")
        self.embed_subs = tk.BooleanVar(value=False)
        self.keep_original = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Gotowy. Wybierz film, aby rozpocząć.")
        self.progress = tk.DoubleVar(value=0)
        self.detected = tk.StringVar(value="Język źródłowy: —")
        self.output = tk.StringVar(value="Folder wynikowy: taki sam jak film")
        self._build_ui()
        self.root.after(150, self._poll_events)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Napisy PL", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Automatyczne rozpoznawanie mowy i tłumaczenie dialogów na język polski",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 16))

        file_frame = ttk.LabelFrame(outer, text="Film źródłowy", padding=10)
        file_frame.pack(fill="x")
        row = ttk.Frame(file_frame)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.video).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Wybierz…", command=self.choose_video).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="Otwórz folder", command=self.open_folder).pack(side="left", padx=(8, 0))

        options = ttk.LabelFrame(outer, text="Ustawienia", padding=10)
        options.pack(fill="x", pady=12)
        ttk.Label(options, text="Model Whisper:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            options, textvariable=self.model_size,
            values=("tiny", "base", "small", "medium", "large-v3"),
            state="readonly", width=13
        ).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(options, text="Urządzenie:").grid(row=0, column=2, sticky="w", padx=(20, 8), pady=4)
        ttk.Combobox(
            options, textvariable=self.device,
            values=("cpu", "cuda"), state="readonly", width=10
        ).grid(row=0, column=3, sticky="w", pady=4)
        ttk.Label(
            options,
            text="tiny/base = szybciej; medium/large-v3 = zwykle dokładniej. CUDA wymaga zgodnego GPU i bibliotek.",
            wraplength=690
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(3, 7))
        ttk.Checkbutton(
            options, text="Utwórz dodatkowo film MP4 z napisami wtopionymi w obraz (wymaga FFmpeg)",
            variable=self.embed_subs
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=3)
        ttk.Checkbutton(
            options, text="Zachowaj oryginalne ścieżki audio w pliku wynikowym",
            variable=self.keep_original
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=3)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(2, 12))
        self.start_btn = ttk.Button(actions, text="Generuj polskie napisy", command=self.start)
        self.start_btn.pack(side="left")
        self.cancel_btn = ttk.Button(actions, text="Anuluj", command=self.cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)
        ttk.Button(actions, text="Pomoc", command=self.show_help).pack(side="right")

        progress_frame = ttk.LabelFrame(outer, text="Postęp", padding=10)
        progress_frame.pack(fill="x")
        ttk.Progressbar(progress_frame, variable=self.progress, maximum=100).pack(fill="x")
        ttk.Label(progress_frame, textvariable=self.status, wraplength=730).pack(anchor="w", pady=(8, 2))
        ttk.Label(progress_frame, textvariable=self.detected).pack(anchor="w")
        ttk.Label(outer, textvariable=self.output, foreground="#555").pack(anchor="w", pady=(10, 0))

        footer = (
            "Rozpoznawanie mowy działa lokalnie. Tłumaczenie przez Google Translate wymaga internetu "
            "i wysyła rozpoznany tekst do usługi tłumaczącej. Pierwsze uruchomienie pobiera model Whisper."
        )
        ttk.Label(outer, text=footer, wraplength=740, foreground="#666").pack(anchor="w", side="bottom", pady=(14, 0))

    def choose_video(self):
        path = filedialog.askopenfilename(title="Wybierz film", filetypes=VIDEO_TYPES)
        if path:
            self.video.set(path)
            self.output.set(f"Folder wynikowy: {Path(path).parent}")

    def open_folder(self):
        path = self.video.get().strip()
        folder = str(Path(path).parent) if path else str(Path.home())
        try:
            import os
            os.startfile(folder)
        except Exception as exc:
            messagebox.showerror("Nie można otworzyć folderu", str(exc))

    def show_help(self):
        messagebox.showinfo(
            "Pomoc — Napisy PL",
            "1. Wybierz plik wideo.\n"
            "2. Wybierz model. Na początek polecam „small”.\n"
            "3. Kliknij „Generuj polskie napisy”.\n\n"
            "Program zapisze obok filmu plik NAZWA.pl.srt.\n"
            "Opcja FFmpeg tworzy też NAZWA.napisy_PL.mp4.\n\n"
            "Tłumaczenie wymaga internetu. Czas pracy zależy od długości filmu, modelu i komputera."
        )

    def start(self):
        path = Path(self.video.get().strip())
        if not path.is_file():
            messagebox.showwarning("Wybierz film", "Wybierz istniejący plik wideo.")
            return
        if WhisperModel is None:
            messagebox.showerror(
                "Brak biblioteki",
                "Nie znaleziono faster-whisper.\nUruchom plik INSTALL_AND_RUN.bat albo wykonaj:\n"
                "python -m pip install -r requirements.txt"
            )
            return
        if GoogleTranslator is None:
            messagebox.showerror(
                "Brak biblioteki",
                "Nie znaleziono deep-translator.\nUruchom plik INSTALL_AND_RUN.bat albo wykonaj:\n"
                "python -m pip install -r requirements.txt"
            )
            return
        if self.embed_subs.get() and shutil.which("ffmpeg") is None:
            messagebox.showerror(
                "Brak FFmpeg",
                "Nie znaleziono FFmpeg w PATH. Zainstaluj FFmpeg i uruchom ponownie program "
                "albo odznacz opcję wtapiania napisów."
            )
            return
        self.cancel_event.clear()
        self.progress.set(0)
        self.detected.set("Język źródłowy: wykrywanie…")
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.worker = threading.Thread(target=self.process, args=(path,), daemon=True)
        self.worker.start()

    def cancel(self):
        self.cancel_event.set()
        self.status.set("Zgłoszono anulowanie. Program zakończy pracę przy najbliższej bezpiecznej okazji.")

    def emit(self, kind, value=None):
        self.events.put((kind, value))

    def process(self, video: Path):
        try:
            model_name = self.model_size.get()
            device = self.device.get()
            self.emit("status", ("Ładowanie modelu Whisper… (pierwsze uruchomienie może pobrać kilka GB)", 2))
            if device == "cuda":
                model = WhisperModel(model_name, device="cuda", compute_type="float16")
            else:
                model = WhisperModel(model_name, device="cpu", compute_type="int8")

            self.emit("status", ("Analizowanie dźwięku i automatyczne wykrywanie języka…", 8))
            segments, info = model.transcribe(
                str(video), language=None, vad_filter=True, beam_size=5
            )
            source_lang = info.language or "nieznany"
            probability = getattr(info, "language_probability", None)
            self.emit("language", f"Język źródłowy: {source_lang}" +
                      (f" (pewność {probability:.0%})" if probability is not None else ""))

            output_srt = video.with_name(video.stem + ".pl.srt")
            rows = []
            for seg in segments:
                if self.cancel_event.is_set():
                    raise InterruptedError("Operacja została anulowana.")
                original = (seg.text or "").strip()
                if not original:
                    continue
                self.emit("status", (f"Tłumaczenie fragmentu {len(rows) + 1}…", min(88, 12 + len(rows) % 75)))
                translated = translate_segment(original)
                rows.append(
                    f"{len(rows) + 1}\n{srt_time(seg.start)} --> {srt_time(seg.end)}\n{translated}\n"
                )

            if not rows:
                raise RuntimeError("Nie wykryto mowy. Sprawdź, czy film zawiera słyszalne dialogi.")

            output_srt.write_text("\n".join(rows), encoding="utf-8-sig")
            final_files = [str(output_srt)]

            if self.embed_subs.get():
                self.emit("status", ("Tworzenie filmu z napisami wtopionymi w obraz…", 92))
                out_video = video.with_name(video.stem + ".napisy_PL.mp4")
                subpath = str(output_srt.resolve()).replace("\\", "/")
                if len(subpath) > 1 and subpath[1] == ":":
                    subpath = subpath[0] + r"\:" + subpath[2:]
                subpath = subpath.replace("'", r"\'")
                cmd = ["ffmpeg", "-y", "-i", str(video), "-vf", f"subtitles='{subpath}'"]
                if self.keep_original.get():
                    cmd += ["-c:a", "copy"]
                else:
                    cmd += ["-c:a", "aac", "-b:a", "192k"]
                cmd.append(str(out_video))
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode:
                    raise RuntimeError("FFmpeg nie utworzył filmu:\n" + result.stderr[-2500:])
                final_files.append(str(out_video))

            self.emit("done", (source_lang, final_files))
        except InterruptedError as exc:
            self.emit("cancelled", str(exc))
        except Exception as exc:
            log = Path.home() / "NapisyPL_error.log"
            try:
                log.write_text(traceback.format_exc(), encoding="utf-8")
            except Exception:
                pass
            self.emit("error", f"{exc}\n\nSzczegóły zapisano w: {log}")
        finally:
            self.emit("finished", None)

    def _poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    message, percent = value
                    self.status.set(message)
                    self.progress.set(percent)
                elif kind == "language":
                    self.detected.set(value)
                elif kind == "done":
                    lang, files = value
                    self.progress.set(100)
                    self.status.set("Zakończono pomyślnie.")
                    self.output.set("Wyniki: " + " | ".join(files))
                    messagebox.showinfo("Gotowe", "Wykryty język: " + lang + "\n\nUtworzono:\n" + "\n".join(files))
                elif kind == "cancelled":
                    self.status.set(value)
                elif kind == "error":
                    self.status.set("Wystąpił błąd.")
                    messagebox.showerror("Błąd", value)
                elif kind == "finished":
                    self.start_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_events)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    NapisyPLApp(root)
    root.mainloop()
