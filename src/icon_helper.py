"""
图标辅助模块
- 从 EXE / LNK / 文件夹 提取图标
- 解析 .lnk 快捷方式获取目标路径
- 返回 QPixmap
"""
import os
import struct
from pathlib import Path
from typing import Optional, Tuple

from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtCore import QFileInfo, QSize


# ──────────────────────────────────────────
#  解析 .lnk 快捷方式
# ──────────────────────────────────────────
def resolve_lnk(lnk_path: str) -> Tuple[str, str]:
    """
    解析 Windows .lnk 文件，返回 (目标路径, 名称)
    优先用 win32com，降级用纯二进制解析
    """
    name = Path(lnk_path).stem

    # 方法1：win32com（最准确）
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        target = shortcut.Targetpath
        if target:
            return target, name
    except Exception:
        pass

    # 方法2：纯二进制解析 LNK（Shell Link Binary File Format）
    try:
        target = _parse_lnk_binary(lnk_path)
        if target:
            return target, name
    except Exception:
        pass

    return lnk_path, name


def _parse_lnk_binary(lnk_path: str) -> Optional[str]:
    """最小化解析 LNK 文件头，提取本地路径"""
    with open(lnk_path, "rb") as f:
        data = f.read()

    # LNK magic
    if data[:4] != b'\x4c\x00\x00\x00':
        return None

    # HeaderSize = 0x4c (76 bytes)
    # LinkFlags at offset 0x14
    link_flags = struct.unpack_from("<I", data, 0x14)[0]
    has_link_target_id_list = bool(link_flags & 0x01)
    has_link_info = bool(link_flags & 0x02)

    offset = 0x4c  # after header

    # 跳过 LinkTargetIDList
    if has_link_target_id_list:
        id_list_size = struct.unpack_from("<H", data, offset)[0]
        offset += 2 + id_list_size

    if not has_link_info:
        return None

    # LinkInfo
    li_size = struct.unpack_from("<I", data, offset)[0]
    li_flags = struct.unpack_from("<I", data, offset + 8)[0]
    local_base_offset = struct.unpack_from("<I", data, offset + 16)[0]

    if li_flags & 0x01:  # VolumeIDAndLocalBasePath
        local_base = data[offset + local_base_offset:].split(b'\x00')[0]
        try:
            return local_base.decode("gbk")
        except Exception:
            return local_base.decode("utf-8", errors="replace")

    return None


# ──────────────────────────────────────────
#  自动识别拖入文件
# ──────────────────────────────────────────
def classify_drop(file_path: str) -> dict:
    """
    根据拖入文件类型，返回识别结果字典：
    {
        "type": "open_software" / "ue_project" / "open_path",
        "name": str,
        "target_path": str,   # 实际目标路径
        "icon_path": str,     # 图标来源路径（用于提取图标）
    }
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    # .lnk 快捷方式 → 解析目标
    if suffix == ".lnk":
        target, name = resolve_lnk(file_path)
        target_path = Path(target)
        icon_src = target if os.path.exists(target) else file_path
        if target_path.suffix.lower() == ".exe":
            return {"type": "open_software", "name": name,
                    "target_path": target, "icon_path": icon_src}
        elif target_path.suffix.lower() == ".uproject":
            return {"type": "ue_project", "name": name,
                    "target_path": target, "icon_path": icon_src}
        else:
            return {"type": "open_path", "name": name,
                    "target_path": target, "icon_path": icon_src}

    # .exe 直接拖入
    elif suffix == ".exe":
        return {"type": "open_software", "name": path.stem,
                "target_path": file_path, "icon_path": file_path}

    # .uproject
    elif suffix == ".uproject":
        return {"type": "ue_project", "name": path.stem,
                "target_path": file_path, "icon_path": file_path}

    # 文件夹
    elif path.is_dir():
        return {"type": "open_path", "name": path.name,
                "target_path": file_path, "icon_path": file_path}

    # 其他文件
    else:
        return {"type": "open_path", "name": path.stem,
                "target_path": file_path, "icon_path": file_path}


# ──────────────────────────────────────────
#  提取图标 → QPixmap
# ──────────────────────────────────────────
def get_file_icon(file_path: str, size: int = 48) -> QPixmap:
    """
    从文件提取图标，返回 QPixmap。
    优先从 EXE 提取内置图标，否则用系统关联图标。
    """
    # 方法1：win32ui 提取 EXE 内置图标（最高质量）
    try:
        pm = _extract_exe_icon_win32(file_path, size)
        if pm and not pm.isNull():
            return pm
    except Exception:
        pass

    # 方法2：Qt 系统文件图标
    try:
        provider = QFileIconProvider()
        info = QFileInfo(file_path)
        icon = provider.icon(info)
        pm = icon.pixmap(QSize(size, size))
        if pm and not pm.isNull():
            return pm
    except Exception:
        pass

    return QPixmap()


def _extract_exe_icon_win32(file_path: str, size: int) -> Optional[QPixmap]:
    """用 win32api 提取 EXE/ICO 图标"""
    import win32api
    import win32con
    import win32gui
    import win32ui
    from ctypes import windll

    # 用 ExtractIconEx 提取
    large, small = win32gui.ExtractIconEx(file_path, 0)
    icons = large if size >= 32 else small
    other = small if size >= 32 else large

    icon_handle = None
    if icons:
        icon_handle = icons[0]
        # 销毁未用的
        for h in (other or []):
            win32gui.DestroyIcon(h)
        for h in icons[1:]:
            win32gui.DestroyIcon(h)
    elif other:
        icon_handle = other[0]
        for h in other[1:]:
            win32gui.DestroyIcon(h)

    if not icon_handle:
        return None

    try:
        # 创建内存 DC 和位图
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hdc_mem = hdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(hdc, size, size)
        hdc_mem.SelectObject(bmp)
        hdc_mem.FillSolidRect((0, 0, size, size), 0x00000000)
        win32gui.DrawIconEx(hdc_mem.GetSafeHdc(), 0, 0, icon_handle,
                            size, size, 0, None, win32con.DI_NORMAL)

        bmp_info = bmp.GetInfo()
        bmp_data = bmp.GetBitmapBits(True)

        image = QImage(bmp_data, bmp_info["bmWidth"], bmp_info["bmHeight"],
                       QImage.Format.Format_ARGB32)
        return QPixmap.fromImage(image)
    finally:
        win32gui.DestroyIcon(icon_handle)


# ──────────────────────────────────────────
#  在配置文件里存储/读取图标缓存路径
# ──────────────────────────────────────────
import base64, json
from pathlib import Path as _Path

_ICON_CACHE_DIR = _Path(os.environ.get("APPDATA", _Path.home())) / "AutoTasker" / "icons"


def save_icon_cache(task_id: str, pixmap: QPixmap) -> Optional[str]:
    """把图标保存为 PNG，返回缓存路径"""
    if pixmap.isNull():
        return None
    _ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _ICON_CACHE_DIR / f"{task_id}.png"
    pixmap.save(str(path), "PNG")
    return str(path)


def load_icon_cache(task_id: str) -> Optional[QPixmap]:
    """从缓存加载图标"""
    path = _ICON_CACHE_DIR / f"{task_id}.png"
    if path.exists():
        pm = QPixmap(str(path))
        return pm if not pm.isNull() else None
    return None
