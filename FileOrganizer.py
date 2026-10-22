"""
SmartSort — Smart File Organizer
A beginner-friendly desktop file organizer built with Python's standard library.

Features:
- Graphical interface to choose a folder
- Preview before moving anything
- Organizes files by category
- Prevents overwriting duplicate filenames
- Undo the most recent organization batch
- Skips folders and its own history file
- Shows a summary and writes a small activity log

Run with: python SmartSort.py
Requires Python 3.9+ (Tkinter is usually included with Python on Windows).
"""

import json
import shutil
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "SmartSort"
HISTORY_FILENAME = ".smartsort_history.json"

CATEGORIES = {
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff",
        ".svg", ".heic", ".ico"
    },
    "Documents": {
        ".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".tex",
        ".ppt", ".pptx", ".odp", ".xls", ".xlsx", ".csv", ".ods"
    },
    "Videos": {
        ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".m4v", ".3gp"
    },
    "Audio": {
        ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".mid", ".midi"
    },
    "Archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"
    },
    "Code": {
        ".py", ".java", ".c", ".cpp", ".h", ".hpp", ".js", ".ts", ".html",
        ".css", ".php", ".sql", ".json", ".xml", ".yaml", ".yml", ".sh",
        ".bat", ".ps1", ".ipynb"
    },
    "Installers": {
        ".exe", ".msi", ".apk", ".deb", ".rpm", ".dmg", ".pkg"
    },
}

def category_for(path: Path) -> str:
    """Return a category based on a file's extension."""
    suffix = path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if suffix in extensions:
            return category
    return "Others"


def unique_destination(folder: Path, filename: str) -> Path:
    """Choose a non-existing destination rather than overwrite a file."""
    candidate = folder / filename
    if not candidate.exists():
        return candidate

    original = Path(filename)
    counter = 1
    while True:
        candidate = folder / f"{original.stem} ({counter}){original.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


class SmartSortApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SmartSort | Smart File Organizer")
        self.root.geometry("920x650")
        self.root.minsize(760, 520)
        self.root.configure(bg="#f3f5f9")

        self.selected_folder = tk.StringVar()
        self.status_text = tk.StringVar(value="Choose a folder to begin.")
        self.summary_text = tk.StringVar(value="No preview yet.")
        self.preview_items = []

        self._configure_style()
        self._build_ui()

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f3f5f9")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f3f5f9", foreground="#202638", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground="#263b70")
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#5e687c")
        style.configure("CardTitle.TLabel", background="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="✦ SmartSort", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="A safer, smarter way to tidy your folders — preview first, organize second.",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(3, 0))

        folder_card = ttk.Frame(outer, style="Card.TFrame", padding=14)
        folder_card.pack(fill="x", pady=(0, 12))
        ttk.Label(folder_card, text="1. Choose a folder", style="CardTitle.TLabel").pack(anchor="w")
        folder_row = ttk.Frame(folder_card, style="Card.TFrame")
        folder_row.pack(fill="x", pady=(9, 0))
        self.folder_entry = ttk.Entry(folder_row, textvariable=self.selected_folder)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(folder_row, text="Browse…", command=self.choose_folder).pack(side="left")
        ttk.Button(folder_row, text="Preview files", command=self.preview).pack(side="left", padx=(8, 0))

        preview_card = ttk.Frame(outer, style="Card.TFrame", padding=12)
        preview_card.pack(fill="both", expand=True)
        top_row = ttk.Frame(preview_card, style="Card.TFrame")
        top_row.pack(fill="x", pady=(0, 8))
        ttk.Label(top_row, text="2. Review the plan", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(top_row, textvariable=self.summary_text, background="#ffffff", foreground="#5e687c").pack(side="right")

        columns = ("filename", "category", "destination", "size")
        self.tree = ttk.Treeview(preview_card, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("filename", text="File name")
        self.tree.heading("category", text="Category")
        self.tree.heading("destination", text="Destination folder")
        self.tree.heading("size", text="Size")
        self.tree.column("filename", width=330, anchor="w")
        self.tree.column("category", width=115, anchor="center")
        self.tree.column("destination", width=180, anchor="w")
        self.tree.column("size", width=90, anchor="e")
        scrollbar = ttk.Scrollbar(preview_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=self.status_text).pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Undo last batch", command=self.undo_last_batch).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Organize files", style="Accent.TButton", command=self.organize).pack(side="right")

        ttk.Label(
            outer,
            text="Safety note: SmartSort only processes files directly inside the chosen folder. It does not delete files.",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(10, 0))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose a folder to organize")
        if folder:
            self.selected_folder.set(folder)
            self.preview()

    def _get_folder(self):
        raw = self.selected_folder.get().strip()
        if not raw:
            messagebox.showwarning("Choose a folder", "Please choose a folder first.")
            return None
        folder = Path(raw).expanduser()
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror("Folder not found", "The selected path is not a valid folder.")
            return None
        return folder.resolve()

    def _direct_files(self, folder: Path):
        # Deliberately non-recursive: avoids re-organizing files inside category folders.
        return sorted(
            (p for p in folder.iterdir()
             if p.is_file() and p.name != HISTORY_FILENAME and not p.name.startswith(".smartsort_tmp_")),
            key=lambda p: p.name.lower()
        )

    @staticmethod
    def _format_size(size):
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024

    def preview(self):
        folder = self._get_folder()
        if folder is None:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.preview_items = []
        files = self._direct_files(folder)
        counts = {}
        for path in files:
            category = category_for(path)
            counts[category] = counts.get(category, 0) + 1
            self.preview_items.append((path, category))
            self.tree.insert(
                "", "end",
                values=(path.name, category, category + "/", self._format_size(path.stat().st_size))
            )
        count_text = f"{len(files)} file(s)"
        category_text = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        self.summary_text.set(count_text + (f"  |  {category_text}" if category_text else ""))
        self.status_text.set("Preview ready. Nothing has been moved yet.")

    def organize(self):
        folder = self._get_folder()
        if folder is None:
            return
        files = self._direct_files(folder)
        if not files:
            messagebox.showinfo("Nothing to organize", "There are no files directly inside this folder.")
            return

        # Make the plan and ask for explicit confirmation before any move.
        plan = [(p, category_for(p)) for p in files]
        counts = {}
        for _, category in plan:
            counts[category] = counts.get(category, 0) + 1
        description = "\n".join(f"• {name}: {count} file(s)" for name, count in sorted(counts.items()))
        confirmed = messagebox.askyesno(
            "Confirm organization",
            f"SmartSort is ready to organize {len(plan)} file(s) in:\n{folder}\n\n"
            f"{description}\n\n"
            "Files will be moved into category folders. Existing files will not be overwritten.\n"
            "Continue?"
        )
        if not confirmed:
            self.status_text.set("Organization cancelled. No files were moved.")
            return

        moved_records = []
        errors = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for source, category in plan:
            try:
                destination_folder = folder / category
                destination_folder.mkdir(exist_ok=True)
                destination = unique_destination(destination_folder, source.name)
                shutil.move(str(source), str(destination))
                moved_records.append({"source": str(source), "destination": str(destination)})
            except (OSError, shutil.Error) as exc:
                errors.append(f"{source.name}: {exc}")

        history_path = folder / HISTORY_FILENAME
        try:
            history = []
            if history_path.exists():
                try:
                    history = json.loads(history_path.read_text(encoding="utf-8"))
                    if not isinstance(history, list):
                        history = []
                except (OSError, json.JSONDecodeError):
                    history = []
            history.append({"timestamp": timestamp, "moves": moved_records})
            history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except OSError as exc:
            errors.append(f"Could not save undo history: {exc}")

        self.preview()
        message = f"Organization complete.\n\nMoved: {len(moved_records)} file(s)\nErrors: {len(errors)}"
        if errors:
            message += "\n\nDetails:\n" + "\n".join(errors[:8])
        messagebox.showinfo("SmartSort result", message)
        self.status_text.set(f"Done: moved {len(moved_records)} file(s).")

    def undo_last_batch(self):
        folder = self._get_folder()
        if folder is None:
            return
        history_path = folder / HISTORY_FILENAME
        if not history_path.exists():
            messagebox.showinfo("Nothing to undo", "No SmartSort history was found for this folder.")
            return
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            messagebox.showerror("History error", "SmartSort could not read its history file.")
            return
        if not history:
            messagebox.showinfo("Nothing to undo", "There is no previous batch to undo.")
            return

        batch = history[-1]
        moves = batch.get("moves", [])
        if not moves:
            messagebox.showinfo("Nothing to undo", "The most recent batch contains no recorded moves.")
            return
        if not messagebox.askyesno(
            "Undo last batch",
            f"Return {len(moves)} file(s) to their original locations?\n\n"
            "If a source filename already exists, SmartSort will keep both files by choosing a new name."
        ):
            return

        restored = 0
        errors = []
        remaining_moves = []
        for record in reversed(moves):
            source = Path(record["source"])
            destination = Path(record["destination"])
            try:
                if not destination.exists():
                    # It may have been manually moved or deleted since organizing.
                    continue
                source.parent.mkdir(parents=True, exist_ok=True)
                safe_source = unique_destination(source.parent, source.name)
                shutil.move(str(destination), str(safe_source))
                restored += 1
            except (OSError, shutil.Error) as exc:
                errors.append(f"{destination.name}: {exc}")
                remaining_moves.append(record)

        # Remove this batch from history only when all its existing files were restored.
        if not remaining_moves:
            history.pop()
        else:
            batch["moves"] = list(reversed(remaining_moves))
            history[-1] = batch
        try:
            history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except OSError as exc:
            errors.append(f"Could not update history: {exc}")

        self.preview()
        message = f"Undo finished.\n\nRestored: {restored} file(s)"
        if errors:
            message += "\n\nSome files could not be restored:\n" + "\n".join(errors[:8])
        messagebox.showinfo("Undo result", message)
        self.status_text.set(f"Undo finished: restored {restored} file(s).")


def main():
    root = tk.Tk()
    SmartSortApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
