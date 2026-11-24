"""One version number, written in one place.

pyproject.toml declares it and everything else derives it: the app reads it
back (blackbyrd3d.__version__), the Windows exe and the macOS bundle read it
at build time, and the download links name no version at all. Only uv.lock
keeps a copy, which `uv lock` rewrites; CI installs with --locked, so a bump
without it fails there, on the release commit, the worst moment to find out.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel: str) -> str:
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()


def _declared() -> str:
    found = re.search(r'^version = "([^"]+)"$', _read("pyproject.toml"),
                      re.MULTILINE)
    assert found, "pyproject.toml declares no version"
    return found.group(1)


def test_the_app_reports_the_declared_version():
    from blackbyrd3d import __version__
    assert __version__ == _declared()


def test_the_lock_file_follows_the_version():
    found = re.search(r'^name = "blackbyrd3d"\nversion = "([^"]+)"$',
                      _read("uv.lock"), re.MULTILINE)
    assert found, "uv.lock does not pin blackbyrd3d"
    assert found.group(1) == _declared(), (
        "uv.lock still names the old version: run `uv lock` after changing "
        "the version in pyproject.toml")


def test_no_file_keeps_a_copy_of_the_version():
    """A copy goes stale at the next release without anyone noticing."""
    copies = {
        "blackbyrd3d/__init__.py": r'__version__ = "\d',
        "blackbyrd3d/ui/splash.py": r'version: str = "\d',
        "packaging/macos/byrd3d.spec": r'(?:^\s*version|CFBundle\w*Version")\s*[=:]\s*"\d',
        "packaging/macos/build-dmg.sh": r'^VERSION="',
        "README.md": r'Blackbyrd3D-\d[\d.]*-arm64\.dmg',
        "docs/getstarted/install.md": r'Blackbyrd3D-\d[\d.]*-arm64\.dmg',
    }
    stale = [rel for rel, pattern in copies.items()
             if re.search(pattern, _read(rel), re.MULTILINE)]
    assert not stale, f"these files write the version out by hand: {stale}"


def test_the_changelog_leads_with_the_version_being_shipped():
    """The top section is either the release itself or work queued behind
    it; either way an entry for a version we are past is a mistake."""
    version = _declared()
    heads = [ln.strip() for ln in _read("CHANGELOG.md").splitlines()
             if ln.startswith("## ")]
    assert heads, "the changelog has no version headings at all"
    top = heads[0]
    assert version in top or "Unreleased" in top, (
        f"the changelog opens with {top!r}, which is neither "
        f"{version!r} nor an Unreleased section")
