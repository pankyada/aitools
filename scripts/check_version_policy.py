#!/usr/bin/env python3
"""Validate ai-toolset versioning and bump policy."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_semver(version: str) -> tuple[int, int, int]:
    """Parse a strict x.y.z semantic version.

    Args:
        version: Version string.

    Returns:
        Parsed (major, minor, patch).

    Raises:
        ValueError: If value is not strict semantic version format.
    """

    match = SEMVER_RE.fullmatch(version.strip())
    if not match:
        raise ValueError(f"Invalid semantic version: {version!r}. Expected format x.y.z")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def load_pyproject_version(path: Path) -> str:
    """Load project version from a pyproject.toml file.

    Args:
        path: Path to pyproject.toml.

    Returns:
        Version string in [project].

    Raises:
        KeyError: If [project].version is missing.
        OSError: If file cannot be read.
    """

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def load_all_versions(repo_root: Path) -> dict[str, str]:
    """Load root and package versions from pyproject files.

    Args:
        repo_root: Repository root directory.

    Returns:
        Mapping of path string to version.

    Raises:
        OSError: If files cannot be read.
        KeyError: If required version keys are missing.
    """

    versions: dict[str, str] = {}
    root_pyproject = repo_root / "pyproject.toml"
    versions[str(root_pyproject)] = load_pyproject_version(root_pyproject)

    for package_pyproject in sorted((repo_root / "packages").glob("*/pyproject.toml")):
        versions[str(package_pyproject)] = load_pyproject_version(package_pyproject)

    return versions


def ensure_uniform_versions(versions: dict[str, str]) -> tuple[bool, str]:
    """Check that all loaded versions are strict semver and identical.

    Args:
        versions: Mapping of pyproject path to version.

    Returns:
        Tuple of success flag and summary message.

    Raises:
        ValueError: If any version is not strict semver.
    """

    parsed_by_path: dict[str, tuple[int, int, int]] = {}
    for path, version in versions.items():
        parsed_by_path[path] = parse_semver(version)

    distinct = sorted(set(versions.values()))
    if len(distinct) != 1:
        lines = ["Version mismatch across pyprojects:"]
        for path, version in sorted(versions.items()):
            lines.append(f"- {path}: {version}")
        return False, "\n".join(lines)

    return True, f"Unified semantic version: {distinct[0]}"


def run_git(args: list[str]) -> str:
    """Run a git command and return stdout.

    Args:
        args: Git arguments after the `git` executable.

    Returns:
        Stdout text stripped of trailing whitespace.

    Raises:
        RuntimeError: If the git command fails.
    """

    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def is_empty_ref(ref: str | None) -> bool:
    """Return whether a git ref is empty or all-zero sentinel.

    Args:
        ref: Candidate ref value.

    Returns:
        True if ref is empty or all-zero 40-char hash.

    Raises:
        None.
    """

    return not ref or ref == "0" * 40


def added_tools_and_skills(base_ref: str) -> tuple[list[str], list[str]]:
    """Collect newly added package and skill directory names versus base ref.

    Args:
        base_ref: Base git ref/sha for comparison.

    Returns:
        Tuple of (added_package_dirs, added_skill_dirs).

    Raises:
        RuntimeError: If git diff fails.
    """

    diff = run_git(["diff", "--name-status", "--diff-filter=A", f"{base_ref}...HEAD"])
    added_packages: set[str] = set()
    added_skills: set[str] = set()

    for line in diff.splitlines():
        parts = line.split("\t", maxsplit=1)
        if len(parts) != 2:
            continue
        _, file_path = parts
        chunks = file_path.split("/")
        if len(chunks) < 2:
            continue
        if chunks[0] == "packages":
            added_packages.add(chunks[1])
        if chunks[0] == "skills":
            added_skills.add(chunks[1])

    return sorted(added_packages), sorted(added_skills)


def load_version_from_ref(ref: str) -> str:
    """Load root project version from a git ref.

    Args:
        ref: Git ref or sha.

    Returns:
        Root pyproject version at that ref.

    Raises:
        RuntimeError: If git show fails.
        KeyError: If version is missing.
        tomllib.TOMLDecodeError: If TOML is malformed.
    """

    content = run_git(["show", f"{ref}:pyproject.toml"])
    data = tomllib.loads(content)
    return str(data["project"]["version"])


def enforce_major_bump_for_new_tooling(
    current_version: str,
    base_ref: str | None,
) -> tuple[bool, str]:
    """Enforce major-version bump when new tools or skills are added.

    Args:
        current_version: Current root version.
        base_ref: Base ref for diff.

    Returns:
        Tuple of success flag and summary message.

    Raises:
        ValueError: If version format is invalid.
    """

    if is_empty_ref(base_ref):
        return True, "Skipped base comparison: no valid base ref available"

    assert base_ref is not None

    try:
        added_packages, added_skills = added_tools_and_skills(base_ref)
    except RuntimeError as exc:
        return False, f"Failed to diff against base ref {base_ref}: {exc}"

    if not added_packages and not added_skills:
        return True, "No new tool package or skill directory added"

    try:
        base_version = load_version_from_ref(base_ref)
    except Exception as exc:
        return False, f"Failed to read base version from {base_ref}: {exc}"

    current_major = parse_semver(current_version)[0]
    base_major = parse_semver(base_version)[0]

    if current_major <= base_major:
        additions: list[str] = []
        if added_packages:
            additions.append(f"packages: {', '.join(added_packages)}")
        if added_skills:
            additions.append(f"skills: {', '.join(added_skills)}")
        reason = "; ".join(additions)
        return (
            False,
            "Major version bump required when adding new tools/skills. "
            f"Detected {reason}. Base version={base_version}, current={current_version}. "
            "Increase major version (e.g., 0.x.y -> 1.0.0).",
        )

    return (
        True,
        "Major version bump check passed for added tooling: "
        f"base={base_version}, current={current_version}",
    )


def main() -> int:
    """Run version policy checks.

    Args:
        None.

    Returns:
        Process exit code.

    Raises:
        None.
    """

    parser = argparse.ArgumentParser(description="Validate ai-toolset version policy")
    parser.add_argument(
        "--base-ref",
        default="",
        help="Git base ref/sha used to detect newly added tools/skills",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    versions = load_all_versions(repo_root)
    ok_uniform, msg_uniform = ensure_uniform_versions(versions)
    print(msg_uniform)
    if not ok_uniform:
        return 1

    root_version = versions[str(repo_root / "pyproject.toml")]
    ok_major, msg_major = enforce_major_bump_for_new_tooling(root_version, args.base_ref)
    print(msg_major)
    return 0 if ok_major else 1


if __name__ == "__main__":
    sys.exit(main())
