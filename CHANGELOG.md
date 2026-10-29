# Changelog

All notable changes to Mitscreen are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/), versions follow SemVer.

## [Unreleased]

### Added
- **White-canvas growth (Screenpresso-style)**: when an annotation — arrow,
  shape, freehand stroke, text, or a step badge — spills past the picture's
  edge, the picture automatically grows a white margin so the whole
  annotation fits instead of being clipped. One Ctrl+Z undoes both the
  growth and the drawing. A manual “Mở rộng nền trắng…” action in the
  Effects menu pads all four sides by a chosen amount.
- **Arrow styles** for the Arrow tool (options bar): single (classic),
  double-headed, dot-tail, and solid block — all in the current colour/width.
- **Letter badges**: the step-badge tool can stamp letters (`a, b, c…` or
  `A, B, C…`) as well as numbers, and a new **“từ” start-value field** sets
  where the sequence begins (e.g. start at 3, or at c).
- **Magnifier loupe tool** (`Z`): drag a circle over any area to embed a
  zoomed view of it (1.5×–4×, selectable), with a coloured ring and shadow.

### Fixed
- Switching to the badge tool no longer resets the counter to 1 — the
  sequence now continues across tool switches, and the start value is
  editable in the options bar.
- Editor keyboard shortcuts promised in the toolbar labels were never wired
  up and did nothing: **Ctrl+S** (save), **Ctrl+Z** (undo), **Ctrl+Y** /
  Ctrl+Shift+Z (redo), **Ctrl+C** (copy) and **Ctrl+P** (print) now work.
  While a text annotation is being typed they act on the text field instead
  of the canvas, and **Esc** now closes the editor when the canvas is idle
  (it still cancels an in-progress text edit or drag first).

### Changed
- Quick Bar button order: **Record now comes before Capture**.
- The workspace / library panel now **docks to the bottom-right corner** of
  the active screen (above the taskbar) whenever it opens, like a tray popup.
- Captures are now **auto-saved the moment they are taken**: when the editor
  opens after a capture it is bound to the file that was just written, and
  Ctrl+S overwrites that same file — no Save-As step, and closing the editor
  can no longer lose a capture. Opening an image from the library for editing
  likewise binds the editor to the library file itself.
- Clicking the tray icon now opens the **library / workspace** panel instead
  of starting a region capture (capture stays on the hotkeys, Quick Bar and
  tray menu).
- Settings: the Quick Bar on/off checkbox is labelled “Bật thanh truy cập
  nhanh (Quick Bar)” and the after-capture options state the auto-save
  behaviour.
- Quick Bar collapsed state: the thin sliver is replaced by a 72 × 78 px black
  stick-figure spider hanging upside down from its web line — folded sitting legs
  hooked at the top, both hands gripping the line, masked head with white eyes at
  the bottom. Strokes get a thin pale rim so the figure reads on light and dark
  desktops. Hovering the spider expands the bar as before.

## [1.0.0] — 2026-10-27

First public release.

### Capture & overlay
- Region, window, full-screen and multi-monitor capture in physical pixels (per-monitor DPI aware).
- Frozen-desktop region overlay with dimming, a magnifier, absolute coordinates and a live hex colour readout.
- Recapture-previous-region, 3-second delayed capture, and a colour picker that copies a pixel's hex code.

### After capture & Quick Bar
- Four after-capture behaviours; default is *copy to clipboard + open editor* with no intermediate menu.
- Floating Quick Bar: draggable, position remembered, auto-folds into a thin sliver, hides itself during capture/recording, with a function menu showing current hotkeys.

### Editor
- 12 tools: crop, cutout & stitch, arrow, line, rectangle, ellipse, pen, highlighter, text, blur, mosaic, step-number badges.
- Cutout & stitch removes a full-width/full-height strip in one undoable step.
- 24-step undo/redo, Ctrl+wheel zoom, Space+drag pan, Shift constraint to square/45°.
- Pretty frame + drop shadow, text watermark, print, copy (image + file), PNG/JPEG/WebP export.
- Export controls for DPI metadata, save scale, PNG compression and JPEG/WebP quality.
- File-name patterns with time codes, live preview, ask-on-save, and F2 rename (file + library sidecar).

### Workspace, library & recording
- Workspace window with sidebar, thumbnail grid and action bar; monthly library with JSON sidecars.
- Region recording through ffmpeg gdigrab to H.264 MP4, optional cursor, FPS/CRF settings, a red frame drawn outside the recorded area, and a floating stop bar.

### System
- Tray icon, 6 rebindable global hotkeys via Win32 `RegisterHotKey` (ctypes, no pywin32), single-instance guard, start-with-Windows, rotating 256 KB diagnostic log, writable-data-dir fallback chain (`%APPDATA%` → `%LOCALAPPDATA%` → portable `data\`, `MITSCREEN_HOME` override).
- Test/tool suite in `tools/` (smoke, cutout, after-capture, colour-pick, workspace, export, naming, recording-frame, Quick Bar, hotkey and end-to-end tests).
