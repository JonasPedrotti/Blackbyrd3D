"""Check GitHub Releases for a newer Blackbyrd3D and point at the download.

Pure and fail-silent: the network call is injectable (``fetch=``) so the
logic is testable without HTTP, and any failure (offline, rate-limited, bad
JSON) just returns ``None`` — a background update check must never disrupt
launch. The anonymous GET to GitHub is the only thing that leaves the
machine; nothing is phoned home.
"""

from __future__ import annotations

import json

REPO = "JonasPedrotti/Blackbyrd3D"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases/latest"

# platform.system() -> the installer asset suffix for that OS
_SUFFIX = {"Linux": ".AppImage", "Windows": ".exe", "Darwin": ".dmg"}

# platform.machine() spellings, and those in asset names, per architecture
_ARCH = {"x86_64": "x86_64", "amd64": "x86_64",
         "aarch64": "arm64", "arm64": "arm64"}


def parse_version(text: str) -> tuple:
    """'v0.3.1' / '0.3' -> (0, 3, 1) / (0, 3). Leading v/V and a
    non-numeric tail on any component are ignored."""
    out = []
    for part in text.strip().lstrip("vV").split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        out.append(int(digits) if digits else 0)
    return tuple(out) or (0,)


def is_newer(latest: str, current: str) -> bool:
    """Is release string `latest` newer than `current`?"""
    a, b = parse_version(latest), parse_version(current)
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return a > b


def _arch_in(name: str) -> str | None:
    lowered = name.lower()
    for token, arch in _ARCH.items():
        if token in lowered:
            return arch
    return None


def asset_for_platform(assets: list, system: str,
                       machine: str | None = None) -> str | None:
    """The download URL whose asset matches this OS and machine, or None.
    `system` is platform.system(): 'Linux' | 'Windows' | 'Darwin';
    `machine` is platform.machine(). An asset naming another architecture
    is never offered; one naming none fits any machine. Without `machine`
    the first asset for the OS is taken."""
    suffix = _SUFFIX.get(system)
    if not suffix:
        return None
    candidates = [a for a in assets
                  if str(a.get("name", "")).endswith(suffix)]
    if machine is None:
        return candidates[0].get("browser_download_url") if candidates else None
    want = _ARCH.get(machine.lower(), machine.lower())
    for fits in (lambda arch: arch == want, lambda arch: arch is None):
        for a in candidates:
            if fits(_arch_in(str(a.get("name", "")))):
                return a.get("browser_download_url")
    return None


def parse_release(data: dict, system: str,
                  machine: str | None = None) -> dict:
    """Normalise a GitHub release payload to {version, url, download}."""
    return {
        "version": str(data.get("tag_name", "")).lstrip("vV"),
        "url": data.get("html_url", ""),
        "download": asset_for_platform(data.get("assets", []), system,
                                       machine),
    }


def check_for_update(current: str, system: str, machine: str | None = None,
                     *, fetch=None) -> dict | None:
    """Return {version, url, download} if a newer release exists, else None.
    Never raises — any error returns None. `fetch` is a no-arg callable
    returning the raw JSON (str/bytes/dict); defaults to a live GET."""
    try:
        raw = (fetch or _fetch)()
        data = raw if isinstance(raw, dict) else json.loads(raw)
        rel = parse_release(data, system, machine)
        if rel["version"] and is_newer(rel["version"], current):
            return rel
        return None
    except Exception:
        return None


def _fetch() -> str:
    from urllib.request import Request, urlopen
    req = Request(RELEASES_API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Blackbyrd3D-update-check",
    })
    with urlopen(req, timeout=4) as resp:   # noqa: S310 (fixed HTTPS URL)
        return resp.read().decode("utf-8")
