# Changelog

## Unreleased

- **Faster opening.** Display meshes are saved in `.byrd` files and
  viewports share their GPU buffers.
- **macOS app no longer reported as damaged** after the last bundle change.
- **MeshToBrep in seconds** behind a progress card, and picking the result
  no longer freezes the window.
- **MergeAllCoplanarFaces in seconds** on converted meshes, behind a
  progress card. Joined faces now show as open or closed polysurface.
- **Stacked bodies merge cleanly.** MergeAllCoplanarFaces removes the faces
  lying back to back between them, so their seams disappear.

## 0.1.0

- **Blackbyrd3D**, an open-source NURBS surface modeller for Linux, Windows
  and macOS, built on Serpentine3D by Chisomo Banzi. Drawings are saved as
  `.byrd`, node graphs in Wyrm as `.wyrm`, and Serpentine3D's `.serp` files
  still open. A first launch copies Serpentine3D's settings and plugins over
  and leaves Serpentine3D's own untouched.
- **Welcome screen with examples.** Recent documents and four examples
  (glazing detail, stool, cabin, urban block) as cards with previews; your own files
  take the places of the examples as they come. A new model starts in the
  units chosen there. Examples open as copies, so Save asks where.
