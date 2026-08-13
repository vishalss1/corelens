"""Build C/C++ binaries with Clang and record exact compiler invocations."""
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def build_matrix(source, output_dir, compiler="clang++", levels=("O0", "O2", "O3"), flags=()):
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError(f"source file does not exist: {source}")
    if not levels or any(level not in ("O0", "O1", "O2", "O3", "Os", "Oz") for level in levels):
        raise ValueError("unsupported optimization level")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([compiler, "--version"], capture_output=True, text=True, timeout=15, check=False)
    if version.returncode:
        raise RuntimeError(version.stderr)
    builds = []
    for level in levels:
        binary = output_dir / (f"{source.stem}-{level}" + (".exe" if platform.system() == "Windows" else ""))
        # C sources use the compiler's C language mode even when the driver is clang++.
        language = ["-x", "c", "-std=c11"] if source.suffix.lower() == ".c" else ["-std=c++17"]
        command = [compiler, *language, f"-{level}", "-g", *flags, str(source), "-o", str(binary)]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
        if completed.returncode:
            raise RuntimeError(f"compilation failed for {level}: {completed.stderr}")
        builds.append({"name": level, "binary": str(binary), "command": command, "diagnostics": completed.stderr,
                       "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()})
    manifest = {"schema_version": 1, "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "compiler_version": version.stdout.strip(), "flags": list(flags), "builds": builds}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
