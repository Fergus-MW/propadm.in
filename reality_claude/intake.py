"""Discover case folders and read everything in them into one case record."""

import re
from pathlib import Path

from pypdf import PdfReader

TEXT = {".md", ".txt", ".csv", ".json", ".eml", ".html", ".htm", ".xml", ".yaml", ".yml"}
SPOILERS = re.compile(r"^## (Overview|Outcome)\s*\n.*?(?=^## |\Z)", re.M | re.S)


def natural(path):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name)]


def discover(root):
    """Each sub-folder is a case; a folder of loose files is one case per file."""
    root = Path(root)
    folders = sorted((p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")), key=natural)
    items = folders or sorted((p for p in root.iterdir() if p.is_file() and not p.name.startswith(".")),
                              key=natural)
    cases, used = [], set()
    for index, path in enumerate(items, 1):
        digits = re.sub(r"\D", "", path.stem if path.is_file() else path.name)
        answer_id = str(int(digits)) if digits else str(index)
        if answer_id in used:
            answer_id = str(index)
        used.add(answer_id)
        cases.append({"answer_id": answer_id, "path": path})
    return cases


def read_file(path):
    """Text, PDF text, or a note that the file could not be read."""
    suffix = path.suffix.lower()
    try:
        if suffix in TEXT:
            text = path.read_text(errors="replace")
        elif suffix == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        else:
            return None, "unreadable (unsupported format)"
    except Exception as error:  # a broken attachment must not stop the case
        return None, f"unreadable ({type(error).__name__})"
    return (text, "read") if text.strip() else (None, "empty or no extractable text")


def order(case_dir, path):
    rel = path.relative_to(case_dir).as_posix().lower()
    return (0 if rel == "index.md" else 1 if rel == "history.md" else 2, natural(path))


def read_case(case, hide_outcome=False):
    path = case["path"]
    files = [path] if path.is_file() else sorted(
        (p for p in path.rglob("*") if p.is_file() and not p.name.startswith(".")),
        key=lambda p: order(path, p))
    parts, inventory, title = [], [], path.stem if path.is_file() else path.name
    for file in files:
        rel = file.name if path.is_file() else file.relative_to(path).as_posix()
        text, status = read_file(file)
        if text and hide_outcome and rel.lower() == "index.md":
            text = SPOILERS.sub("", text)
        if text and rel.lower() in {"index.md", path.name.lower()}:
            heading = re.search(r"^# (.+)$", text, re.M)
            title = re.sub(r"^case\s+\d+\s*[:\-]\s*", "", heading.group(1).strip(), flags=re.I) if heading else title
        inventory.append({"file": rel, "bytes": file.stat().st_size, "status": status,
                          "chars": len(text) if text else 0})
        parts.append(f"===== {rel} =====\n" + (text.strip() if text else f"[{status}]"))
    body = "\n\n".join(parts)
    stamps = re.findall(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)", body)
    return {**case, "title": title, "text": body, "files": inventory,
            "events": len(re.findall(r'<a id="event-\d+"></a>', body)),
            "case_time": max(stamps) + " UTC" if stamps else None}
