"""Installing 0.3.0 over 0.2.1 left the old blackbyrd3d-0.2.1.dist-info in
_internal beside the new one, so the app still called itself 0.2.1.
"""
import re
from pathlib import Path

ISS = (Path(__file__).resolve().parent.parent
       / "packaging" / "windows" / "installer.iss")


def test_the_installer_clears_the_old_bundle_first():
    iss = ISS.read_text()
    section = re.search(r"^\[InstallDelete\]\n(.*?)(?=^\[)", iss,
                        re.MULTILINE | re.DOTALL)
    assert section, "installer.iss has no [InstallDelete] section"
    assert re.search(r'Type:\s*filesandordirs;\s*Name:\s*"\{app\}\\_internal"',
                     section.group(1))
