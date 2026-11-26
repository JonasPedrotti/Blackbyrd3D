"""Check GitHub Releases for a newer Blackbyrd3D, and fetch and install it.

Pure and fail-silent: the network call is injectable (``fetch=``) so the
logic is testable without HTTP, and any failure (offline, rate-limited, bad
JSON) just returns ``None`` — a background update check must never disrupt
launch. The anonymous GET to GitHub is the only thing that leaves the
machine; nothing is phoned home.

Installing in place is offered where the app can replace itself: the
Windows installer build and an AppImage in a writable folder. The release
is not code-signed yet, so a download is only used when its SHA256 matches
the digest GitHub publishes for the asset.
"""

from __future__ import annotations

import hashlib
import json
import os

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


def _pick_asset(assets: list, system: str,
                machine: str | None = None) -> dict | None:
    suffix = _SUFFIX.get(system)
    if not suffix:
        return None
    candidates = [a for a in assets
                  if str(a.get("name", "")).endswith(suffix)]
    if machine is None:
        return candidates[0] if candidates else None
    want = _ARCH.get(machine.lower(), machine.lower())
    for fits in (lambda arch: arch == want, lambda arch: arch is None):
        for a in candidates:
            if fits(_arch_in(str(a.get("name", "")))):
                return a
    return None


def asset_for_platform(assets: list, system: str,
                       machine: str | None = None) -> str | None:
    """The download URL whose asset matches this OS and machine, or None.
    `system` is platform.system(): 'Linux' | 'Windows' | 'Darwin';
    `machine` is platform.machine(). An asset naming another architecture
    is never offered; one naming none fits any machine. Without `machine`
    the first asset for the OS is taken."""
    a = _pick_asset(assets, system, machine)
    return a.get("browser_download_url") if a else None


def _sha256_of(asset: dict | None) -> str | None:
    digest = str((asset or {}).get("digest") or "")
    if digest.lower().startswith("sha256:"):
        return digest[7:].lower() or None
    return None


def parse_release(data: dict, system: str,
                  machine: str | None = None) -> dict:
    """Normalise a GitHub release payload to
    {version, url, download, sha256, size}."""
    asset = _pick_asset(data.get("assets", []), system, machine)
    return {
        "version": str(data.get("tag_name", "")).lstrip("vV"),
        "url": data.get("html_url", ""),
        "download": asset.get("browser_download_url") if asset else None,
        "sha256": _sha256_of(asset),
        "size": int((asset or {}).get("size") or 0),
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


# -- installing in place ----------------------------------------------------

# Held while the app runs, so the Windows installer can wait for it to quit
RUNNING_MUTEX = "Blackbyrd3D-running"
_mutex = None


def hold_running_mutex():
    """Windows only: name this process for the installer to wait on."""
    global _mutex
    if os.name != "nt" or _mutex is not None:
        return
    try:
        import ctypes
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False,
                                                     RUNNING_MUTEX)
    except Exception:                                       # noqa: BLE001
        _mutex = None


def install_kind(system: str, *, frozen: bool,
                 appimage: str | None) -> str | None:
    """'windows', 'appimage', or None where only a browser download fits.
    A development checkout has nothing to install over, and an AppImage
    can only be swapped in a folder this user may write to."""
    if system == "Windows" and frozen:
        return "windows"
    if system == "Linux" and appimage and os.path.isfile(appimage):
        if os.access(os.path.dirname(os.path.abspath(appimage)), os.W_OK):
            return "appimage"
    return None


def can_install(rel: dict | None, kind: str | None) -> bool:
    return bool(kind and rel and rel.get("download") and rel.get("sha256"))


class DownloadCancelled(Exception):
    pass


class DownloadError(Exception):
    pass


def download(url: str, dest: str, sha256: str, *, progress=None,
             cancelled=None, opener=None, chunk: int = 1 << 18) -> str:
    """Stream `url` to `dest`, checked against `sha256`. Written to a
    .part file first, so nothing half-fetched or tampered ever lands at
    `dest`. `progress(done, total)` is told after every chunk, total 0
    when unknown; `cancelled()` returning True stops it."""
    part = dest + ".part"
    digest = hashlib.sha256()
    try:
        with (opener or _open)(url) as resp, open(part, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                if cancelled and cancelled():
                    raise DownloadCancelled()
                block = resp.read(chunk)
                if not block:
                    break
                out.write(block)
                digest.update(block)
                done += len(block)
                if progress:
                    progress(done, total)
        if digest.hexdigest() != sha256.lower():
            raise DownloadError("the download does not match the release's "
                                "checksum")
        os.replace(part, dest)
    except BaseException:
        try:
            os.remove(part)
        except OSError:
            pass
        raise
    return dest


def _open(url: str):
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": "Blackbyrd3D-updater"})
    return urlopen(req, timeout=30)       # noqa: S310 (GitHub release URL)


def appimage_download_path(appimage: str) -> str:
    """Beside the running AppImage, so the swap is a rename on one disk."""
    folder, name = os.path.split(os.path.abspath(appimage))
    return os.path.join(folder, f".{name}.update")


def install_appimage(new: str, appimage: str):
    """Put the downloaded AppImage in place of the running one. The running
    process keeps its mount of the old file until it quits."""
    os.chmod(new, 0o755)
    os.replace(new, appimage)


def windows_download_path() -> str:
    import tempfile
    folder = os.path.join(tempfile.gettempdir(), "Blackbyrd3D-update")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "Blackbyrd3D-Setup-x86_64.exe")


def windows_install_command(installer: str) -> list[str]:
    """No wizard pages, the previous choices kept; /UPDATE has the
    installer wait for this app to quit and start it again afterwards."""
    return [installer, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
            "/CLOSEAPPLICATIONS", "/UPDATE"]


def start_windows_installer(installer: str):
    import subprocess
    flags = (getattr(subprocess, "DETACHED_PROCESS", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    subprocess.Popen(windows_install_command(installer),   # noqa: S603
                     creationflags=flags, close_fds=True)
