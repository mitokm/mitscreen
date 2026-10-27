# Cài đặt Mitscreen / Installation

Hướng dẫn từng bước cho Windows 10/11. English summary at the bottom.

![Cài đặt Mitscreen](docs/screenshots/settings.png)

## 1. Yêu cầu

| Mục | Cần có |
|---|---|
| Hệ điều hành | Windows 10 hoặc Windows 11 |
| Python | 3.12 trở lên (`python --version` kiểm tra được) |
| Thư viện Python | `PySide6-Essentials` và `Pillow` — cài bằng pip ở bước 3 |
| Quay video (tuỳ chọn) | `ffmpeg` có trong `PATH` (`ffmpeg -version` kiểm tra được) |

> Mitscreen không cần `pywin32` — mọi thao tác Win32 đều làm bằng `ctypes` trong thư viện chuẩn.

## 2. Lấy mã nguồn

```powershell
git clone https://github.com/mitokm/mitscreen.git
cd mitscreen
```

Hoặc tải bản phát hành dạng `.zip` từ trang **Releases**, giải nén vào một thư mục cố định (đừng chạy thẳng trong thư mục Downloads nếu bạn muốn đặt shortcut/autostart — đường dẫn sẽ đổi khi dọn dẹp).

## 3. Tạo môi trường và cài thư viện

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` chỉ gồm:

```text
PySide6-Essentials
Pillow
```

### Cài offline (không có mạng)

Nếu đã có sẵn thư mục wheel `.wheels\` đi kèm:

```powershell
.\.venv\Scripts\python.exe -m pip install --no-index --find-links .wheels PySide6-Essentials Pillow
```

## 4. Chạy

```powershell
.\Mitscreen.cmd
```

`Mitscreen.cmd` tự dùng `pythonw.exe` trong `.venv` nếu có (không hiện cửa sổ console), nếu không thì dùng `pythonw` trong `PATH`. Bạn cũng có thể chạy trực tiếp:

```powershell
.\.venv\Scripts\pythonw.exe run.pyw
```

Dấu hiệu chạy thành công:

- Icon chữ **M** xuất hiện trong khay hệ thống (Windows 11 có thể giấu icon mới trong nút `^` — xem mục Khắc phục trong [README](README.vi.md#khắc-phục-sự-cố)).
- Bấm trái icon → lớp phủ chọn vùng mở ra.
- Nhấn `Print Screen` → chụp vùng chọn.

## 5. Tạo shortcut Desktop

1. Chuột phải lên `Mitscreen.cmd` → **Send to → Desktop (create shortcut)**, hoặc tạo shortcut mới trỏ tới:
   - Target: `<thư mục Mitscreen>\Mitscreen.cmd`
   - Start in: `<thư mục Mitscreen>`
2. Đổi tên shortcut thành **Mitscreen**; icon có sẵn ở `assets\mitscreen.ico` (chuột phải shortcut → Properties → Change Icon…).

## 6. Khởi động cùng Windows

Mở Mitscreen → **Cài đặt → Quay & hệ thống** → bật **Khởi động cùng Windows**. Tuỳ chọn này đăng ký autostart cho đúng bản đang chạy; tắt đi là gỡ đăng ký. Không cần quyền admin.

## 7. Cài ffmpeg (chỉ khi cần quay video)

1. Tải bản build Windows từ trang chính thức của ffmpeg hoặc qua trình quản lý gói bạn quen dùng, ví dụ `winget install Gyan.FFmpeg`.
2. Đảm bảo thư mục chứa `ffmpeg.exe` nằm trong `PATH`, mở terminal mới và kiểm tra:

```powershell
ffmpeg -version
```

3. Mitscreen cũng tự tìm ở hai vị trí phổ biến `C:\ffmpeg\bin\ffmpeg.exe` và `C:\Program Files\ffmpeg\bin\ffmpeg.exe` nếu `PATH` chưa có.

## 8. Gỡ / chạy portable

- **Dừng app:** chuột phải icon khay → **Thoát**.
- **Gỡ:** xoá thư mục mã nguồn và thư mục dữ liệu `%APPDATA%\Mitscreen` (trong đó có `settings.json`, thư viện ảnh và log). Ảnh đã lưu trong `Pictures\Mitscreen` là của bạn — giữ hay xoá tuỳ bạn.
- **Portable:** đặt biến môi trường `MITSCREEN_HOME` trỏ tới một thư mục bạn chọn; toàn bộ cấu hình, thư viện và log sẽ nằm ở đó. Nếu tiến trình không ghi được AppData, Mitscreen cũng tự rơi về `<thư mục app>\data`.

---

## English summary

1. Install Python 3.12+ on Windows 10/11 (and ffmpeg if you want recording).
2. `git clone https://github.com/mitokm/mitscreen.git && cd mitscreen`
3. `python -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
4. Run `.\Mitscreen.cmd` — the app appears as a tray icon. Left-click = region capture, `Print Screen` works out of the box.
5. Optional: create a Desktop shortcut to `Mitscreen.cmd` (icon: `assets\mitscreen.ico`) and enable **Start with Windows** in Settings.
