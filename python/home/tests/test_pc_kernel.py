"""pc-doctor's kernel-settings line through the doctor, with ssh stood in: pass, a changed key, and each unknown."""

# Spec #729, ticket #730. The answers follow what sysctl (procps-ng 4.0.7) printed on the PC on 2026-11-16: one
# `key = value` line per key, exit 1 and a message on stderr for a key the kernel does not have.

from pathlib import Path

import pytest

from .test_pc_doctor import KERNEL, answer, doctor

KERNEL_KEYS = {
    "kernel.kptr_restrict": "0",
    "kernel.sysrq": "16",
    "kernel.printk": "0\t4\t1\t4",
    "kernel.core_pattern": "|/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h %d %F %I",
    "fs.protected_regular": "1",
}


def sysctl(changed: dict[str, str] | None = None, code: int = 0) -> dict[str, object]:
    """sysctl's answer for the five keys, with some values changed."""
    values = KERNEL_KEYS | (changed or {})
    return {"stdout": "".join(f"{key} = {value}\n" for key, value in values.items()), "code": code}


def kernel(folder: Path, capfd: pytest.CaptureFixture[str], said: dict[str, object]) -> tuple[int, dict, str]:
    """The doctor's exit code, its kernel-settings line as JSON, and stderr, with every other line healthy."""
    answer(folder, {KERNEL: said})
    code, lines, err = doctor(capfd)
    [line] = [line for line in lines if line.check == "kernel-settings"]
    return code, line.model_dump(mode="json"), err


def test_boot_values_pass(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = kernel(ssh, capfd, sysctl())
    assert code == 0
    assert (line["result"], line["culprits"]) == ("pass", [])
    assert "5 kernel settings match" in line["detail"]


def test_a_changed_key_fails_naming_it_with_both_values(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = kernel(ssh, capfd, sysctl({"kernel.sysrq": "1", "kernel.core_pattern": "core"}))
    assert code == 1
    assert line["result"] == "fail"
    assert line["culprits"] == ["sysctl:kernel.sysrq", "sysctl:kernel.core_pattern"]
    assert "kernel.sysrq is '1', expected '16'" in line["detail"]
    assert "kernel.core_pattern is 'core', expected '|/usr/lib/systemd/systemd-coredump" in line["detail"]


def test_a_changed_printk_field_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = kernel(ssh, capfd, sysctl({"kernel.printk": "4\t4\t1\t7"}))
    assert (code, line["result"], line["culprits"]) == (1, "fail", ["sysctl:kernel.printk"])


def test_a_spacing_only_change_fails(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    spaced = KERNEL_KEYS["kernel.core_pattern"].replace(" %P", "  %P")
    code, line, _ = kernel(ssh, capfd, sysctl({"kernel.core_pattern": spaced, "kernel.printk": "0 4 1 4"}))
    assert (code, line["culprits"]) == (1, ["sysctl:kernel.printk", "sysctl:kernel.core_pattern"])


def test_a_stray_line_does_not_hide_a_change(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    rows = "".join(f"{key} = {value}\n" for key, value in (KERNEL_KEYS | {"kernel.kptr_restrict": "1"}).items())
    code, line, _ = kernel(ssh, capfd, {"stdout": "sysctl: permission denied on key x\n" + rows})
    assert (code, line["result"], line["culprits"]) == (1, "fail", ["sysctl:kernel.kptr_restrict"])


def test_a_missing_sysctl_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = kernel(ssh, capfd, {"stderr": "bash: line 1: sysctl: command not found\n", "code": 127})
    assert (code, line["result"]) == (3, "unknown")
    assert "sysctl is not on the PC" in line["detail"]


@pytest.mark.parametrize("stdout", ["not sysctl output\n", "kernel.sysrq: 16\n"], ids=["prose", "no-equals"])
def test_malformed_output_is_unknown(stdout: str, ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = kernel(ssh, capfd, {"stdout": stdout})
    assert (code, line["result"]) == (3, "unknown")
    assert "did not parse" in line["detail"]


def test_a_key_sysctl_could_not_read_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    rows = "".join(f"{key} = {value}\n" for key, value in KERNEL_KEYS.items() if key != "fs.protected_regular")
    stderr = "sysctl: cannot stat /proc/sys/fs/protected_regular: No such file or directory\n"
    code, line, err = kernel(ssh, capfd, {"stdout": rows, "stderr": stderr, "code": 1})
    assert (code, line["result"], line["culprits"]) == (3, "unknown", ["sysctl:fs.protected_regular"])
    assert "cannot stat" in err


def test_an_error_exit_with_every_key_read_is_unknown(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, line, _ = kernel(ssh, capfd, sysctl(code=1))
    assert (code, line["result"], line["culprits"]) == (3, "unknown", [])
    assert "exit 1" in line["detail"]


def test_a_changed_key_fails_even_when_another_could_not_be_read(ssh: Path, capfd: pytest.CaptureFixture[str]) -> None:
    rows = "".join(f"{key} = {value}\n" for key, value in KERNEL_KEYS.items() if key != "fs.protected_regular")
    code, line, _ = kernel(ssh, capfd, {"stdout": rows.replace("= 16", "= 1"), "code": 1})
    assert (code, line["result"], line["culprits"]) == (1, "fail", ["sysctl:kernel.sysrq"])
