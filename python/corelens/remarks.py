"""Summarize LLVM YAML remark documents without pretending to be a YAML parser.

The complete record remains available on disk; scalar fields and source-location
text are extracted for display. Nested Args are preserved verbatim.
"""
import re
from pathlib import Path


def read_remarks(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    documents = re.split(r"^--- !", text, flags=re.MULTILINE)
    remarks = []
    for document in documents[1:]:
        kind = document.splitlines()[0].strip()
        if kind not in ("Passed", "Missed", "Analysis", "AnalysisFPCommute", "AnalysisAliasing", "Failure"):
            continue
        entry = {"kind": kind}
        for key in ("Pass", "Name", "Function", "DebugLoc", "Hotness"):
            match = re.search(r"^" + key + r":\s*(.+)$", document, re.MULTILINE)
            if match:
                entry[key.lower()] = match.group(1).strip()
        args = re.search(r"^Args:\s*\n(.*?)(?:^\.\.\.|\Z)", document, re.MULTILINE | re.DOTALL)
        if args:
            entry["arguments_yaml"] = args.group(1).strip()
        remarks.append(entry)
    return {"record": str(Path(path).resolve()), "remarks": remarks,
            "note": "Display summary only; consult the original YAML for full nested arguments and exact locations."}
