# Changelog

All notable changes to Mitscreen are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/), versions follow SemVer.

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
