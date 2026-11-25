# Changelog

## Unreleased

- **Ortho and grid snap in every pane.** The Ortho and Grid buttons and F8
  and F9 now hold in all viewports, not only the first one.
- **Backspace deletes the selection,** so the delete key on a Mac works.
- **Cen on faces and closed curves, and `centroid`.** Cen finds the middle
  of rectangles, surfaces and every face of a solid; `centroid` places a
  point at an area or volume centroid.
- **Relocate the gumball.** Right-click, Ctrl+click or double-click its
  centre to move it anywhere; Ctrl+double-click resets it.
- **Faces on surfaces stay put.** Moving a face of joined surfaces with
  the gumball no longer deletes it; the faces beside it follow.
- **Temporary guides.** Tap Ctrl while picking a point to drop a guide;
  the cursor lines up with it, and the lines through two guides snap,
  with Mid and Perp.
- **Pushpull picks with a plain click.** It always asks for the face, and
  a click on one goes straight to the distance.
- **An installer in the app's colours.** The Windows installer is dark like
  Blackbyrd3D, with the bird on its first and last page.
- **Default app from the installer.** A ticked box makes Blackbyrd3D open
  .byrd and .wyrm files on Windows.
- **The update check says it ran.** After launch the status bar says the
  app is up to date, or that GitHub could not be reached.

## 0.2.1

- **Linux ARM AppImage.** Releases now include `Blackbyrd3D-aarch64.AppImage`
  for 64-bit ARM; E57 import is not available there yet.
- **Linux uninstall leaves Serpentine3D alone.** Removing Blackbyrd3D from
  the desktop no longer deletes a Serpentine3D launcher or AppImage.

## 0.2.0

- **Faster opening.** Display meshes are saved in `.byrd` files and
  viewports share their GPU buffers.
- **macOS app no longer reported as damaged** after the last bundle change.
- **MeshToBrep in seconds** behind a progress card, and picking the result
  no longer freezes the window.
- **MergeAllCoplanarFaces in seconds** on converted meshes, behind a
  progress card. Joined faces now show as open or closed polysurface.
- **Stacked bodies merge cleanly.** MergeAllCoplanarFaces removes the faces
  lying back to back between them, so their seams disappear.
- **Typed coordinates on the gumball.** Typing `0,` while dragging a move
  arrow sends the object or point to zero on that axis, on release.
- **Units button in the status bar.** Click the units to pick new ones;
  with objects in the file it asks whether to scale them along.
- **Space and Enter in the viewport** finish or repeat a command, as in the
  command line.
- **Double-clicked .wyrm files no longer crash** the app on launch.

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
