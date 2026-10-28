<p align="center">
  <img src="assets/mitscreen.png" alt="Mitscreen logo" width="110">
</p>

<h1 align="center">Mitscreen</h1>

<p align="center">
  <strong>A fast, personal screenshot &amp; screen-recording tool for Windows</strong><br>
  Capture a region, a window or the whole screen · annotate it properly · cut out the
  boring middle and stitch the rest together · record a region to MP4 — all from the tray,
  a floating Quick Bar, or a single hotkey.
</p>

<p align="center">
  <a href="README.vi.md">🇻🇳 Tiếng Việt</a> ·
  <a href="INSTALL.md">Installation</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

<p align="center">
  <img alt="Platform: Windows 10 / 11" src="https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-0078d4">
  <img alt="Python 3.12+" src="https://img.shields.io/badge/python-3.12%2B-3776ab">
  <img alt="UI: PySide6 / Qt 6" src="https://img.shields.io/badge/UI-PySide6%20%2F%20Qt%206-41cd52">
  <img alt="Version 1.0.0" src="https://img.shields.io/badge/version-1.0.0-blue">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Dependencies: PySide6 + Pillow" src="https://img.shields.io/badge/dependencies-PySide6%20%2B%20Pillow-lightgrey">
</p>

![Mitscreen at a glance — editor, region overlay and workspace](docs/hero-collage.png)

> Mitscreen is an **independent, from-scratch implementation** written in Python + Qt.
> It borrows a *workflow* — capture → annotate → share — that every good screenshot tool
> converges on, but **no code, icons, assets, strings or licences from any commercial
> screenshot product are used**. Every icon in the app is drawn at runtime with `QPainter`,
> including the “M” logo.

---

## Screenshots

### The editor — annotate, blur, number, cut & stitch

![Editor with arrow, rectangle, highlighter, blur and step badges](docs/screenshots/editor.png)

### Region selection — frozen desktop, magnifier, live colour code

![Region overlay with magnifier and coordinates](docs/screenshots/overlay.png)

### Quick Bar — a floating dock that folds into a hanging spider

![Quick Bar: expanded, menu, collapsed](docs/quickbar-sequence.png)

<table>
  <tr>
    <td align="center"><img src="docs/screenshots/quickbar.png" alt="Quick Bar expanded"><br><sub><b>Expanded</b> — capture, record, folder, menu, close</sub></td>
    <td align="center"><img src="docs/screenshots/quickbar-menu.png" alt="Quick Bar function menu"><br><sub><b>Function menu</b> — recapture last region, timer, colour picker, workspace…</sub></td>
    <td align="center"><img src="docs/screenshots/quickbar-collapsed.png" alt="Quick Bar collapsed into a hanging spider figure"><br><sub><b>Collapsed</b> — a small black spider figure hanging from its web line (72 × 78 px)</sub></td>
  </tr>
</table>

### Workspace — every capture, one panel

![Workspace: sidebar, thumbnail grid and action bar](docs/screenshots/workspace.png)

### Settings — capture behaviour, file size and file naming in one place

![Settings: format, DPI, scale, PNG compression, naming pattern, after-capture behaviour, watermark](docs/screenshots/settings.png)

### Cutout & stitch — remove a strip, the two sides join

![Cutout before and after](docs/cutout-before-after.png)

<table>
  <tr>
    <td align="center"><img src="docs/screenshots/cutout.png" alt="Cutout strip highlighted in red"><br><sub><b>Before</b> — the strip to remove is painted red, across the full width</sub></td>
    <td align="center"><img src="docs/screenshots/cutout-result.png" alt="Cutout result, stitched"><br><sub><b>After</b> — the strip is gone and the two parts are stitched together</sub></td>
  </tr>
</table>

### Recording — a red frame that never appears in the video

![Recording frame around the recorded region](docs/screenshots/recording-frame.png)

### Library, history and the app icon at every size

<table>
  <tr>
    <td align="center"><img src="docs/screenshots/history.png" alt="Capture library"><br><sub><b>Library</b> — monthly folders with JSON sidecars</sub></td>
    <td align="center"><img src="docs/screenshots/icon.png" alt="Mitscreen icon at 16–128 px"><br><sub><b>Icon</b> — the “M” at 16, 24, 32, 48, 64 and 128 px, on light and dark</sub></td>
  </tr>
</table>

![Gallery — all twelve screenshots in one picture](docs/gallery-collage.png)

---

## Features

| Area | What you get |
|---|---|
| **Capture** | Region (drag), window (click the window), full screen, multi-monitor, recapture the previous region, 3-second delayed capture |
| **Magnifier** | While selecting: a magnifier at the cursor, absolute coordinates and the hex colour under the pointer |
| **Colour picker** | Click anywhere on screen to copy that pixel’s hex code to the clipboard |
| **After capture** | Default: **copy to clipboard + open the editor** — no intermediate menu. Switchable to *editor only*, *save immediately*, or the classic *action bar (Edit / Copy / Save / Record / Cancel)* |
| **Quick Bar** | Floating bar (top-centre by default): region capture, record, open save folder, function menu, hide. Draggable, remembers its position, folds into a small hanging spider figure when idle, hides itself while you capture or record |
| **Editor** | Crop, **cutout & stitch**, arrow, line, rectangle, ellipse, pen, highlighter, text, blur, mosaic / pixelate, step-number badges |
| **Editing** | 24-step undo/redo, zoom (`Ctrl` + wheel), pan (`Space` + drag), `Shift` constrains to square / 45° |
| **Effects** | Pretty frame (padding + rounded corners + drop shadow), text watermark (colour + opacity), resize by % on save |
| **Export** | PNG / JPEG / WebP, copy to clipboard (image **and** a file, so pasting into Explorer works), print |
| **Smaller files** | Export DPI metadata (72 / 96 / 150 / 300), save scale (100 / 90 / 75 / 50 / 25 %), PNG compression 1–9, JPEG/WebP quality — see [Make files lighter](#make-files-lighter-dpi--scale--compression) |
| **File naming** | Time-code patterns (`snap-%Y%m%d-%H%M%S`), live preview, optional “ask for a name on every save”, rename later with `F2` (renames the file on disk and its library sidecar) |
| **Workspace / library** | Every capture is also kept by month in a library; the workspace panel has a sidebar, a thumbnail grid and an action bar — double-click to edit, right-click to open / copy / reveal / rename / delete |
| **Recording** | ffmpeg `gdigrab` on the selected region → H.264 MP4, optional cursor, FPS and CRF settings, a red frame drawn **outside** the recorded pixels, floating stop bar with elapsed time |
| **System** | Tray icon, 6 global hotkeys, single-instance guard, start with Windows, rotating diagnostic log |

## Quick start

```powershell
git clone https://github.com/mitokm/mitscreen.git
cd mitscreen

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\Mitscreen.cmd          # launches without a console window
```

Requirements: **Windows 10/11, Python 3.12+**, and **`ffmpeg` on `PATH`** if you want
screen recording. Full step-by-step instructions, a desktop-shortcut recipe and an
offline-install variant are in **[INSTALL.md](INSTALL.md)**.

The app lives in the **system tray** — there is no main window. Left-click the tray icon
to capture a region; right-click for the menu.

## Hotkeys

### Global (default)

| Action | Keys |
|---|---|
| Capture region | `Print Screen` |
| Recapture previous region | `Ctrl + Shift + 2` |
| Capture full screen | `Ctrl + Shift + 3` |
| Capture window | `Ctrl + Shift + 4` |
| Record region (start / stop) | `Ctrl + Shift + 5` |
| Open workspace | `Ctrl + Shift + 6` |

Change them in **Settings → Hotkeys**. If another app already owns a combination,
Mitscreen tells you at startup and writes the reason to `app.log` (Snipping Tool,
OneDrive and other screenshot tools are the usual owners of `Print Screen`).

### In the editor

| Keys | Tool / action |
|---|---|
| `C` / `U` | Crop / **Cutout & stitch** |
| `A` / `L` / `R` / `E` | Arrow / Line / Rectangle / Ellipse |
| `P` / `H` / `T` | Pen / Highlighter / Text |
| `B` / `X` / `N` | Blur / Mosaic / Step-number badge |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo (24 steps) |
| `Ctrl+C` / `Ctrl+S` / `Ctrl+Shift+S` / `Ctrl+P` | Copy / Save / Save as… / Print |
| `F2` | Rename the file |
| `Ctrl` + wheel · `Space` + drag · `Shift` + drag | Zoom · pan · constrain to square / 45° |
| `Esc` | Cancel the shape being drawn |

## Highlights in detail

### After capture — no menu unless you ask for one

By default, releasing the mouse **copies the image to the clipboard and opens the editor
immediately**. Closing the editor does not nag you to save, because the image is already
on the clipboard and in the library.

| Setting → Capture → *After capture* | Behaviour |
|---|---|
| **Copy to clipboard + open editor** *(default)* | Copy, then edit |
| Editor only | No copy; edit, then save yourself |
| Save immediately (no editor) | Write straight to the save folder + library, with a toast showing the path |
| Show action bar | The classic bar: Edit / Copy / Save / Record / Cancel |

Recording (`Ctrl+Shift+5` or the Quick Bar button) **always** starts right after you pick
the region, regardless of this setting.

### Cutout & stitch

1. Pick **Cutout & stitch** (`U`).
2. Drag a band across the part you want gone. The band always spans the **full width or
   full height** — whichever matches the longer side of your drag — and is painted red,
   so you see exactly what will disappear.
3. Release: the band is deleted and **the two remaining parts join together**.

Drag wider than tall → a horizontal cut, the image gets shorter. Drag taller than wide →
a vertical cut, the image gets narrower. Bands smaller than 6 px are ignored, and the
whole operation is **one undo step**.

### Quick Bar

A small floating dock, anchored to the **top-centre of the primary screen** by default.

- **Hover** → it expands: *Capture region · Record · save folder · function menu · ✕*.
- **Leave it for ~1 s** → it folds back into a 72 × 78 px figure: a black stick-figure spider hanging upside down from its web line, both hands gripping the line. Hover over the spider and the bar expands again.
- **Drag** it by any empty area to move it; the position is remembered.
- It **hides itself while capturing or recording**, so it never lands in your image or
  video, and comes back immediately afterwards.
- Turn it on/off from the tray menu or **Settings**, and turn the auto-fold off if you
  prefer it always expanded.

The function menu (`⌄`) contains: capture region, recapture previous region, full screen,
window capture, 3-second delayed capture, colour picker, workspace, and settings — each
with its current hotkey shown on the right.

### Workspace

Open it from the tray menu, `Ctrl+Shift+6`, or the Quick Bar menu.

- **Left sidebar:** *Recent images*, *Save folder*, *Settings…*, and a **＋ New capture**
  button (region / window / full screen / record).
- **Centre grid:** thumbnails, newest first, with file name and time. Double-click to
  edit; right-click to open / copy / reveal in Explorer / rename / delete.
- **Bottom bar:** *Capture region · Record · Edit… · Share* (copy image / copy path /
  open folder / delete) *· Close*.

### Make files lighter (DPI · scale · compression)

**Settings → Capture → “Image & size”:**

| Option | Effect |
|---|---|
| **Export DPI** (72 / 96 / 150 / 300) | Writes DPI metadata into PNG/JPEG — changes print / Word insert size, **not** the pixel count |
| **Save scale** (100 / 90 / 75 / 50 / 25 %) | Actually resizes the pixels — the strongest size reduction |
| **PNG compression** (1–9) | 9 = tightest compression, smallest file, slightly slower |
| **JPEG / WebP quality** | Lower = lighter |

These apply to **Save**, **Save as…** and **Quick save** alike — set once, use forever.
Lightest while still sharp: **WebP + 75 % + quality 80**.

### File naming

**Settings → Capture → “File name”:**

| Option | Effect |
|---|---|
| **Pattern** | Time codes: `%Y` year, `%m` month, `%d` day, `%H` hour, `%M` minute, `%S` second — e.g. `snap-%Y%m%d-%H%M%S` |
| **Preview** | Shows the exact file name that will be created, with the current format’s extension |
| **Ask for a name on every new save** | Prompts each time; leave it empty to fall back to the pattern |

Forbidden characters (`< > : " / \ | ? *`) are replaced with `-` automatically, and an
empty pattern falls back to the default.

## Where data lives

The data folder is the first **writable** location in this order:

1. `%APPDATA%\Mitscreen` *(default)*
2. `%LOCALAPPDATA%\Mitscreen`
3. `<app folder>\data` *(portable mode — for accounts/sandboxes that cannot write AppData)*
4. The `MITSCREEN_HOME` environment variable, when set, always wins

| Inside it | Contents |
|---|---|
| `settings.json` | All settings (unknown keys are preserved across versions) |
| `shots\` | Fallback capture folder, used when `Pictures\Mitscreen` is not writable |
| `library\YYYY-MM\` | Library copies + `.json` sidecar metadata |
| `app.log` | Rotating log (256 KB): startup, hotkeys, captures, recordings |
| `crash.log` | Only written when startup itself fails |

Captures go to `%USERPROFILE%\Pictures\Mitscreen\` by default;
recordings are named `rec-YYYYMMDD-HHMMSS.mp4`.

## Architecture

The process runs **DPI-aware in physical pixels** (Qt scaling is disabled in the
launcher): mouse coordinates, window geometry and grabbed bitmaps then share one
coordinate space, which is what makes region capture exact on scaled displays.
The UI scales its fonts by `dpi / 96` instead. All Win32 work (hotkeys, DPI,
window-at-point, autostart) is done with `ctypes` — **no `pywin32` dependency**.

```
run.pyw                 entry point: DPI awareness, single-instance, theme, tray
app/
  config.py             Settings dataclass + writable-data-dir fallback chain
  win32util.py          DPI, RegisterHotKey + native event filter, window-at-point, autostart
  imageutil.py          PIL <-> QImage, grabbing, blur/pixelate, frame, watermark, encoding
  overlay.py            region overlay: frozen desktop, dimming, magnifier, action bar
  quickbar.py           floating Quick Bar: draggable, auto-folding, self-hiding
  editor.py             canvas + 12 tools + undo/redo + save/copy/print
  history.py            workspace window: sidebar + thumbnail grid + action bar
  library.py            library copies + JSON sidecars
  recorder.py           ffmpeg gdigrab wrapper + floating stop bar
  recframe.py           red recording frame (masked hole = never in the video)
  settings_ui.py        settings dialog (capture / hotkeys / recording & system)
  tray.py               controller: tray, hotkeys, capture & recording flows
  theme.py              dark theme, DPI-scaled fonts
  icons.py              every icon drawn with QPainter — including the “M” logo
  logging_util.py       256 KB rotating log
tools/                  test & utility scripts (see below)
assets/                 mitscreen.ico / mitscreen.png
docs/screenshots/       the screenshots used in this README
```

### Source map

| File | Lines | Role |
|---|---:|---|
| `run.pyw` | 105 | Launcher (DPI-aware, single-instance, theme, tray) |
| `app/tray.py` | 554 | Controller: tray icon, hotkeys, capture/record flows, Quick Bar |
| `app/editor.py` | 995 | Editor: canvas, 12 tools, undo/redo, save/copy/print |
| `app/overlay.py` | 445 | Region overlay + magnifier + action bar |
| `app/win32util.py` | 426 | Win32 via ctypes: DPI, hotkeys, window-at-point, autostart |
| `app/quickbar.py` | 339 | Quick Bar |
| `app/icons.py` | 327 | Runtime-drawn vector icons |
| `app/history.py` | 318 | Workspace window |
| `app/settings_ui.py` | 316 | Settings dialog |
| `app/config.py` | 225 | Settings + data-dir fallback |
| `app/recorder.py` | 217 | Screen recording via ffmpeg |
| `app/imageutil.py` | 207 | Image helpers (blur, mosaic, frame, watermark, encode) |
| `app/library.py` | 109 | Library copies + metadata |
| `app/theme.py` | 87 | Dark theme |
| `app/recframe.py` | 62 | Red recording frame |
| `app/logging_util.py` | 27 | Logging |
| `tools/*.py` | 2,666 | 26 test / utility scripts |

**Total ≈ 7,400 lines of Python**, with no runtime dependencies beyond
**PySide6 + Pillow** (plus `ffmpeg` for video).

## Testing

```powershell
.\.venv\Scripts\python.exe tools\smoke_test.py         # core checks: images, settings, library, editor, overlay
.\.venv\Scripts\python.exe tools\cutout_test.py        # cutout & stitch: horizontal/vertical, undo, tiny-band guard
.\.venv\Scripts\python.exe tools\after_capture_test.py # the 4 after-capture behaviours
.\.venv\Scripts\python.exe tools\color_pick_test.py    # colour picker: right pixel, hex copied
.\.venv\Scripts\python.exe tools\workspace_test.py     # workspace: grid, sidebar, action bar, signals
.\.venv\Scripts\python.exe tools\export_test.py        # DPI metadata, scaling, PNG/JPEG compression
.\.venv\Scripts\python.exe tools\naming_test.py        # naming pattern, ask-on-save, rename file + sidecar
.\.venv\Scripts\python.exe tools\recframe_test.py      # recording frame: geometry, mask, clean video
.\.venv\Scripts\python.exe tools\quickbar_test.py      # Quick Bar: size, signals, folding, pause/resume
.\.venv\Scripts\python.exe tools\hotkey_test.py        # hotkey registration + WM_HOTKEY delivery
.\.venv\Scripts\python.exe tools\e2e_test.py           # real capture + a 2.5 s ffmpeg recording
.\.venv\Scripts\python.exe -m pyflakes app run.pyw tools
```

Live tests (`tools\*live_test.py`) attach to a running instance by PID and drive the
real hotkey → drag → copy/editor flow end to end.

## Troubleshooting

| Symptom | Fix |
|---|---|
| No tray icon | Windows 11 hides new icons: **Settings → Personalization → Taskbar → Other system tray icons** → enable Mitscreen |
| A hotkey does nothing | Check `app.log` for `hotkey ... FAILED`; change the combination in Settings (usually Snipping Tool / OneDrive / another screenshot app owns it) |
| Recording fails | Run `ffmpeg -version`; install ffmpeg and put it on `PATH` |
| You want two separate instances | Give each its own `MITSCREEN_HOME` — the single-instance guard is per system, so normally only one instance runs |
| The app will not start | Read `crash.log` in the data folder |

## Known limitations (v1)

- No scrolling capture, webcam/microphone recording, cloud upload/sharing, OCR, or
  library tags/search yet; no multi-image PDF export.
- Recordings are **video only (no audio)** — ffmpeg is already in place to add
  `-f dshow` audio later.
- The recorded region is rounded to an **even size**, as H.264 requires.
- Annotations are baked into the image when you release the mouse — undoable, but a
  shape cannot be moved again after it has been drawn.

## Legal note

Mitscreen is an independent reimplementation for personal use. It does not copy code,
icons, strings, resources or branding from any commercial screenshot product, and it
does not use or circumvent any commercial licence. Only capture screens you have the
right to capture.

## Licence

[MIT](LICENSE) © 2026 mitokm
