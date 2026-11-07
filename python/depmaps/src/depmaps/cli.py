"""The depmaps CLI: list, map, sync and diff the dependency maps of the registry."""

import sys
from collections.abc import Sequence

from . import config, registry, store
from .diff import changes, files
from .events import DepmapsError, emit
from .models import Command, Config, DepStatus, Done, Error, ErrorCode, Mapped, Pruned, Request

USAGE = "usage: depmaps list | map <dep> [--version <version>] | sync | diff <dep> <old> <new>"


def parse(args: Sequence[str]) -> Request:
    match list(args):
        case ["list" | "sync" as name]:
            return Request(command=Command(name), args=[])
        case ["map", dep]:
            return Request(command=Command.map, args=[dep])
        case ["map", dep, "--version", version] if registry.VERSION.fullmatch(version):
            return Request(command=Command.map, args=[dep], version=version)
        case ["diff", dep, old, new] if registry.VERSION.fullmatch(old) and registry.VERSION.fullmatch(new):
            return Request(command=Command.diff, args=[dep, old, new])
        case _:
            raise ValueError(USAGE)


def suffix(failed: int) -> str:
    return f"; {failed} failed" if failed else ""


def run_list(cfg: Config) -> tuple[str, int]:
    failed = mapped = 0
    deps = registry.load(cfg).deps
    for name, entry in deps.items():
        try:
            version = registry.pinned(cfg, name, entry)
            has = store.mapped(cfg, name, version)
        except DepmapsError as failure:
            emit(Error(code=failure.code, message=str(failure)))
            failed += 1
            continue
        mapped += has
        emit(DepStatus(dep=name, version=version, mapped=has))
    return f"depmaps: {len(deps)} deps, {mapped} mapped at the pinned version{suffix(failed)}", failed


def run_map(cfg: Config, name: str, version: str | None) -> tuple[str, int]:
    entry = registry.dep(registry.load(cfg), name)
    version = version or registry.pinned(cfg, name, entry)
    emit(Mapped(manifest=store.build(cfg, name, entry, version)))
    return f"depmaps: mapped {name} {version}", 0


def run_sync(cfg: Config) -> tuple[str, int]:
    failed = built = pruned = 0
    for name, entry in registry.load(cfg).deps.items():
        try:
            version = registry.pinned(cfg, name, entry)
            if not store.mapped(cfg, name, version):
                emit(Mapped(manifest=store.build(cfg, name, entry, version)))
                built += 1
            for gone in store.prune(cfg, name, version):
                emit(Pruned(dep=name, version=gone))
                pruned += 1
        except DepmapsError as failure:  # one dependency's failure leaves the others to sync
            emit(Error(code=failure.code, message=str(failure)))
            failed += 1
    return f"depmaps: sync mapped {built}, pruned {pruned}{suffix(failed)}", failed


def run_diff(cfg: Config, name: str, old: str, new: str) -> tuple[str, int]:
    entry = registry.dep(registry.load(cfg), name)
    found = []
    for version in (old, new):
        each = store.manifest(cfg, name, version)
        if each is None:
            raise DepmapsError(ErrorCode.no_map, f"depmaps: {name} {version} has no map; mise run //depmaps:map {name}")
        found.append(each)
    bare = store.bare(cfg, name)
    counted = files_counted = 0
    for change in changes(bare, *found):
        emit(change)
        counted += 1
    for change in files(bare, *found, entry.files):
        emit(change)
        files_counted += 1
    return f"depmaps: {name} {old} -> {new}: {counted} functions, {files_counted} files changed", 0


def main(argv: Sequence[str] | None = None) -> None:
    try:
        request = parse(sys.argv[1:] if argv is None else argv)
    except ValueError as error:
        emit(Error(code=ErrorCode.invalid_usage, message=str(error)))
        raise SystemExit(2) from None
    cfg = config.load()
    try:
        runs = {
            Command.list: lambda: run_list(cfg),
            Command.map: lambda: run_map(cfg, request.args[0], request.version),
            Command.sync: lambda: run_sync(cfg),
            Command.diff: lambda: run_diff(cfg, *request.args),
        }
        message, failed = runs[request.command]()
    except DepmapsError as failure:
        emit(Error(code=failure.code, message=str(failure)))
        message, failed = f"depmaps: {request.command.value} failed: {failure.code.value}", 1
    emit(Done(command=request.command, message=message))
    if failed:
        raise SystemExit(1)
