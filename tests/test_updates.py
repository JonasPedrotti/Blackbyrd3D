"""Update-notifier logic (TDD, written before blackbyrd3d/utils/updates.py).

Pure + network-injected: no real HTTP in tests. The UI wiring (welcome-screen
banner, Help menu, launch check) is visual and verified in the app, not here.
"""

import json

import pytest

from blackbyrd3d.utils import updates as u


# ---------------------------------------------------------- version parsing

@pytest.mark.parametrize("text,expected", [
    ("0.3.1", (0, 3, 1)),
    ("v0.3.1", (0, 3, 1)),
    ("V1.2.3", (1, 2, 3)),
    ("0.3", (0, 3)),
    ("2.0.0", (2, 0, 0)),
    ("  v0.4.0  ", (0, 4, 0)),
])
def test_parse_version(text, expected):
    assert u.parse_version(text) == expected


@pytest.mark.parametrize("latest,current,newer", [
    ("0.3.2", "0.3.1", True),
    ("0.3.1", "0.3.1", False),       # equal is not newer
    ("0.3.0", "0.3.1", False),
    ("v0.4.0", "0.3.9", True),        # minor beats larger patch
    ("1.0.0", "0.9.9", True),
    ("0.3.1", "0.3", True),           # 0.3.1 > 0.3 (padded)
    ("0.3", "0.3.1", False),
])
def test_is_newer(latest, current, newer):
    assert u.is_newer(latest, current) is newer


# ------------------------------------------------------- asset by platform

def _assets():
    return [
        {"name": "Blackbyrd3D-x86_64.AppImage",
         "browser_download_url": "https://x/Blackbyrd3D-x86_64.AppImage"},
        {"name": "Blackbyrd3D-Setup-x86_64.exe",
         "browser_download_url": "https://x/Blackbyrd3D-Setup-x86_64.exe"},
        {"name": "Blackbyrd3D-0.3.2-arm64.dmg",
         "browser_download_url": "https://x/Blackbyrd3D-0.3.2-arm64.dmg"},
    ]


@pytest.mark.parametrize("system,suffix", [
    ("Linux", ".AppImage"),
    ("Windows", ".exe"),
    ("Darwin", ".dmg"),
])
def test_asset_for_platform_picks_right_file(system, suffix):
    url = u.asset_for_platform(_assets(), system)
    assert url is not None and url.endswith(suffix)


def test_asset_for_platform_unknown_os_is_none():
    assert u.asset_for_platform(_assets(), "Plan9") is None


def test_asset_for_platform_no_matching_asset_is_none():
    only_exe = [_assets()[1]]
    assert u.asset_for_platform(only_exe, "Linux") is None


# ---------------------------------------------- asset by architecture

def _both_appimages():
    return [
        {"name": "Blackbyrd3D-x86_64.AppImage",
         "browser_download_url": "https://x/Blackbyrd3D-x86_64.AppImage"},
        {"name": "Blackbyrd3D-aarch64.AppImage",
         "browser_download_url": "https://x/Blackbyrd3D-aarch64.AppImage"},
    ]


@pytest.mark.parametrize("assets", [_both_appimages(),
                                    _both_appimages()[::-1]])
@pytest.mark.parametrize("machine,arch", [
    ("x86_64", "x86_64"),
    ("aarch64", "aarch64"),
])
def test_linux_gets_the_appimage_for_its_architecture(assets, machine, arch):
    url = u.asset_for_platform(assets, "Linux", machine)
    assert url.endswith(f"-{arch}.AppImage")


def test_arm_linux_is_not_sent_the_x86_appimage():
    # releases made before there was an ARM build
    only_x86 = _both_appimages()[:1]
    assert u.asset_for_platform(only_x86, "Linux", "aarch64") is None


@pytest.mark.parametrize("machine", ["AMD64", "ARM64"])
def test_windows_machine_names_are_understood(machine):
    url = u.asset_for_platform(_assets(), "Windows", machine)
    assert (url is not None) == (machine == "AMD64")


def test_mac_arm64_matches_the_arm64_disk_image():
    url = u.asset_for_platform(_assets(), "Darwin", "arm64")
    assert url.endswith("-arm64.dmg")


def test_an_asset_naming_no_architecture_fits_any():
    plain = [{"name": "Blackbyrd3D.AppImage",
              "browser_download_url": "https://x/Blackbyrd3D.AppImage"}]
    assert u.asset_for_platform(plain, "Linux", "aarch64") is not None


def test_an_unknown_machine_only_gets_plain_assets():
    assert u.asset_for_platform(_both_appimages(), "Linux", "riscv64") is None


def test_check_passes_the_machine_through():
    release = dict(_release(), assets=_both_appimages())
    got = u.check_for_update("0.3.1", "Linux", "aarch64",
                             fetch=lambda: json.dumps(release))
    assert got["download"].endswith("-aarch64.AppImage")


# ------------------------------------------------------------ parse release

def _release(tag="v0.3.2"):
    return {
        "tag_name": tag,
        "html_url": f"https://github.com/JonasPedrotti/Blackbyrd3D/releases/"
                    f"tag/{tag}",
        "assets": _assets(),
    }


def test_parse_release_normalises_fields():
    rel = u.parse_release(_release(), "Linux")
    assert rel["version"] == "0.3.2"
    assert rel["url"].endswith("/tag/v0.3.2")
    assert rel["download"].endswith(".AppImage")


# -------------------------------------------------- check_for_update (glue)

def test_check_returns_release_when_newer():
    got = u.check_for_update("0.3.1", "Linux",
                             fetch=lambda: json.dumps(_release()))
    assert got is not None
    assert got["version"] == "0.3.2"
    assert got["download"].endswith(".AppImage")


def test_check_returns_none_when_equal():
    assert u.check_for_update("0.3.2", "Linux",
                              fetch=lambda: json.dumps(_release())) is None


def test_check_returns_none_when_current_is_ahead():
    assert u.check_for_update("0.4.0", "Windows",
                              fetch=lambda: json.dumps(_release())) is None


def test_check_is_fail_silent_on_fetch_error():
    def boom():
        raise OSError("offline")
    assert u.check_for_update("0.3.1", "Linux", fetch=boom) is None


def test_check_is_fail_silent_on_bad_json():
    assert u.check_for_update("0.3.1", "Linux",
                              fetch=lambda: "not json {{{") is None


def test_check_accepts_bytes_payload():
    got = u.check_for_update("0.3.1", "Linux",
                             fetch=lambda: json.dumps(_release()).encode())
    assert got is not None and got["version"] == "0.3.2"
