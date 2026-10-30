"""p2996 verify: clang++-p2996 loads its default config, then compiles and runs reflection.cpp."""

import os
import subprocess
import tempfile
from pathlib import Path

from .config import RESOURCES, bin_dir
from .models import Config


def run(cfg: Config, sample: Path = RESOURCES / "reflection.cpp", expect: str = "reflection value=43") -> None:
    cxx = str(bin_dir(cfg) / "clang++-p2996")
    env = {k: v for k, v in os.environ.items() if k not in ("SDKROOT", "CLANG_NO_DEFAULT_CONFIG")}
    version = subprocess.run([cxx, "--version"], check=True, capture_output=True, text=True, env=env).stdout
    if "/arm64-apple-darwin-clang++.cfg" not in version:
        msg = f"p2996 verify: {cxx} does not load arm64-apple-darwin-clang++.cfg"
        raise SystemExit(msg)
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "reflection"
        subprocess.run([cxx, "-std=c++26", "-freflection", str(sample), "-o", str(exe)], check=True, env=env)
        out = subprocess.run([exe], check=True, capture_output=True, text=True).stdout.strip()
    if out != expect:
        msg = f"p2996 verify: sample printed {out!r}"
        raise SystemExit(msg)
    print(f"p2996 verify OK: {version.splitlines()[0]}")
