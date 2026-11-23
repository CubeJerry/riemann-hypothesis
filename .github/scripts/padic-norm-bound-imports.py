#!/usr/bin/env python3
"""Measure fresh Lake builds of the p-adic norm bound on each locked toolchain."""

import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time


TARGETS = ("Lemmata.FirstBlockLemmaF.Imports",)
PATHS = {name: Path("src", *name.split(".")).with_suffix(".lean") for name in TARGETS}
IMPORT = re.compile(r"^(?:public |meta )*import (?:all )?([^/\s]+)", re.M)


def git(*args):
    return subprocess.check_output(["git", *args])


def source_at(revision, path):
    return git("show", f"{revision}:{path.as_posix()}")


def write_report(report):
    path = Path(os.environ["BENCH_OUTPUT"])
    path.mkdir(parents=True, exist_ok=True)
    (path / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    return path


def local_importers():
    pattern = "^[[:space:]]*((public|meta)[[:space:]]+)*import[[:space:]].*Lemmata[.]FirstBlockLemmaF[.]Imports"
    found = subprocess.run(
        ["git", "grep", "-l", "-E", pattern, "HEAD", "--", "src"],
        check=False, stdout=subprocess.PIPE, text=True,
    )
    if found.returncode not in (0, 1):
        found.check_returncode()
    paths = [Path(line.removeprefix("HEAD:")) for line in found.stdout.splitlines()]
    return {str(path): list(IMPORT.findall(path.read_text())) for path in paths}


def clean_target(module):
    relative = Path(*module.split("."))
    for directory in (Path(".lake/build/lib/lean") / relative.parent,
                      Path(".lake/build/ir") / relative.parent):
        for output in directory.glob(relative.name + ".*"):
            if output.is_file():
                output.unlink()


def compile_target(module, variant, repetition, output):
    clean_target(module)
    log = output / f"{module}.{variant}.{repetition}.log"
    env = dict(os.environ, LEAN_NUM_THREADS="1", LEAN_ABORT_ON_PANIC="1",
               LAKE_ARTIFACT_CACHE="false", LAKE_RESTORE_ARTIFACTS="false")
    start = time.monotonic()
    with log.open("w") as stream:
        process = subprocess.run(["lake", "--rehash", "build", "+" + module],
                                 stdout=stream, stderr=subprocess.STDOUT, env=env, check=False)
    elapsed = time.monotonic() - start
    text = log.read_text()
    artifact = Path(".lake/build/lib/lean", *module.split(".")).with_suffix(".olean")
    if (process.returncode or "Built " + module + " " not in text or "Restored " + module + " " in text
            or "Build completed successfully" not in text or not artifact.is_file()):
        print(text[-16000:], flush=True)
        raise RuntimeError(f"Failed to freshly build {module} ({variant}), see {log}")
    return {
        "wall_seconds": elapsed,
        "olean_bytes": artifact.stat().st_size,
        "warnings": text.count("warning:"),
        "project_modules_built": [
            match for match in re.findall(r"\bBuilt ([\w.]+)", text)
            if Path("src", *match.split(".")).with_suffix(".lean").exists()
        ],
    }


def main():
    base, head, mathlib = sys.argv[1:]
    assert git("rev-parse", "HEAD").decode().strip() == head
    assert git("rev-parse", head + "^").decode().strip() == base
    assert set(git("diff", "--name-only", base, head).decode().splitlines()) == {
        p.as_posix() for p in PATHS.values()
    }
    manifest = json.loads(Path("lake-manifest.json").read_text())
    assert next(p["rev"] for p in manifest["packages"] if p["name"] == "mathlib") == mathlib
    assert subprocess.check_output(
        ["git", "-C", ".lake/packages/mathlib", "rev-parse", "HEAD"], text=True
    ).strip() == mathlib

    revisions = {"before": base, "after": head}
    sources = {
        version: {module: source_at(revision, path) for module, path in PATHS.items()}
        for version, revision in revisions.items()
    }
    for module in TARGETS:
        def body(data):
            return data.split(b"@[expose] public section\n", 1)[1]
        assert body(sources["before"][module]) == body(sources["after"][module])

    result = {
        "status": "started",
        "revisions": revisions,
        "mathlib": mathlib,
        "lean_version": subprocess.check_output(["lean", "--version"], text=True).strip(),
        "cpu": next(line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")),
        "direct_project_importers": local_importers(),
        "targets": {},
    }
    output = write_report(result)
    assert list(result["direct_project_importers"]) == [
        "src/Formalism/LocalToGlobal/GroupLattices/PendingLemmas/WittFractionToCpAlgebraMap.lean"
    ]
    try:
        for module, path in PATHS.items():
            versions = {}
            for version in revisions:
                imports = IMPORT.findall(sources[version][module].decode())
                versions[version] = {
                    "direct_imports": imports,
                    "samples": [],
                }
            result["targets"][module] = versions
            for repetition in range(4):
                order = ("before", "after") if repetition % 2 == 0 else ("after", "before")
                for version in order:
                    path.write_bytes(sources[version][module])
                    sample = compile_target(module, version, repetition, output)
                    versions[version]["samples"].append(sample)
                    print(module, version, sample, flush=True)
                    write_report(result)
            for data in versions.values():
                data["median_wall_seconds"] = statistics.median(
                    sample["wall_seconds"] for sample in data["samples"][1:]
                )
                assert len({sample["olean_bytes"] for sample in data["samples"]}) == 1
            path.write_bytes(sources["after"][module])
        result["consumer_builds"] = {}
        for importer in result["direct_project_importers"]:
            name = ".".join(Path(importer).relative_to("src").with_suffix("").parts)
            result["consumer_builds"][name] = compile_target(name, "after", 0, output)
        result["status"] = "passed"
        summary = {
            "status": result["status"],
            "lean_version": result["lean_version"],
            "cpu": result["cpu"],
            "targets": {
                module: {variant: {
                    "direct": len(data["direct_imports"]),
                    "wall_seconds": data["median_wall_seconds"],
                    "olean_bytes": data["samples"][0]["olean_bytes"],
                    "warnings": data["samples"][0]["warnings"],
                } for variant, data in versions.items()}
                for module, versions in result["targets"].items()
            },
            "consumer_builds": result["consumer_builds"],
        }
        print("BENCHMARK_RESULT", json.dumps(summary), flush=True)
    except Exception as error:
        result.update(status="failed", error=str(error))
        raise
    finally:
        write_report(result)
        for module, path in PATHS.items():
            path.write_bytes(sources["after"][module])


if __name__ == "__main__":
    main()
