"""Public-source guard for repository files (not a full secret/permission audit).

Checks Git-tracked and non-ignored untracked text files; local caches stay out.
Only names/line numbers of matches are printed, never matching secret values.
"""

from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
files = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
).decode().split("\0")
# Secret-like markers are assembled so the guard does not flag itself.
private_key = "-----BEGIN " + "PRIVATE KEY-----"
patterns = [re.compile(re.escape(private_key)),
            re.compile(r"https?://[^\s\"')<>]+"),
            re.compile(r"(?:/Users/|[A-Z]:\\\\Users\\\\)", re.I)]
failed = False
for name in filter(None, files):
    path = ROOT / name
    if not path.is_file():
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"Binary file requires manual review: {name}")
        failed = True
        continue
    if name == "scripts/check-public.py":
        continue
    for line_number, line in enumerate(text.splitlines(), 1):
        if patterns[0].search(line) or patterns[2].search(line):
            print(f"Potential private material: {name}:{line_number}")
            failed = True
        for match in patterns[1].finditer(line):
            host = urlparse(match.group()).hostname or ""
            if host.endswith((".corp", ".internal", ".local")):
                print(f"Private host requires review: {name}:{line_number}")
                failed = True
    if name.endswith("package-lock.json"):
        import json
        lock = json.loads(text)
        for record in lock.get("packages", {}).values():
            resolved = record.get("resolved", "")
            if resolved and urlparse(resolved).hostname != "registry.npmjs.org":
                print("Non-public registry resolution in lockfile")
                failed = True
print("Public-source guard:", "FAILED" if failed else "passed")
sys.exit(1 if failed else 0)
