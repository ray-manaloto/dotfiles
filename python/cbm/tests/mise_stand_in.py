"""A local mise stand-in that installs test releases; all inputs and writes belong to the temporary HOME."""

# The real mise would consult the user's configs/store and download releases. This stand-in installs the
# fixture's file:// releases instead, and records each call so a test can show that cbm never runs mise.
# Contract: mise v2026.11.0 src/cli/install.rs:640-675 (an installed version is kept unless --force).
MISE = r"""
import io, json, os, shutil, sys, tarfile
from pathlib import Path
from urllib.request import urlopen

home = Path(os.environ["HOME"])
args = sys.argv[1:]
with (home / "mise-calls.jsonl").open("a") as stream:
    stream.write(json.dumps({"args": args, "cwd": str(Path.cwd())}) + "\n")
if not args or args[0] != "install":
    sys.exit(64)
tool = "github:DeusData/codebase-memory-mcp"
spec = next(arg for arg in args[1:] if arg.startswith(tool + "@"))
release = json.loads((home / "mise-fixture.json").read_text())["releases"][spec.split("@", 1)[1]]
target = Path(release["installed"])
if target.exists():
    if "--force" not in args and "-f" not in args:
        sys.exit(0)
    shutil.rmtree(target)
target.mkdir(parents=True)
with urlopen(release["url"]) as download, tarfile.open(fileobj=io.BytesIO(download.read())) as archive:
    archive.extractall(target, filter="data")
"""
