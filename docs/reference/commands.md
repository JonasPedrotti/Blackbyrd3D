# Command reference

Every command is typed on the command line (Tab completes,
F1 opens this list inside the app). Aliases in parentheses.
Commands that need a file open a filtered chooser by default. Append
`--headless` to keep the typed path prompt for scripts and automation.

## Booleans

| Command | Does |
|---|---|
| `booleandifference` (`difference`, `bd`) | Subtract solids from solids, in place. DeleteInput=No, the default, keeps what they were cut with; Yes removes it too. |
| `booleanintersection` (`intersection`, `bi`) | Keep only the volume two or more solids share. |
| `booleanunion` (`union`, `bu`) | Merge two or more solids into one. |
| `booleanunionmerge` (`unionmerge`) | Boolean union, then MergeAllCoplanarFaces on the result. |
| `curveboolean` (`curvebool`) | Closed curves around the regions of overlapping planar curves. |

## Camera

| Command | Does |
|---|---|
| `camera` (`cam`) | Set the view's camera: Lens (focal length), Sensor, Place, Position, Target, or Frame guides for an aspect ratio. |

## Capture

| Command | Does |
|---|---|
| `turntable` | Orbit the camera once around the work and write a video clip; orbits the selection if there is one, at the pane's own elevation. |
| `turntableui` | Record a portrait turntable of the current shot and application UI. |
| `viewcapture` (`screenshot`, `viewcapturetofile`, `vcf`, `viewcapturetoclipboard`, `vcc`) | Capture the active viewport as an image: copy it or save it, at the pane's own pixels or scaled up or down. A script gives the file to save to instead. |

## Curves

| Command | Does |
|---|---|
| `arc` (`a`) | Arc from its center, start and end; or EndsFirst (both ends, then a point on the arc), or Through (start, a point on the arc, end). |
| `circle` (`c`, `ci`) | Circle from center and radius; or 2Point across, or 3Point through. |
| `closecrv` (`cc`, `closecurve`) | Close open curves with a straight segment between their ends. |
| `curve` (`cv`) | NURBS curve by control points, as Rhino's Curve does. |
| `divide` | Place points that divide curves into equal segments. |
| `ellipse` (`el`) | Ellipse from its center and the ends of its two axes; Diameter takes the first axis whole. |
| `interpcrv` (`interpcurve`) | NURBS curve through picked points; Close joins it back smoothly. |
| `line` (`l`) | Straight line; BothSides grows it evenly out of its middle. |
| `point` (`pt`) | Place one point object. |
| `points` | Place point objects one after another until Enter. |
| `polyline` (`pl`, `pline`) | Polyline through picked points; Close or a click back on the start closes it, Enter finishes it open. |
| `rectangle` (`rect`, `rec`) | Rectangle corner to corner; or Center out, or 3Point to lean it. |
| `tweencurves` (`tween`) | Curves in even steps between two curves. |

## Deformation

| Command | Does |
|---|---|
| `bend` | Bend objects along a spine by an angle. |
| `curvaturegraph` (`combs`) | Toggle curvature combs on selected curves. |
| `draftanalysis` (`draft`) | Colour faces by draft angle relative to the pull direction (+Z): green = enough draft, blue = vertical-side risk, red = undercut. |
| `extend` | Lengthen curves at the end, the start or both, by dragging or typing a length. |
| `flow` (`flowalongcrv`) | Flow objects from a base line onto a target curve. |
| `matchcrv` (`match`) | Change a curve's end so it meets another curve with Position or Tangent continuity. |
| `taper` | Taper objects along an axis, scaling the far end by a factor. |
| `twist` | Twist objects around an axis by a total angle. |

## Display & views

| Command | Does |
|---|---|
| `1view` (`oneview`, `singleview`) | Show one viewport instead of four. |
| `4view` (`fourview`, `quadview`) | Split the model area into Top / Front / Right / Perspective. |
| `ai` (`assistant`) | Open the AI assistant panel — model by describing what you want. |
| `angle` | Angle at a vertex point between two directions. |
| `area` | Measure the area of surfaces or solids. |
| `back` | Look at the model from the back. |
| `bottom` | Look at the model from below. |
| `centroid` (`areacentroid`, `volumecentroid`) | Place a point at each object's centroid: the volume centroid of a solid, the area centroid of a surface or a closed planar curve. |
| `clippingplane` (`clip`) | Place a rectangular clipping plane parallel to the CPlane through the first corner. It cuts away the side toward the view it is drawn in, as Rhino 8 does: drawn in Top it takes what is above and keeps what is below, the way you are looking. Move or rotate the plane object to move the cut; Flip reverses the kept side. The purple arrow points toward the visible side, following Rhino's convention. |
| `cplane` | Reposition the construction plane (drawing plane + grid). |
| `curvature` | Curvature and radius of a curve at a point. |
| `curvatureanalysis` (`curvmap`) | Color surfaces by curvature (run again to turn off). |
| `disableclippinginview` (`dcv`) | Switch clipping planes off in the view you are in (the pane, or the detail you are inside) and leave them cutting every other view. |
| `disableclippingplane` (`dcc`) | Pause clipping planes (they stay in the scene, the cut stops). |
| `distance` (`dist`) | Measure the distance between two points. |
| `enableclippinginview` (`ecv`) | Switch clipping planes back on in the view you are in (the pane, or the detail you are inside). A paused one resumes, and so cuts its other views again as well. |
| `enableclippingplane` (`ecc`) | Re-enable paused clipping planes. |
| `floatviewport` (`floatvp`) | Open a floating viewport window (drag it to another monitor). |
| `front` | Look at the model from the front. |
| `ghosted` (`gh`) | Ghosted display, shaded and see-through. |
| `grid` | Show or hide the grid. |
| `gridsnap` | Turn snapping to the grid on or off. |
| `gumball` | Turn the gumball on or off. |
| `gumballalignment` | Choose what the gumball's axes follow: the CPlane, the object, the world or the view. |
| `isocurves` (`showisocurves`) | Show or hide the wires across surfaces in this viewport. |
| `isometric` (`iso`) | Isometric view. |
| `left` | Look at the model from the left. |
| `length` (`len`) | Measure the length of curves. |
| `maxviewport` (`max`, `maximizeviewport`) | Give the pane you are in the whole window; again puts it back. |
| `namedview` (`nv`) | Save, restore, list or delete named views. |
| `newviewport` (`newvp`, `splitview`) | Open an extra live viewport in a dockable panel — drag its title bar to rearrange or tear it off to float; a pane's own title menu picks what it shows, so a paper sheet can sit beside the model. |
| `ortho` | Toggle ortho: picked points lock to CPlane axes from the last point (hold Shift for the momentary opposite). |
| `osnap` | Toggle one object-snap type (or All = the master switch) — scriptable, e.g. bind a key to 'osnap mid toggle'. |
| `perspective` (`persp`) | Perspective view. |
| `pictureframe` (`picture`) | Choose and place an embedded reference image for tracing. |
| `plaster` (`clay`, `arctic`) | Every surface in matte white under soft light, like a plaster model. |
| `plastercolor` (`claycolor`) | Plaster's soft light, with every object in its own colour. |
| `pointsoff` (`pf`) | Hide all control points. |
| `pointson` (`po`) | Show control points for selected curves, surfaces and meshes (F10); a mesh's are its corners. |
| `printcheck` (`printinfo`) | Check selected objects for 3D-print readiness: watertight, manifold, degenerate facets, thin walls, overhangs and print size. |
| `radius` | Radius of curvature of a curve at a picked point. |
| `redoview` | Go forward again through the views `undoview` stepped back through. |
| `rendered` (`render`) | Environment-lit display with materials and a ground shadow. |
| `right` | Look at the model from the right. |
| `selclippingplane` | Select every clipping plane object. |
| `shaded` (`sh`) | Shaded display. |
| `showedges` | Highlight all edges or only the naked edges of objects. |
| `showedgesadd` | Add objects to the ones ShowEdges is highlighting. |
| `showedgesremove` | Take objects out of the ones ShowEdges is highlighting. |
| `snap` | Turn object snaps on or off. |
| `spacemouse` (`3dmouse`) | SpaceMouse status, on/off toggle, and a live axis readout for checking the motion mapping. |
| `surfaceedges` | Show or hide the outlines of faces. Curves and text are unaffected. |
| `technical` (`tech`) | Hidden-line technical display (parallel projection linework). |
| `tolerance` | Show or set the document's absolute modelling tolerance. |
| `top` | Look at the model from the top. |
| `undoview` | Put the view back where it was before the last view change. |
| `units` | Set document units; optionally rescale the model to keep real size. |
| `volume` (`vol`) | Measure the volume of solids. |
| `wireframe` (`wf`) | Wireframe display. |
| `wyrm` (`nodes`) | Open Wyrm, the visual graph editor: wire components together to make geometry, watch it preview in the model, then Bake it in. |
| `wyrmset` | Pick the model objects a Wyrm component holds. Wyrm starts this from a component's Set Crv... (or Pt, Brep, Mesh), filtered to its kind. |
| `wyrmvector` | Pick the two points a Wyrm Vector runs between: where it starts, then where its arrow points. Wyrm starts this from Set Vector... |
| `zebra` | Zebra stripes to check surface continuity (run again to turn off). |
| `zoom` (`z`) | Zoom the active view: Selected, Extents, a picked Window, In, Out. |
| `zoomextents` (`ze`, `zea`) | Zoom to fit everything in the view. |
| `zoomselected` (`zs`) | Frame the current selection in the active view. |
| `zoomwindow` (`zw`) | Zoom into a window picked with two corner points. |

## Drafting & layouts

| Command | Does |
|---|---|
| `annotedit` (`editnote`, `edittext`) | Edit the annotation nearest a picked point (text, style). |
| `detail` | Draw a detail on the layout, a window showing the model from a view at a scale. |
| `detailborder` | Show or hide the border of the detail you are in. |
| `detaildelete` | Delete the detail you are in. |
| `detaillock` | Lock or unlock a detail's view and scale; its frame still moves. |
| `detailmode` | Set how the detail you are in draws the model: Technical, Hidden, Wireframe, Shaded, Plaster or PlasterColor. |
| `detailscale` | Set the scale of the detail you are in, e.g. 1:20. |
| `detailsection` | Cut the detail you are in with a section plane: what is in front is removed, cut faces are hatched. |
| `dim` (`dimension`, `dimlinear`, `dimaligned`) | Linear dimension between two points, on a layout or in the model. |
| `dimangle` (`dimangular`) | Angular dimension on a layout, from a vertex and two directions. |
| `dimdiameter` (`dimdia`) | Diameter dimension on a layout. |
| `dimradius` (`dimr`) | Radius dimension on a layout. |
| `dimstyle` (`textstyle`) | Create or edit a named annotation style (text height, arrows). |
| `dot` (`annotationdot`) | Model-space annotation dots: a label bubble anchored to a 3D point. Dots keep their size on screen and always face the camera. |
| `exportdxf` | Export the active layout sheet (or the model) to DXF. |
| `exportpdf` (`pdf`) | Export the current layout, or all of them, to a PDF. |
| `exportsvg` | Export the current layout to an SVG file. |
| `hatch` | Fill a region with a pattern: on a sheet, as it always was, and in the model as an object of its own (#33). |
| `hatchpatterns` (`loadpat`, `loadhatchpatterns`) | Hatch patterns from .pat files (#92): Load installs the patterns in one, Delete takes one off again. The app's own are always there. |
| `layout` | Manage paper layouts: New (with paper size), Rename, Delete, Duplicate or List. |
| `leader` | Leader on a layout: an arrow, a bent line and a text. |
| `make2d` | Project the picked objects (or everything visible) to 2D curves as seen from the current view, hidden lines on their own layer. |
| `printsheets` (`print`, `plot`) | Print sheets, or save them as one PDF, choosing them from the set. |
| `revision` | Add a row to this sheet's revision table (drawn by the title block). |
| `scalebar` | Place a scale bar on a layout, at the scale of the detail under it. |
| `sheetindex` | Place an index of all sheets as a note on the current layout. |
| `text` (`note`, `textobject`, `textcurves`) | Place text: a note on a sheet, editable lettering in the model. |
| `titleblock` | Add or edit the layout's title block: project, title and author; date, sheet and scale fill in themselves. |

## Editing

| Command | Does |
|---|---|
| `boundingbox` (`bb`) | Create the world-aligned bounding box of the selection. |
| `chamfer` | Bevel the corner between two curves with straight cut-offs. |
| `delete` (`del`, `erase`) | Delete the selected objects, or held control points, faces or curve segments; on a sheet, the picked sheet items. |
| `dir` | Show which way curves run and which way surfaces face. |
| `explode` (`x`) | Break objects into their parts: polysurfaces into surfaces, polycurves into segments. |
| `fillet` | Round the corner between two curves, or fillet a solid's edges. |
| `filletcorners` | Round every corner of a polyline at once, straight and arc pieces alike. |
| `flip` | Turn curves round and surfaces inside out, as Rhino's Flip does. |
| `hide` | Hide the selected objects. |
| `hideindetail` | Hide the objects you pick in the detail you are inside, and nowhere else: the model and every other detail still show them. |
| `insertknot` (`insertcontrolpoint`) | Add a control point to a curve without moving the curve. |
| `join` (`j`) | Join curves into one curve, or surfaces that share edges into a polysurface. |
| `layer` | Layer actions: New, Current, Show, Hide, Rename, Weight, Linetype or Hatch. |
| `material` (`mat`) | Assign a look (metallic/roughness/opacity) for rendered display and GLB/USD export. |
| `offset` | Offset a curve to one side, by dragging or typing a distance. |
| `plugins` | List loaded plugins and where they came from. |
| `rebuild` | Rebuild curves with a set point count and degree. |
| `recordhistory` (`history`) | Toggle record history: loft/extrude/revolve outputs rebuild when their input curves are edited. |
| `redo` | Redo the last undone change. |
| `removecontrolpoint` | Delete the control points you are holding, as Delete does. |
| `removeknot` | Take a knot out of a curve and say how far the curve moved. |
| `rename` | Rename an object. |
| `selall` (`sa`) | Select everything. |
| `selnone` (`sn`) | Clear the selection. |
| `show` (`unhide`) | Show every hidden object again. |
| `showindetail` | Show everything the detail you are inside has hidden. |
| `showselected` (`unhideselected`) | Show the hidden objects you pick and leave the rest hidden. |
| `showselectedindetail` | Show the objects you pick of those the detail you are inside has hidden, and leave the rest hidden there. |
| `smooth` | Relax a curve's control points toward their neighbours. |
| `split` | Split a curve, surface, hatch or picture with cutting objects, or a curve at Points picked on it. |
| `splitpoints` | Split, cutting a curve at points picked on it rather than by cutters. |
| `trim` (`tr`) | Cut objects with the cutters and take away the part clicked. |
| `undo` | Undo the last change. |

## Files

| Command | Does |
|---|---|
| `export` (`exp`) | Export what is picked: picked before, it goes without asking. |
| `import` (`imp`) | Import a model file into the current one, or place an image as a picture. |
| `new` | Clear the scene and start a new document. |
| `open` | Open a model, replacing the current one. |
| `save` | Save the model as .byrd, or to another format by its extension (e.g. .3dm). |
| `setdefaultapp` | Make Blackbyrd3D the default application for .byrd files. |

## Help

| Command | Does |
|---|---|
| `help` (`?`) | Describe a command, or list every command by category. |

## Organisation

| Command | Does |
|---|---|
| `audit` | Check every object's geometry for validity. |
| `block` | Turn a selection into a block definition and one instance in its place: pick the objects, then the base point, then name it. The base point is where 'insert' later puts its point. |
| `blocklist` (`blockmanager`) | List the block definitions with their instance counts. |
| `breptomesh` (`meshify`) | Convert BREP objects into lightweight native meshes. |
| `bringforward` (`bringforwards`) | Nudge the selected objects one step towards the front. |
| `bringtofront` (`bf`) | Draw the selected objects on top of overlapping ones. |
| `changelayer` (`tolayer`) | Move objects to a layer by name (created if missing). |
| `count` | Count objects: totals by block, kind and layer (for takeoffs). |
| `getusertext` | Report the user text on the selected objects, as Rhino's GetUserText does: one key's value, or with Enter every key. |
| `group` | Group objects so clicking one selects them all. |
| `insert` | Insert an instance of a block definition at a point. |
| `linetype` (`lt`, `setlinetype`) | Set the dash style of selected objects (Continuous/Dashed/…/ByLayer). |
| `lock` | Lock what is picked: still drawn and snapped to, but not pickable. |
| `lockother` | Lock everything except what you picked, as Rhino's LockOther does. |
| `matchprops` (`matchproperties`) | Copy an object's layer, colour, material, print width and hatch. |
| `meshtobrep` | Convert mesh objects into BREP shells of flat triangles. |
| `pointcloud` (`pc`) | Point clouds: `info` says what a scan holds; `subsample` keeps an even fraction of its points, which is the cheap way to make a scan the laptop can orbit. |
| `printwidth` (`plotweight`, `printweight`) | Set the pen width selected objects plot with, or ByLayer. |
| `purge` | Remove empty layers and unused block definitions. |
| `sectionhatch` (`sectionstyle`) | Set how a section cut through selected objects is filled. |
| `sendbackward` (`sendbackwards`) | Nudge the selected objects one step towards the back. |
| `sendtoback` (`sb`) | Draw the selected objects behind overlapping ones. |
| `setusertext` (`setattributeusertext`) | Set a key of user text on the selected objects, as Rhino's SetUserText does. |
| `ungroup` | Take the outermost group off the selected objects. |
| `unlockall` (`unlock`) | Unlock every locked object, and every locked item on every sheet, whichever space it is run from. A detail's view lock is not one of them: that is `detaillock`'s. |
| `what` | Report details of the selected objects. |

## Selection

| Command | Does |
|---|---|
| `invert` (`selinv`) | Invert the selection. |
| `isolate` | Hide everything but the selected objects; 'unisolate' brings it back. |
| `selcrv` (`selcurves`) | Select all curves. |
| `seldup` | Select later duplicates of identical, identically-placed objects. |
| `selfilter` (`selectionfilter`) | Restrict viewport picking to one kind of object (Off = anything). 'selfiltertoggle' (F6-style) pauses/resumes without forgetting. |
| `selfiltertoggle` (`sft`) | Pause/resume the selection filter without changing its kind. |
| `selhatch` (`selhatches`) | Select all hatches. |
| `sellast` | Select the most recently created object. |
| `sellayer` | Select every object on a layer. |
| `selname` | Select objects whose name contains the given text. |
| `selpointcloud` (`selpc`, `selpointclouds`) | Select all point clouds. |
| `selprev` | Restore the previous selection. |
| `selpt` (`selpoints`) | Select all point objects. |
| `selsolid` (`selsolids`) | Select all solids. |
| `selsrf` (`selsurfaces`) | Select all surfaces. |
| `unisolate` | Show again what 'isolate' hid. |

## Solid editing

| Command | Does |
|---|---|
| `booleansplit` (`bsplit`) | Split solids with cutters, keeping every piece. |
| `cap` | Close the planar holes of open surfaces to make solids. |
| `chamferedge` (`che`) | Chamfer edges. Ctrl+Shift-click edges first to chamfer only those; otherwise every edge of the selected solids. |
| `contour` | Section curves through objects at even spacing along Z, X, Y or the CPlane normal. |
| `filletedge` (`fe`) | Fillet edges. Ctrl+Shift-click edges first to fillet only those; otherwise fillets every edge of the selected solids. |
| `intersect` (`int`) | Curves where two surfaces or solids meet. |
| `mergeallcoplanarfaces` (`mergeallfaces`) | Fuse coplanar neighbouring faces of each selected polysurface. |
| `pushpull` (`pp`, `moveface`) | SketchUp-style push/pull: click a face, then drag or type how far. Positive pushes the face outward, negative carves inward. |
| `section` (`sec`) | Cut the selection with a plane drawn as a line across it. |

## Solids

| Command | Does |
|---|---|
| `box` | Box from a base and height; Center spreads the base evenly. |
| `cone` | Cone from base center, radius and apex height, standing on the CPlane. |
| `cylinder` (`cyl`) | Cylinder from base center, radius and height, standing on the CPlane. |
| `sphere` (`sph`) | Sphere from center and radius; 2Point spans a diameter instead. |
| `torus` | Torus from center, major radius and tube radius. |

## Surfaces

| Command | Does |
|---|---|
| `blendcrv` (`blend`) | Blend curve between two curve ends, Tangent or Position. |
| `blendsrf` | G1 blend surface between two Ctrl+Shift-picked surface edges. |
| `dupborder` | Copy the open borders of surfaces, or the boundary of hatches, as curves. |
| `dupedge` | Duplicate Ctrl+Shift-picked edges as curves. |
| `dupfaceborder` | Duplicate the border wires of Ctrl+Shift-picked faces as curves. |
| `edgesrf` (`srfedges`) | Surface from 2, 3 or 4 connected edge curves. |
| `extendsrf` | Extend a surface past a Ctrl+Shift-picked boundary edge. |
| `extractisocurve` (`isocurve`) | Copy isocurves of a surface at picked points, in U, V or Both. |
| `extractsrf` (`extractsurface`, `extractface`) | Pull Ctrl+Shift-picked faces out of the polysurfaces holding them. |
| `extrude` (`ext`, `extrudecrv`, `extrudesrf`) | Extrude curves or surfaces straight out, by dragging or typing a distance; Cap, BothSides and KeepOriginal options. |
| `helix` | Helix from base center, radius, pitch and turns. |
| `loft` | Surface through two or more profile curves in order; Style Normal or Ruled. |
| `offsetsrf` | Offset surfaces along their normal, by dragging or typing a distance. |
| `patch` (`networksrf`) | Surface filling a boundary of two or more curves. |
| `pipe` | Pipe of a set radius around rail curves, capped or open. |
| `planarsrf` (`planar`, `planesrf`) | Planar surfaces from closed planar curves. |
| `plane` (`rectsrf`) | A rectangular plane corner to corner; or 3Points to stand it up. |
| `plane3pt` (`3ptplane`, `plane3points`) | A rectangular plane from one edge and a width, standing at any angle. |
| `project` | Project curves onto a surface along the CPlane normal. |
| `pull` | Pull curves onto a surface, each point to its closest. |
| `revolve` (`rev`) | Revolve a curve around an axis by an angle. |
| `shell` | Hollow a solid, leaving it open at the face(s) you pick. |
| `srfpt` (`cornersrf`, `surfacefrompoints`) | A surface from 3 or 4 corners; Enter after the third makes a triangle. |
| `sweep1` (`sweep`) | Sweep a profile curve along one rail. |
| `sweep2` | Sweep a profile curve along two rails. |
| `unrollsrf` (`unroll`) | Unroll planar, cylindrical or conical faces flat onto an Unrolled layer. |
| `untrim` | Remove trims from surfaces: only the holes, or All. |

## Transforms

| Command | Does |
|---|---|
| `align` | Line up the picked objects on the view's plane, as a layout program does: their edges or middles to the bounds of the pick, or spaced evenly with the first and the last left where they are. |
| `array` | Copies in a grid with set counts and spacing along the CPlane X and Y. |
| `arraypath` (`arraycrv`) | Copies along a curve; Freeform, Roadlike or no rotation. |
| `arraypolar` | Copies in a ring around a center, over a set angle. |
| `copy` (`co`, `cp`) | Copy objects or held parts from one point to others; Vertical copies along the CPlane normal only. |
| `mirror` (`mi`) | Mirror objects across a line picked in the CPlane; Copy keeps the original. |
| `move` (`m`) | Move objects or held parts from one point to another; Vertical moves along the CPlane normal only. |
| `orient` (`o2`) | Remap objects from two reference points to two target points (rotation + translation, Scale=Yes matches the point spacing). |
| `orient3pt` (`o3`) | Remap objects from three reference points to three target points (full 3D reorientation). |
| `projecttocplane` (`flatten`) | Flatten curves/surfaces/points onto the construction plane. |
| `rotate` (`ro`) | Rotate around the CPlane normal: type an angle, or pick a reference direction and drag it to its new heading (live preview). |
| `rotate3d` (`ro3`) | Rotate around an arbitrary axis picked as two points: type an angle, or point at a reference direction and swing it round to where it should end up (live preview). |
| `scale` (`sc`) | Scale about a base point: type a factor, or grab a reference point and drag it to its new position (live preview). |
| `scale1d` | Stretch along one direction only: type a factor and it stretches the way the cursor is pointing, or set the axis with a reference point and drag that to where it should end up. |
| `scale2d` | Scale in the CPlane only (thickness along the CPlane normal is kept). |
| `scalenu` | Scale by a different amount along each axis: type the three factors, or grab a reference point and drag it to where it should end up (live preview either way). |
| `setpt` (`setpoints`) | Force chosen coordinates of every control point to one value — the classic way to flatten walls onto a level (Z) or line things up on an axis. |

