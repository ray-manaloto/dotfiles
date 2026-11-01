"""p2996 projects: compile each real reflection project in projects.json; nothing is run."""

import itertools
import re

import anyio

from . import proc, source
from .config import MANIFEST, TOOLCHAIN, compiler_env, project_dir
from .log import P2996Error, log
from .models import Config, Manifest, Project, Projects

# ninja 1.13 adds [code=N]; the step's first output names an object, its module scan or a link.
_FAILED = re.compile(r"^FAILED: (?:\[code=\d+\] )?(\S+?)(?:\.ddi)?(?:\s|$)", re.MULTILINE)
_STEP = re.compile(r"^(?:FAILED: |\[\d+/\d+\] |ninja: )", re.MULTILINE)


async def run(cfg: Config, args: Projects) -> None:
    text = await anyio.Path(args.manifest or MANIFEST).read_text()
    problems = [
        problem for project in Manifest.model_validate_json(text).projects for problem in await check(cfg, project)
    ]
    if problems:
        raise P2996Error("p2996 projects: " + "; ".join(problems))


async def check(cfg: Config, project: Project) -> list[str]:
    """What differs from the record for one project; empty means it compiled as recorded."""
    top = project_dir(cfg, project.name)
    tree, out = top / "source", top / "build"
    await anyio.Path(tree).mkdir(parents=True, exist_ok=True)
    await source.fetch(tree, project.remote, project.commit)
    env = compiler_env()
    layout = ("-S", tree, "-B", out, "-G", "Ninja", f"-DCMAKE_TOOLCHAIN_FILE={TOOLCHAIN}")
    configured = await proc.run("cmake", "--fresh", *layout, *project.options, check=False, env=env)
    if configured.returncode != 0:
        return [f"{project.name} did not configure: {configured.stderr.decode().strip()}"]
    targets = ("--target", *project.targets) if project.targets else ()
    built = await proc.run(
        "cmake", "--build", out, "--parallel", str(cfg.jobs), *targets, "--", "-k", "0", check=False, env=env
    )
    output = built.stdout.decode() + built.stderr.decode()
    await anyio.Path(top / "build.log").write_text(output)
    failed = failures(output)
    problems = compare(project, failed)
    if built.returncode != 0 and not failed:
        problems.append(f"{project.name} stopped before compiling: {output.strip()}")
    if not problems:
        log.info("project ok", project=project.name, commit=project.commit, known_failures=len(project.known_failures))
    return problems


def failures(output: str) -> dict[str, str]:
    """Each failed object with the diagnostics printed for it."""
    steps = [match.start() for match in _STEP.finditer(output)] + [len(output)]
    blocks = [output[start:end] for start, end in itertools.pairwise(steps)]
    return {found[1]: block for block in blocks if (found := _FAILED.match(block))}


def compare(project: Project, failed: dict[str, str]) -> list[str]:
    problems = []
    remaining = dict(failed)
    for known in project.known_failures:
        name = next((obj for obj in remaining if obj.endswith(f"/{known.source}.o")), None)
        if name is None:
            problems.append(f"{project.name} {known.source} compiles now: remove its record")
        elif known.reason not in remaining.pop(name):
            problems.append(f"{project.name} {known.source} failed without {known.reason!r}")
    return problems + [f"{project.name} new failure: {name}" for name in remaining]
