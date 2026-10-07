"""Generate one pinned CPU-validation notebook and archive older entry points."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = """from pathlib import Path
import datetime
import json
import os
import subprocess
import sys
import tempfile
import zipfile

REPO_REF = "__REF__"
workspace = Path(tempfile.mkdtemp(prefix="dccp-cpu-"))
repo = workspace / "repo"
venv = workspace / "venv"
subprocess.run(["git", "clone", "https://github.com/Virelion-Biotech/Virelion-DCCP.git", str(repo)], check=True)
subprocess.run(["git", "checkout", "--detach", REPO_REF], cwd=repo, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
assert actual == REPO_REF
subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
subprocess.run([str(python), "-m", "pip", "install", ".[test,validation,cardivex,cardisim]"], cwd=repo, check=True)
log_path = workspace / "pytest.log"
with log_path.open("w") as log:
    test = subprocess.run([str(python), "-m", "pytest", "-q", "--cov=dccp", "--cov-branch"], cwd=repo, stdout=log, stderr=subprocess.STDOUT)
print(log_path.read_text())
test.check_returncode()
subprocess.run([str(python), "scripts/validate_cpu.py"], cwd=repo, check=True)
report_path = repo / "validation/cpu/results.json"
report = json.loads(report_path.read_text())
assert report["passed"], report["checks"]
print("Empirical status:", report["empirical_validation"])
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
output = Path.cwd() / ("DCCP_CPU_Validation_" + stamp + ".zip")
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    archive.write(report_path, "results.json")
    archive.write(repo / "validation/data/GSE240848_host_subset.json", "GSE240848_host_subset.json")
    archive.write(repo / "docs/CPU_AUDIT.md", "CPU_AUDIT.md")
    archive.write(log_path, "pytest.log")
    archive.writestr("commit.txt", actual + "\\n")
print("Saved:", output)
try:
    from google.colab import files
except ImportError:
    pass
else:
    files.download(str(output))
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", required=True, help="Exact 40-character implementation commit")
    args = parser.parse_args()
    if len(args.ref) != 40 or any(c not in "0123456789abcdef" for c in args.ref):
        raise ValueError("Provide a full hexadecimal commit SHA")
    code = CODE.replace("__REF__", args.ref)
    compile(code, "<notebook>", "exec")
    target = ROOT / "notebooks/DCCP_CPU_Validation.ipynb"
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "cells": [
            {
                "cell_type": "markdown",
                "id": "scope",
                "metadata": {},
                "source": [
                    "# DCCP pinned CPU validation\n",
                    "Run the next cell in Colab or Jupyter with Python 3.10+. It creates a fresh isolated environment, verifies an exact source commit, installs pinned optional adapters, executes tests and the real-count fixture checks, and downloads results. No GPU is needed.\n",
                    "The report preserves OOD misses. Passing software checks does not establish empirical biological validation.\n",
                ],
            },
            {
                "cell_type": "code",
                "id": "run",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": code.splitlines(keepends=True),
            },
        ],
    }
    target.write_text(json.dumps(notebook, indent=2) + "\n")
    for path in (ROOT / "notebooks").glob("DCCP_Runtime_Validation*.ipynb"):
        archived = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": notebook["metadata"],
            "cells": [
                {
                    "cell_type": "markdown",
                    "id": "archive",
                    "metadata": {},
                    "source": [
                        "# Superseded validation entry point\n",
                        "Use [DCCP_CPU_Validation.ipynb](DCCP_CPU_Validation.ipynb). It replaces the historical mutable-main bug-hunt notebooks with a pinned, isolated, tested CPU workflow.\n",
                    ],
                }
            ],
        }
        path.write_text(json.dumps(archived, indent=2) + "\n")


if __name__ == "__main__":
    main()
