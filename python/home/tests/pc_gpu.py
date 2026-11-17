"""The gpu-cdi line's calls on the PC and their answers, healthy unless a test changes one (tests/test_pc_gpu.py)."""

# The answers copy what the PC printed on 2026-11-16 (nvidia-container-toolkit 1.20.1, nvidia-utils 615.78.08-1,
# systemd, GNU find and stat under LC_ALL=C), cut to a few mounts, with the GPU's UUID and PCI address left out. The
# healthy PC is the one dotfiles declares: the refresh units enabled, Docker's /etc/cdi empty, NVIDIA's spec in
# /run/cdi. Each call's key is its argv as ssh sends it: every word quoted for the PC's shell.

import json
import shlex

REMOTE = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "pc", "--"]
C = ("env", "LC_ALL=C")


def call(*argv: str) -> str:
    """The stand-in's key for argv run on the PC."""
    return json.dumps([*REMOTE, *map(shlex.quote, argv)])


DIRS = ("/etc/cdi", "/run/cdi")
SPEC_FILE = "/run/cdi/nvidia.yaml"
LIBRARY = "/usr/lib/libcuda.so.615.78.08"
PATHS = (LIBRARY, "/usr/lib/libnvidia-ml.so.615.78.08", "/usr/bin/nvidia-smi")

PACMAN = call("pacman", "-Q", "nvidia-container-toolkit", "nvidia-utils")
UNITS = call(
    "systemctl",
    "show",
    "--property=Id,LoadState,UnitFileState,ActiveState,SubState,Result",
    "--",
    "nvidia-cdi-refresh.path",
    "nvidia-cdi-refresh.service",
)
DOCKER = call("docker", "--host", "unix:///var/run/docker.sock", "info", "--format", "{{json .CDISpecDirs}}")


def cdi_list(dirs: tuple[str, ...] = DIRS) -> str:
    return call("nvidia-ctk", "cdi", "list", *(arg for d in dirs for arg in ("--spec-dir", d)))


def find(dirs: tuple[str, ...] = DIRS) -> str:
    # What CDI reads: each entry one level down that is not a directory (a link to a spec is one), named *.yaml or
    # *.json.
    entries = (
        "-mindepth",
        "1",
        "-maxdepth",
        "1",
        "!",
        "-type",
        "d",
        "(",
        "-name",
        "*.yaml",
        "-o",
        "-name",
        "*.json",
        ")",
    )
    return call(*C, "find", "-H", *dirs, *entries, "-printf", r"\0%p\0", "-exec", "cat", "{}", ";")


def stat(paths: tuple[str, ...] = PATHS) -> str:
    return call(*C, "stat", "-L", "--printf", r"%n\0", "--", *paths)


MODULE = call("cat", "/proc/driver/nvidia/version")


def spec(*mounts: str, device_mounts: tuple[str, ...] = ()) -> str:
    """A CDI spec as nvidia-ctk cdi generate writes it, with mounts on the spec and on its "all" device."""

    def edits(paths: tuple[str, ...], indent: str) -> str:
        rows = "".join(
            f"{indent}    - hostPath: {path}\n{indent}      containerPath: {path}\n"
            f"{indent}      options:\n{indent}        - ro\n{indent}        - nosuid\n"
            for path in paths
        )
        return f"{indent}mounts:\n{rows}" if paths else ""

    device = "    - name: all\n      containerEdits:\n        deviceNodes:\n            - path: /dev/nvidia0\n"
    return (
        "---\ncdiVersion: 0.7.0\nkind: nvidia.com/gpu\ndevices:\n"
        + device
        + edits(device_mounts, "        ")
        + "containerEdits:\n"
        + edits(mounts, "    ")
    )


def pacman(*, toolkit: bool = True, utils: str | None = "615.78.08-1") -> dict[str, object]:
    rows = (["nvidia-container-toolkit 1.20.1-1"] if toolkit else []) + ([f"nvidia-utils {utils}"] if utils else [])
    missing = [name for name, here in (("nvidia-container-toolkit", toolkit), ("nvidia-utils", utils)) if not here]
    stderr = "".join(f"error: package '{name}' was not found\n" for name in missing)
    return {"stdout": "".join(f"{row}\n" for row in rows), "stderr": stderr, "code": 1 if missing else 0}


def unit(name: str, state: str, *, result: str = "success", load: str = "loaded") -> str:
    """One unit's block of systemctl show, in systemd's property order; state is UnitFileState/ActiveState/SubState."""
    unit_file, active, sub = state.split("/")
    values = {"LoadState": load, "ActiveState": active, "SubState": sub, "UnitFileState": unit_file, "Result": result}
    return f"Id={name}\n" + "".join(f"{key}={value}\n" for key, value in values.items())


PATH_WAITING = unit("nvidia-cdi-refresh.path", "enabled/active/waiting")
SERVICE_DONE = unit("nvidia-cdi-refresh.service", "enabled/inactive/dead")


def units(path: str = PATH_WAITING, service: str = SERVICE_DONE) -> dict[str, object]:
    return {"stdout": f"{path}\n{service}"}


FOUND = 'time="2026-11-16T17:15:27-06:00" level=info msg="Found 3 CDI devices"\n'


def listed(
    stderr: str = FOUND, devices: tuple[str, ...] = ("nvidia.com/gpu=0", "nvidia.com/gpu=all")
) -> dict[str, object]:
    return {"stdout": "".join(f"{d}\n" for d in devices), "stderr": stderr}


def found(specs: dict[str, str]) -> dict[str, object]:
    """find's answer: NUL, the spec's path, NUL, its text, for each spec."""
    return {"stdout": "".join(f"\0{name}\0{text}" for name, text in specs.items())}


def quoted(path: str) -> str:
    """A name as coreutils quotes it in a message: in single quotes, each quote in it as '\\''."""
    return "'" + path.replace("'", "'\\''") + "'"


def stated(
    paths: tuple[str, ...] = PATHS, missing: tuple[str, ...] = (), denied: tuple[str, ...] = ()
) -> dict[str, object]:
    """stat's answer: each readable path and a NUL, and one message per missing or unreadable path."""
    stdout = "".join(f"{path}\0" for path in paths if path not in missing + denied)
    stderr = "".join(f"stat: cannot statx {quoted(path)}: No such file or directory\n" for path in missing) + "".join(
        f"stat: cannot statx {quoted(path)}: Permission denied\n" for path in denied
    )
    return {"stdout": stdout, "stderr": stderr, "code": 1 if missing or denied else 0}


def module(version: str = "615.78.08") -> dict[str, object]:
    return {
        "stdout": f"NVRM version: NVIDIA UNIX Open Kernel Module for x86_64  {version}  Release Build  (builder)  \n"
        "GCC version:  gcc version 16.2.1 20260810 (GCC) \n"
    }


# NVIDIA's spec in /run/cdi, mounting PATHS: two on the spec, one on its device.
SPECS = found({SPEC_FILE: spec(*PATHS[:2], device_mounts=PATHS[2:])})

HEALTHY: dict[str, object] = {
    PACMAN: pacman(),
    UNITS: units(),
    DOCKER: {"stdout": json.dumps(list(DIRS)) + "\n"},
    cdi_list(): listed(),
    find(): SPECS,
    stat(): stated(),
    MODULE: module(),
}
