# Code signing policy

!!! note "Not signed yet"
    Blackbyrd3D has applied to SignPath Foundation's programme for open
    source. Until it is accepted, the Windows installer is unsigned and
    Windows warns about an unknown publisher. This page is the policy the
    signed installers will follow.

Free code signing provided by [SignPath.io](https://about.signpath.io),
certificate by [SignPath Foundation](https://signpath.org).

## What is signed

Only the Windows installer, `Blackbyrd3D-Setup-x86_64.exe`, attached to each
[GitHub release](https://github.com/JonasPedrotti/Blackbyrd3D/releases).
The programs and libraries it installs are not signed one by one; most of
them come from other projects (Python, Qt, Open CASCADE, VTK).

Every signed installer is built from this repository's source by GitHub
Actions, in the
[Build Windows installer](https://github.com/JonasPedrotti/Blackbyrd3D/blob/main/.github/workflows/build-windows.yml)
workflow, and handed straight to SignPath from that run. Nothing built on a
personal computer is signed. The installer's product name and version must
match the release, or SignPath refuses to sign it.

## Team roles

| Role | Members |
|---|---|
| Committers and reviewers | [Jonas Pedrotti](https://github.com/JonasPedrotti) |
| Approvers | [Jonas Pedrotti](https://github.com/JonasPedrotti) |

Every signing request is approved by hand before it is signed. Contributions
from anyone else reach the code only as pull requests, which are reviewed
before they are merged.

## Privacy

This program will not transfer any information to other networked systems
unless specifically requested by the user or the person installing or
operating it, with one exception: the update check, which is on by default
and can be turned off in the installer or the app. The
[privacy policy](privacy.md) lists every connection and what it sends.
