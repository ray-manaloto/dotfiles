"""A local mise stand-in for upgrade tests; all inputs and writes belong to the temporary HOME."""

# The real mise would consult the user's configs/store and download releases. This stand-in uses the
# fixture's file:// releases instead. HOME/mise-{command}.json overrides a JSON response; mise-fail and
# mise-warning exercise lookup failure/warnings. Like the CBM stand-in, it records only context needed
# by the tests, never the whole inherited environment. Later tickets exercise it through cbm upgrade.
# Contracts: mise v2026.11.0 src/cli/install.rs:640-675; src/cli/ls.rs:270-313,605-628,778-812;
# src/cli/config/ls.rs:130-140; src/toolset/tool_source.rs:55-58.
MISE = r"""
import io, json, os, shutil, sys, tarfile, tomllib
from pathlib import Path
from urllib.request import urlopen

home = Path(os.environ["HOME"])
args = sys.argv[1:]
with (home / "mise-calls.jsonl").open("a") as stream:
    stream.write(json.dumps({"args": args, "cwd": str(Path.cwd()), "launcher": sys.argv[0],
                            "home": str(home), "runtime": os.getenv("CBM_RUNTIME_DIR"),
                            "cache": os.getenv("CBM_CACHE_DIR")}) + "\n")
if (home / "mise-fail").exists():
    print("mise: fixture failure", file=sys.stderr)
    sys.exit(1)
if (home / "mise-warning").exists():
    print("mise WARN fixture lookup incomplete", file=sys.stderr)
fixture = json.loads((home / "mise-fixture.json").read_text())
tool = "github:DeusData/codebase-memory-mcp"
if args == ["--version"]:
    print("mise 2026.11.0"); sys.exit(0)
if not args:
    sys.exit(64)
operation = args[0]
override = home / f"mise-{operation}.json"
if override.exists():
    print(override.read_text()); sys.exit(0)
if operation == "outdated":
    print(json.dumps({tool: {"requested": "9.9.9", "current": "9.9.9", "latest": "9.9.10", "bump": "9.9.10"}}))
elif args == ["config", "ls", "--json"]:
    print(json.dumps(fixture["configs"]))
elif operation == "ls":
    declared = {tomllib.loads(Path(config["path"]).read_text())["tools"][tool]: config["path"]
                for config in fixture["configs"] if tool in config["tools"]}
    rows = []
    for version, data in fixture["releases"].items():
        installed = Path(data["installed"]).exists()
        active = version in declared
        if not installed and not active:
            continue
        row = {"version": version, "install_path": data["installed"], "installed": installed, "active": active}
        if active:
            row.update(requested_version=version, source={"type": "mise.toml", "path": declared[version]})
        rows.append(row)
    filters = [arg for arg in args[1:] if not arg.startswith("-")]
    print(json.dumps((rows if tool in filters else []) if filters else {tool: rows}))
elif operation in ("where", "lock", "install"):
    spec = next((arg for arg in args[1:] if arg.startswith(tool)), tool + "@9.9.9")
    version = spec.split("@", 1)[1] if "@" in spec else "9.9.9"
    release = fixture["releases"][version]
    if operation == "where":
        print(release["installed"])
    elif operation == "lock":
        platforms = args[args.index("--platform") + 1].split(",") if "--platform" in args else ["macos-arm64"]
        text = f'[[tools."{tool}"]]\nversion = "{version}"\nbackend = "{tool}"\nspecifiers = ["{version}"]\n'
        for platform in platforms:
            text += f'\n[tools."{tool}"."platforms.{platform}"]\n'
            text += f'checksum = "sha256:{release["sha256"]}"\nurl = "{release["url"]}"\n'
        Path(fixture["lockfile"]).write_text(text)
    else:
        target = Path(release["installed"])
        if target.exists():
            if "--force" not in args and "-f" not in args:
                sys.exit(0)
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        with urlopen(release["url"]) as download, tarfile.open(fileobj=io.BytesIO(download.read())) as archive:
            archive.extractall(target, filter="data")
else:
    sys.exit(64)
"""
