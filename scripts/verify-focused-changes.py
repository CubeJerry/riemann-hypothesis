#!/usr/bin/env python3
"""Compile independent source changes against one pinned upstream base."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    base = os.environ["VERIFY_BASE"]
    head = os.environ["VERIFY_HEAD"]
    cases = json.loads(Path(__file__).with_suffix(".json").read_text())
    selection = os.environ.get("VERIFY_CASES", "all").split(",")
    if selection != ["all"]:
        cases = [c for c in cases if c["id"] in selection]
    assert cases, "No cases selected"
    evidence = Path(os.environ["RUNNER_TEMP"]) / "targeted-build-evidence"
    evidence.mkdir(exist_ok=True)
    results = []
    for case in cases:
        assert case["targets"], "An explicit target list is required"
        assert all(p.startswith("src/") and p.endswith(".lean") for p in case["files"])
        subprocess.run(["git", "reset", "--hard", base], check=True)
        subprocess.run(["git", "restore", "--source=" + head, "--", *case["files"]], check=True)
        changed = git("diff", "--name-only").splitlines()
        assert set(changed) == set(case["files"]), (case["id"], changed)
        subprocess.run(["git", "diff", "--check"], check=True)
        patch = git("diff", "--binary")
        assert not re.search(r"^\+(?!\+).*\b(sorry|admit|axiom|unsafe)\b", patch, re.M)
        (evidence / (case["id"] + ".patch")).write_text(patch + "\n")
        hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in case["files"]}
        command = ["lake", "build", *case["targets"]]
        print("::group::" + case["id"] + " — " + " ".join(command), flush=True)
        started = time.monotonic()
        log_path = evidence / (case["id"] + ".log")
        with log_path.open("w") as log:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, bufsize=1)
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            code = process.wait()
        uses_sorry = bool(re.search(r"declaration uses .sorry.", log_path.read_text()))
        result = {**case, "base": base, "source_head": head, "sha256": hashes,
                  "exit_code": code, "sorry_warning": uses_sorry,
                  "seconds": round(time.monotonic() - started, 2)}
        results.append(result)
        (evidence / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(result), flush=True)
        print("::endgroup::", flush=True)
    subprocess.run(["git", "reset", "--hard", base], check=True)
    failed = [r["id"] for r in results if r["exit_code"] or r["sorry_warning"]]
    print("FAILED: " + ", ".join(failed) if failed else "All selected target builds passed.", flush=True)
    raise SystemExit(bool(failed))


if __name__ == "__main__":
    main()
