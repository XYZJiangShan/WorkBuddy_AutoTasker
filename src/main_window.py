"""
AutoTasker - 主窗口（重设计版）
"""
import sys
import copy
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QTextEdit, QFrame,
    QSystemTrayIcon, QMenu, QMessageBox, QScrollArea, QGridLayout,
    QFileIconProvider, QLineEdit, QGraphicsDropShadowEffect,
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QInputDialog, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QMimeData, QPoint, QFileInfo, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QColor, QAction, QPixmap, QPainter, QPen, QBrush, QDrag, QLinearGradient, QPainterPath

from config_manager import (load_tasks, save_tasks, load_settings, save_settings,
                             new_task, new_action, load_groups, save_groups, new_group)
from executor import TaskExecutor
from scheduler import TaskScheduler
from task_editor import TaskEditorDialog

# ── LOGO 路径 ──
def _logo_path(size: int = 256) -> str:
    """返回 assets/logo_{size}.png 的绝对路径（打包后用 sys._MEIPASS）"""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    # 开发模式：src/../assets/；打包模式：同目录
    for candidate in [
        os.path.join(base, '..', 'assets', f'logo_{size}.png'),
        os.path.join(base, 'assets', f'logo_{size}.png'),
        os.path.join(base, f'logo_{size}.png'),
    ]:
        p = os.path.normpath(candidate)
        if os.path.exists(p):
            return p
    return ""

def _make_logo_icon(size: int = 32) -> QIcon:
    """加载 LOGO 文件，不存在则回退到代码绘制图标"""
    path = _logo_path(256)  # 始终用最高分辨率缩放
    if path:
        pm = QPixmap(path).scaled(size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        if not pm.isNull():
            return QIcon(pm)
    # 回退：代码绘制
    return _fallback_icon(size)

def _fallback_icon(size: int = 32) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor("#7aa2f7"))
    grad.setColorAt(1, QColor("#9ece6a"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size, size, size * 0.2, size * 0.2)
    p.setPen(QPen(QColor("white")))
    p.setFont(QFont("Arial", size // 2, QFont.Weight.Bold))
    p.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, "A")
    p.end()
    return QIcon(pm)

# ══════════════════════════════════════════════
#  主题系统
# ══════════════════════════════════════════════
THEMES = {
    "nebula": {
        "name": "星云",
        "emoji": "🌌",
        "bg":         "#0d0e14",
        "panel":      "#13141c",
        "card":       "#1a1b26",
        "card_hover": "#212236",
        "border":     "#2a2c3e",
        "accent":     "#7aa2f7",
        "accent2":    "#9ece6a",
        "danger":     "#f7768e",
        "warn":       "#e0af68",
        "text":       "#c0caf5",
        "text2":      "#565f89",
        "shortcut":   "#9ece6a",
        "workflow":   "#7aa2f7",
        "log_bg":     "#090a10",
        "log_text":   "#a9b1d6",
    },
    "ocean": {
        "name": "深海",
        "emoji": "🌊",
        "bg":         "#0a0f1e",
        "panel":      "#0f1632",
        "card":       "#162040",
        "card_hover": "#1c2a50",
        "border":     "#243258",
        "accent":     "#4f9cf9",
        "accent2":    "#2dd4bf",
        "danger":     "#f87171",
        "warn":       "#fbbf24",
        "text":       "#dce8ff",
        "text2":      "#4a6fa5",
        "shortcut":   "#2dd4bf",
        "workflow":   "#4f9cf9",
        "log_bg":     "#060b16",
        "log_text":   "#b0c8f0",
    },
    "forest": {
        "name": "原野",
        "emoji": "🌲",
        "bg":         "#0c110c",
        "panel":      "#111711",
        "card":       "#172217",
        "card_hover": "#1d2e1d",
        "border":     "#253325",
        "accent":     "#40c074",
        "accent2":    "#61afef",
        "danger":     "#e06c75",
        "warn":       "#e5c07b",
        "text":       "#d8e8d0",
        "text2":      "#4a7055",
        "shortcut":   "#40c074",
        "workflow":   "#61afef",
        "log_bg":     "#080d08",
        "log_text":   "#a8c8a0",
    },
    "dawn": {
        "name": "曙光",
        "emoji": "☀️",
        "bg":         "#f5f6f8",
        "panel":      "#ffffff",
        "card":       "#f0f2f6",
        "card_hover": "#e8eaf2",
        "border":     "#dde1ea",
        "accent":     "#5a6ef0",
        "accent2":    "#22c55e",
        "danger":     "#dc2626",
        "warn":       "#d97706",
        "text":       "#18191f",
        "text2":      "#6b7485",
        "shortcut":   "#16a34a",
        "workflow":   "#5a6ef0",
        "log_bg":     "#eef0f5",
        "log_text":   "#2d3142",
    },
    "dusk": {
        "name": "晚霞",
        "emoji": "🌸",
        "bg":         "#110e12",
        "panel":      "#1a1520",
        "card":       "#221c28",
        "card_hover": "#2a2232",
        "border":     "#362a3e",
        "accent":     "#e879a0",
        "accent2":    "#fb923c",
        "danger":     "#f87171",
        "warn":       "#fbbf24",
        "text":       "#f5e6f8",
        "text2":      "#8b6a90",
        "shortcut":   "#fb923c",
        "workflow":   "#e879a0",
        "log_bg":     "#0d0a0f",
        "log_text":   "#d4b8e0",
    },
}

# 当前主题（运行时变量）
_current_theme_key = "nebula"

def get_theme() -> dict:
    return THEMES.get(_current_theme_key, THEMES["nebula"])

def set_theme(key: str):
    global _current_theme_key, C
    if key in THEMES:
        _current_theme_key = key
        C = get_theme()

# 初始化 C
C = get_theme()

# ══════════════════════════════════════════════
#  样式表（函数，支持动态主题）
# ══════════════════════════════════════════════
def build_style(c: dict) -> str:
    log_bg   = c.get("log_bg",   "#090a10")
    log_text = c.get("log_text", "#a9b1d6")
    is_light = c.get("bg", "#0").startswith("#f")
    card_shadow = "none" if is_light else "none"
    return f"""
QMainWindow, QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}}
/* 日志 */
QTextEdit#log_view {{
    background-color: {log_bg};
    color: {log_text};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 10px 14px;
    font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 12px;
    line-height: 1.7;
    selection-background-color: {c['accent']}55;
    selection-color: {c['text']};
}}
/* 搜索框 */
QLineEdit#search_box {{
    background-color: {c['card']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 20px;
    padding: 7px 16px 7px 38px;
    font-size: 13px;
}}
QLineEdit#search_box:focus {{
    border-color: {c['accent']};
    background-color: {c['card_hover']};
}}
QLineEdit#search_box::placeholder {{
    color: {c['text2']};
}}
/* 分割线 */
QSplitter::handle {{ background-color: {c['border']}; }}
QSplitter::handle:vertical {{ height: 1px; margin: 1px 0; }}
QSplitter::handle:horizontal {{ width: 1px; }}
/* 通用按钮 */
QPushButton {{
    background-color: {c['card']};
    color: {c['text2']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {c['card_hover']};
    border-color: {c['accent']}88;
    color: {c['text']};
}}
QPushButton:pressed {{
    background-color: {c['border']};
    color: {c['text']};
}}
QPushButton:disabled {{ color: {c['text2']}55; border-color: {c['card']}; background: {c['card']}; }}
/* 执行按钮 */
QPushButton#btn_run {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c['accent']}ee, stop:1 {c['accent']}aa);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 28px;
    letter-spacing: 0.3px;
}}
QPushButton#btn_run:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c['accent']}, stop:1 {c['accent']}cc);
    color: #ffffff;
}}
QPushButton#btn_run:pressed {{
    background: {c['accent']}99;
    color: #ffffff;
}}
QPushButton#btn_run:disabled {{
    background: {c['card']};
    color: {c['text2']};
}}
/* 新建按钮 */
QPushButton#btn_add {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c['accent2']}ee, stop:1 {c['accent2']}aa);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}}
QPushButton#btn_add:hover {{
    background: {c['accent2']};
    color: #ffffff;
}}
/* 删除按钮 */
QPushButton#btn_delete {{
    background-color: transparent;
    color: {c['danger']};
    border: 1px solid {c['danger']}44;
    border-radius: 8px;
}}
QPushButton#btn_delete:hover {{
    background-color: {c['danger']}18;
    border-color: {c['danger']}88;
}}
QPushButton#btn_delete:disabled {{ color: {c['text2']}33; border-color: transparent; }}
/* 编辑按钮 */
QPushButton#btn_edit {{
    background-color: transparent;
    color: {c['text2']};
    border: 1px solid {c['border']};
}}
QPushButton#btn_edit:hover {{
    color: {c['text']};
    border-color: {c['accent']}66;
    background-color: {c['card']};
}}
QPushButton#btn_edit:disabled {{ color: {c['text2']}33; border-color: transparent; }}
/* 主题按钮 */
QPushButton#btn_theme {{
    background-color: transparent;
    color: {c['text2']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 15px;
}}
QPushButton#btn_theme:hover {{
    background-color: {c['card']};
    border-color: {c['accent']}66;
    color: {c['text']};
}}
/* 滚动条 */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 4px; margin: 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border']};
    border-radius: 2px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['accent']}88; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{
    background: transparent; height: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {c['border']}; border-radius: 2px; min-width: 32px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
/* 菜单 */
QMenu {{
    background-color: {c['panel']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    padding: 6px 4px;
    color: {c['text']};
    font-size: 13px;
}}
QMenu::item {{
    padding: 8px 22px 8px 16px;
    border-radius: 6px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background-color: {c['card_hover']};
    color: {c['accent']};
}}
QMenu::separator {{
    height: 1px;
    background: {c['border']};
    margin: 4px 12px;
}}
/* MessageBox */
QMessageBox {{
    background-color: {c['panel']};
    color: {c['text']};
}}
"""

STYLE = build_style(C)

# ══════════════════════════════════════════════
#  颜色/类型工具
# ══════════════════════════════════════════════
SHORTCUT_COLORS = ["#1e6a4a", "#1a5a8a", "#4a3a1a", "#4a1a3a", "#1a4a5a"]
WORKFLOW_COLORS  = ["#4a2aaa", "#6a2a7a", "#2a4aaa", "#6a3a1a", "#1a4a6a"]
SIMPLE_TYPES = {"open_software", "open_path"}
TYPE_BADGE = {
    "p4_sync": "P4", "ue_project": "UE",
    "open_software": "APP", "open_path": "DIR", "run_command": "CMD",
}
TYPE_BADGE_COLOR = {
    "p4_sync": "#f59e0b", "ue_project": "#7c6aff",
    "open_software": "#22c55e", "open_path": "#38bdf8", "run_command": "#f472b6",
}

def _is_shortcut(task):
    a = task.get("actions", [])
    return len(a) == 1 and a[0].get("type", "") in SIMPLE_TYPES

def _task_color(task, idx):
    pool = SHORTCUT_COLORS if _is_shortcut(task) else WORKFLOW_COLORS
    return pool[idx % len(pool)]

# ══════════════════════════════════════════════
#  图标工具
# ══════════════════════════════════════════════
_icon_provider = None

def _get_file_icon(file_path: str, bg_color: str, size: int = 60) -> Optional[QPixmap]:
    global _icon_provider
    if _icon_provider is None:
        _icon_provider = QFileIconProvider()
    if not os.path.exists(file_path):
        return None
    try:
        icon_size = size - 14
        info = QFileInfo(file_path)
        # 先请求大尺寸，再强制缩放，避免小图标留白
        raw = _icon_provider.icon(info).pixmap(QSize(256, 256))
        if raw.isNull():
            return None
        # 强制缩放到 icon_size × icon_size，填满，不保留比例（系统图标通常是方形的）
        raw = raw.scaled(icon_size, icon_size,
                         Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)

        bg = QPixmap(size, size)
        bg.fill(Qt.GlobalColor.transparent)
        p = QPainter(bg)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(bg_color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, size, size, 14, 14)
        ox = (size - raw.width()) // 2
        oy = (size - raw.height()) // 2
        p.drawPixmap(ox, oy, raw)
        p.end()
        return bg
    except Exception:
        return None

def _letter_icon(letter: str, color: str, size: int = 60) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # 渐变背景
    grad = QLinearGradient(0, 0, size, size)
    base = QColor(color)
    light = base.lighter(130)
    grad.setColorAt(0, light)
    grad.setColorAt(1, base)
    p.setBrush(QBrush(grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size, size, 14, 14)
    p.setPen(QPen(QColor("#ffffff")))
    f = QFont("Microsoft YaHei UI", size // 3, QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, letter.upper()[:1])
    p.end()
    return pm

def _task_icon(task: Dict, color: str, size: int = 60) -> QPixmap:
    for a in task.get("actions", []):
        path = (a.get("exe_path") or a.get("uproject_path") or a.get("path") or "").strip()
        if path:
            pm = _get_file_icon(path, color, size)
            if pm:
                return pm
    name = task.get("name", "?")
    return _letter_icon(name[0] if name else "?", color, size)


# ══════════════════════════════════════════════
#  任务卡片
# ══════════════════════════════════════════════
class TaskCard(QWidget):
    clicked = pyqtSignal(str)
    double_clicked = pyqtSignal(str)

    CARD_W, CARD_H = 120, 134

    def __init__(self, task: Dict, color: str, parent=None):
        super().__init__(parent)
        self.task_id = task["id"]
        self.color = color
        self.is_shortcut = _is_shortcut(task)
        self._selected = False
        self._hovered = False
        self._drag_start = QPoint()
        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._build(task)

    def _build(self, task: Dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        name = task.get("name", "?")
        actions = task.get("actions", [])
        first_type = actions[0].get("type", "") if actions else ""

        # 图标
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(60, 60)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setPixmap(_task_icon(task, self.color, 60))

        # 任务名
        self.name_lbl = QLabel(name)
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setStyleSheet(f"color:{C['text']};font-size:11px;background:transparent;")
        self.name_lbl.setMaximumWidth(108)
        self.name_lbl.setMaximumHeight(36)

        # 状态行
        enabled = task.get("enabled", True)
        sched = task.get("schedule")
        parts = []
        if not enabled: parts.append("禁用")
        if sched: parts.append("⏰")
        self.status_lbl = QLabel("  ".join(parts))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.status_lbl.setStyleSheet(f"color:{C['text2']};font-size:10px;background:transparent;")

        layout.addWidget(self.icon_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_lbl)
        layout.addWidget(self.status_lbl)

        # 右上角类型徽标
        self._badge_type = first_type
        self._badge_text = TYPE_BADGE.get(first_type, "")
        self._badge_color = TYPE_BADGE_COLOR.get(first_type, C['text2'])
        self._type_label = "快捷" if self.is_shortcut else "流程"
        self._type_color = C['shortcut'] if self.is_shortcut else C['workflow']

    def update_task(self, task: Dict):
        self.icon_lbl.setPixmap(_task_icon(task, self.color, 60))
        self.name_lbl.setText(task.get("name", "?"))
        enabled = task.get("enabled", True)
        sched = task.get("schedule")
        parts = []
        if not enabled: parts.append("禁用")
        if sched: parts.append("⏰")
        self.status_lbl.setText("  ".join(parts))

    def set_selected(self, v: bool):
        self._selected = v
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = 12

        # 卡片背景
        if self._selected:
            bg = QColor(C['card_hover'])
        elif self._hovered:
            bg = QColor(C['card']).lighter(115)
        else:
            bg = QColor(C['card'])
        p.setBrush(QBrush(bg))

        # 边框
        if self._selected:
            p.setPen(QPen(QColor(C['accent']), 2))
        elif self._hovered:
            p.setPen(QPen(QColor(C['border']).lighter(140), 1))
        else:
            p.setPen(QPen(QColor(C['border']), 1))

        p.drawRoundedRect(1, 1, w-2, h-2, r, r)

        # 选中时底部彩色光条
        if self._selected:
            grad = QLinearGradient(0, h-4, w, h-4)
            grad.setColorAt(0, QColor(C['accent'] + "00"))
            grad.setColorAt(0.5, QColor(C['accent']))
            grad.setColorAt(1, QColor(C['accent'] + "00"))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(8, h-4, w-16, 4, 2, 2)

        # 右上角类型徽标
        if self._badge_text:
            badge_c = QColor(self._badge_color)
            badge_bg = QColor(badge_c)
            badge_bg.setAlpha(40)
            fm_rect = p.fontMetrics().boundingRect(self._badge_text)
            bw = fm_rect.width() + 10
            bh = 16
            bx = w - bw - 6
            by = 6
            p.setBrush(QBrush(badge_bg))
            p.setPen(QPen(badge_c, 1))
            p.drawRoundedRect(bx, by, bw, bh, 4, 4)
            p.setPen(QPen(badge_c))
            f = QFont("Microsoft YaHei UI", 8, QFont.Weight.Bold)
            p.setFont(f)
            p.drawText(bx, by, bw, bh, Qt.AlignmentFlag.AlignCenter, self._badge_text)

        p.end()

    def enterEvent(self, e):
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.position().toPoint()
            self.clicked.emit(self.task_id)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        if (e.position().toPoint() - self._drag_start).manhattanLength() < 12:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"task_drag:{self.task_id}")
        drag.setMimeData(mime)
        # 半透明拖拽预览
        pm = self.grab()
        drag.setPixmap(pm)
        drag.setHotSpot(self._drag_start)
        drag.exec(Qt.DropAction.MoveAction)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.task_id)


# ══════════════════════════════════════════════
#  主窗口
# ══════════════════════════════════════════════
class MainWindow(QMainWindow):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.tasks: List[Dict] = load_tasks()
        self.groups: List[Dict] = load_groups()
        self.settings = load_settings()
        self.selected_task_id: Optional[str] = None
        self._cards: Dict[str, TaskCard] = {}
        self._search_text = ""
        # 记录每个分类的 grid layout，供拖拽使用
        self._group_grids: Dict[str, QGridLayout] = {}
        self._group_grid_ws: Dict[str, QWidget] = {}

        # 加载主题
        saved_theme = self.settings.get("theme", "nebula")
        set_theme(saved_theme)

        self.executor = TaskExecutor(log_callback=lambda m: self.log_signal.emit(m))
        self.scheduler = TaskScheduler(run_task_callback=self._on_scheduled)
        self.log_signal.connect(self._append_log)

        self._init_ui()
        self._init_tray()
        self._refresh_grid()
        self.scheduler.reload_all(self.tasks)

        if self.tasks:
            self._select(self.tasks[0]["id"])

    # ── UI 初始化 ──
    def _init_ui(self):
        self.setWindowTitle("AutoTasker")
        self.setMinimumSize(860, 580)
        self.resize(1080, 700)
        self.setStyleSheet(STYLE)
        self.setAcceptDrops(True)
        # 设置窗口图标（标题栏 + 任务栏）
        self.setWindowIcon(_make_logo_icon(256))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ═══ Header ═══
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background-color:{C['panel']};border-bottom:1px solid {C['border']};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)
        hl.setSpacing(16)

        # Logo
        logo = QLabel()
        logo_icon = _make_logo_icon(32)
        logo.setPixmap(logo_icon.pixmap(QSize(32, 32)))
        logo.setFixedSize(36, 36)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("background:transparent;")
        title = QLabel("AutoTasker")
        title.setStyleSheet(f"font-size:17px;font-weight:bold;color:{C['text']};background:transparent;letter-spacing:0.5px;")

        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setObjectName("search_box")
        self.search_box.setPlaceholderText("🔍  搜索任务...")
        self.search_box.setFixedWidth(240)
        self.search_box.setFixedHeight(34)
        self.search_box.textChanged.connect(self._on_search)

        # 状态
        self.status_lbl = QLabel("就绪")
        self.status_lbl.setStyleSheet(f"color:{C['text2']};font-size:12px;background:transparent;")

        # 主题切换按钮
        self.btn_theme = QPushButton("🎨")
        self.btn_theme.setObjectName("btn_theme")
        self.btn_theme.setFixedSize(36, 34)
        self.btn_theme.setToolTip("切换主题")
        self.btn_theme.clicked.connect(self._show_theme_menu)

        hl.addWidget(logo)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(self.search_box)
        hl.addStretch()
        hl.addWidget(self.status_lbl)
        hl.addWidget(self.btn_theme)
        root.addWidget(header)

        # ═══ 主体 ═══
        body = QWidget()
        body.setStyleSheet(f"background-color:{C['bg']};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.setSpacing(14)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(1)

        # ── 上：任务网格区 ──
        top = QWidget()
        top.setStyleSheet("background:transparent;")
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(10)

        # 工具栏
        tb = QHBoxLayout()
        sec_label = QLabel("我的任务")
        sec_label.setStyleSheet(f"font-size:14px;font-weight:bold;color:{C['text']};background:transparent;")

        self.btn_add = QPushButton("＋  新建")
        self.btn_add.setObjectName("btn_add")
        self.btn_add.setFixedHeight(34)
        self.btn_add.clicked.connect(self._new_task)

        tb.addWidget(sec_label)
        tb.addStretch()
        tb.addWidget(self.btn_add)

        # 分类管理按钮
        self.btn_manage_groups = QPushButton("⚙  分类")
        self.btn_manage_groups.setObjectName("btn_edit")
        self.btn_manage_groups.setFixedHeight(34)
        self.btn_manage_groups.clicked.connect(self._manage_groups)
        tb.addWidget(self.btn_manage_groups)
        tl.addLayout(tb)

        # 整个任务区用一个滚动区包裹（分类由 _refresh_grid 动态生成）
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(160)
        self.scroll.setStyleSheet("background:transparent;border:none;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background:transparent;")
        self.scroll_vl = QVBoxLayout(self.scroll_content)
        self.scroll_vl.setContentsMargins(0, 4, 0, 8)
        self.scroll_vl.setSpacing(0)
        self.scroll_vl.addStretch()
        self.scroll.setWidget(self.scroll_content)
        tl.addWidget(self.scroll)
        splitter.addWidget(top)

        # ── 下：操作栏 + 可折叠日志 ──
        bot = QWidget()
        bot.setStyleSheet("background:transparent;")
        bot_l = QVBoxLayout(bot)
        bot_l.setContentsMargins(0, 0, 0, 0)
        bot_l.setSpacing(6)

        # ── 单行操作栏：任务名 + 全部按钮 ──
        self.detail_panel = QFrame()
        self.detail_panel.setStyleSheet(
            f"background-color:{C['panel']};border:1px solid {C['border']};border-radius:12px;")
        self.detail_panel.setFixedHeight(54)
        dp = QHBoxLayout(self.detail_panel)
        dp.setContentsMargins(16, 0, 12, 0)
        dp.setSpacing(10)

        # 任务名 + 步骤描述（单行，用 · 分隔）
        self.detail_name = QLabel("← 选择一个任务开始")
        self.detail_name.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{C['text']};background:transparent;")
        self.detail_steps = QLabel("")
        self.detail_steps.setStyleSheet(
            f"font-size:11px;color:{C['text2']};background:transparent;")
        self.detail_steps.setWordWrap(False)

        dp.addWidget(self.detail_name)
        dp.addWidget(self.detail_steps, stretch=1)

        # 分隔竖线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"background:{C['border']};max-width:1px;margin:10px 0;")
        dp.addWidget(sep)

        # 按钮：执行 | 编辑 | 删除 | 日志
        self.btn_run = QPushButton("▶  执行")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setFixedHeight(34)
        self.btn_run.setMinimumWidth(80)
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run_task)

        self.btn_edit2 = QPushButton("✏  编辑")
        self.btn_edit2.setObjectName("btn_edit")
        self.btn_edit2.setFixedHeight(34)
        self.btn_edit2.setMinimumWidth(72)
        self.btn_edit2.setEnabled(False)
        self.btn_edit2.clicked.connect(self._edit_task)

        self.btn_del2 = QPushButton("删除")
        self.btn_del2.setObjectName("btn_delete")
        self.btn_del2.setFixedHeight(34)
        self.btn_del2.setMinimumWidth(60)
        self.btn_del2.setEnabled(False)
        self.btn_del2.clicked.connect(self._delete_task)

        # 日志展开/折叠按钮
        self._log_visible = False
        self.btn_log_toggle = QPushButton("📋  日志")
        self.btn_log_toggle.setObjectName("btn_edit")
        self.btn_log_toggle.setFixedHeight(34)
        self.btn_log_toggle.setMinimumWidth(72)
        self.btn_log_toggle.setCheckable(True)
        self.btn_log_toggle.setChecked(False)
        self.btn_log_toggle.clicked.connect(self._toggle_log)

        dp.addWidget(self.btn_run)
        dp.addWidget(self.btn_edit2)
        dp.addWidget(self.btn_del2)
        dp.addWidget(self.btn_log_toggle)
        bot_l.addWidget(self.detail_panel)

        # ── 日志区（默认隐藏）──
        self.log_container = QWidget()
        self.log_container.setStyleSheet("background:transparent;")
        log_vl = QVBoxLayout(self.log_container)
        log_vl.setContentsMargins(0, 0, 0, 0)
        log_vl.setSpacing(4)

        log_bar = QHBoxLayout()
        log_title = QLabel("执行日志")
        log_title.setStyleSheet(
            f"font-size:12px;font-weight:bold;color:{C['text2']};background:transparent;")
        self.btn_clear = QPushButton("清空")
        self.btn_clear.setFixedSize(48, 24)
        self.btn_clear.setStyleSheet(
            f"font-size:11px;padding:0;background:{C['card']};border:1px solid {C['border']};"
            f"border-radius:5px;color:{C['text2']};")
        self.btn_clear.clicked.connect(lambda: self.log_view.clear())
        log_bar.addWidget(log_title)
        log_bar.addStretch()
        log_bar.addWidget(self.btn_clear)
        log_vl.addLayout(log_bar)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("log_view")
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(160)
        self.log_view.setPlaceholderText("任务执行日志将在这里显示...")
        log_vl.addWidget(self.log_view)

        self.log_container.setVisible(False)
        bot_l.addWidget(self.log_container)

        splitter.addWidget(bot)
        splitter.setSizes([9999, 1])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        bl.addWidget(splitter)
        root.addWidget(body)

    def _init_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(_make_logo_icon(32))
        self.tray.setToolTip("AutoTasker")
        m = QMenu()
        m.addAction(QAction("显示", self, triggered=self.show_window))
        m.addSeparator()
        m.addAction(QAction("退出", self, triggered=self._quit))
        self.tray.setContextMenu(m)
        self.tray.activated.connect(
            lambda r: self.show_window() if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()


    # ── 网格刷新（动态分类）──
    def _refresh_grid(self):
        # 清空 scroll_content（保留最后一个 stretch）
        while self.scroll_vl.count() > 1:
            item = self.scroll_vl.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._cards.clear()
        self._group_grids.clear()
        self._group_grid_ws.clear()

        cols = max(1, (self.scroll.width() - 24) // (TaskCard.CARD_W + 10))
        filtered = [t for t in self.tasks
                    if self._search_text.lower() in t.get("name", "").lower()]

        sorted_groups = sorted(self.groups, key=lambda g: g.get("order", 99))
        all_idx = 0
        prev_had_tasks = False

        for group in sorted_groups:
            gid = group["id"]
            group_tasks = [t for t in filtered if t.get("group_id", "default") == gid]

            # 搜索时隐藏空分类
            if self._search_text and not group_tasks:
                continue

            # 分隔线（第一个分类之后才加）
            if prev_had_tasks or (not self._search_text and sorted_groups.index(group) > 0):
                div = QFrame()
                div.setFrameShape(QFrame.Shape.HLine)
                div.setStyleSheet(
                    f"background-color:{C['border']};max-height:1px;margin:6px 0;border:none;")
                self.scroll_vl.insertWidget(self.scroll_vl.count() - 1, div)

            # 分类 section widget
            section = QWidget()
            section.setStyleSheet("background:transparent;")
            sec_l = QVBoxLayout(section)
            sec_l.setContentsMargins(0, 0, 0, 0)
            sec_l.setSpacing(4)

            # 分类标题行
            hdr = QHBoxLayout()
            is_first = (group.get("order", 99) == 0)
            lbl_color = C['accent'] if is_first else C['text2']
            lbl = QLabel(f"{group.get('emoji','📁')}  {group.get('name','分类')}")
            lbl.setStyleSheet(
                f"font-size:12px;font-weight:bold;color:{lbl_color};background:transparent;")
            cnt = QLabel(f"{len(group_tasks)} 个")
            cnt.setStyleSheet(f"font-size:11px;color:{C['text2']};background:transparent;")
            hdr.addWidget(lbl)
            hdr.addWidget(cnt)
            hdr.addStretch()
            sec_l.addLayout(hdr)

            # 卡片网格
            grid_w = QWidget()
            grid_w.setAcceptDrops(True)
            grid_w.dragEnterEvent = self._drag_enter
            grid_w.dragMoveEvent  = self._drag_move
            _gid = gid  # 闭包捕获
            grid_w.dropEvent = lambda e, g=_gid: self._drop(e, group_id=g)
            grid_l = QGridLayout(grid_w)
            grid_l.setContentsMargins(0, 2, 0, 4)
            grid_l.setSpacing(10)
            grid_l.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            if group_tasks:
                grid_w.setStyleSheet("background:transparent;")
                for i, task in enumerate(group_tasks):
                    color = _task_color(task, all_idx); all_idx += 1
                    card = self._make_card(task, color)
                    r, c = divmod(i, cols)
                    grid_l.addWidget(card, r, c)
            else:
                # 空分类：虚线占位区，保证可接收拖拽
                grid_w.setMinimumHeight(72)
                grid_w.setStyleSheet(
                    f"background:transparent;"
                    f"border:2px dashed {C['border']};"
                    f"border-radius:10px;"
                )
                hint_lbl = QLabel("将任务拖到此处")
                hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                hint_lbl.setStyleSheet(
                    f"color:{C['text2']};font-size:12px;background:transparent;border:none;")
                grid_l.addWidget(hint_lbl, 0, 0)

            self._group_grids[gid] = grid_l
            self._group_grid_ws[gid] = grid_w
            sec_l.addWidget(grid_w)
            self.scroll_vl.insertWidget(self.scroll_vl.count() - 1, section)
            prev_had_tasks = bool(group_tasks)

        # 恢复选中
        if self.selected_task_id and self.selected_task_id in self._cards:
            self._cards[self.selected_task_id].set_selected(True)

    def _make_card(self, task: Dict, color: str) -> "TaskCard":
        card = TaskCard(task, color)
        card.clicked.connect(self._select)
        card.double_clicked.connect(self._on_dbl)
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, t=task: self._card_context_menu(t, card.mapToGlobal(pos)))
        self._cards[task["id"]] = card
        return card

    def _card_context_menu(self, task: Dict, global_pos):
        menu = QMenu(self)

        # 移动到分类子菜单
        move_menu = menu.addMenu("📂  移动到分类")
        current_gid = task.get("group_id", "default")
        for g in sorted(self.groups, key=lambda x: x.get("order", 99)):
            act = move_menu.addAction(f"{g.get('emoji','📁')}  {g['name']}")
            if g["id"] == current_gid:
                act.setEnabled(False)  # 当前分类置灰
            act.setData(g["id"])

        menu.addSeparator()
        act_run   = menu.addAction("▶  立即执行")
        act_admin = menu.addAction("🛡  以管理员身份运行")
        act_edit  = menu.addAction("✏  编辑")
        menu.addSeparator()
        act_del   = menu.addAction("🗑  删除")

        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen.parent() is move_menu:
            new_gid = chosen.data()
            if new_gid and new_gid != current_gid:
                task["group_id"] = new_gid
                # 同步兼容 pinned 字段
                task["pinned"] = (new_gid == "pinned")
                save_tasks(self.tasks)
                self._refresh_grid()
        elif chosen == act_run:
            self._select(task["id"])
            self._run_task()
        elif chosen == act_admin:
            self._select(task["id"])
            self._run_task_as_admin(task)
        elif chosen == act_edit:
            self._select(task["id"])
            self._edit_task()
        elif chosen == act_del:
            self._select(task["id"])
            self._delete_task()

    def _manage_groups(self):
        """分类管理对话框"""
        dlg = GroupManagerDialog(self.groups, parent=self)
        if dlg.exec():
            self.groups = dlg.get_groups()
            save_groups(self.groups)
            # 确保所有任务的 group_id 合法
            valid_ids = {g["id"] for g in self.groups}
            default_gid = self.groups[-1]["id"] if self.groups else "default"
            for t in self.tasks:
                if t.get("group_id", "default") not in valid_ids:
                    t["group_id"] = default_gid
            save_tasks(self.tasks)
            self._refresh_grid()

    def _on_search(self, text: str):
        self._search_text = text
        self._refresh_grid()

    # ── 拖拽排序 ──
    def _drag_enter(self, e):
        if e.mimeData().hasText() and e.mimeData().text().startswith("task_drag:"):
            e.acceptProposedAction()
        else:
            e.ignore()

    def _drag_move(self, e):
        if e.mimeData().hasText() and e.mimeData().text().startswith("task_drag:"):
            e.acceptProposedAction()
        else:
            e.ignore()

    def _drop(self, e, group_id: str = "default"):
        text = e.mimeData().text()
        if not text.startswith("task_drag:"):
            e.ignore()
            return
        drag_id = text.split(":", 1)[1]
        drag_task = self._get(drag_id)
        if not drag_task:
            e.acceptProposedAction()
            return

        # 跨分类拖拽
        if drag_task.get("group_id", "default") != group_id:
            drag_task["group_id"] = group_id
            drag_task["pinned"] = (group_id == "pinned")
            save_tasks(self.tasks)
            self._refresh_grid()
            self._select(drag_id)
            e.acceptProposedAction()
            return

        # 同分区内排序
        grid_w = self._group_grid_ws.get(group_id)
        if not grid_w:
            e.acceptProposedAction()
            return
        pos = e.position().toPoint()
        target_id = None
        for tid, card in self._cards.items():
            t = self._get(tid)
            if not t or t.get("group_id", "default") != group_id:
                continue
            cp = card.mapTo(grid_w, QPoint(0, 0))
            if (cp.x() <= pos.x() <= cp.x() + card.width() and
                    cp.y() <= pos.y() <= cp.y() + card.height()):
                target_id = tid
                break

        if target_id and target_id != drag_id:
            di = next((i for i, t in enumerate(self.tasks) if t["id"] == drag_id), None)
            ti = next((i for i, t in enumerate(self.tasks) if t["id"] == target_id), None)
            if di is not None and ti is not None:
                task = self.tasks.pop(di)
                self.tasks.insert(ti, task)
                save_tasks(self.tasks)
                self._refresh_grid()
                self._select(drag_id)
        e.acceptProposedAction()

    def _show_theme_menu(self):
        menu = QMenu(self)
        for key, theme in THEMES.items():
            action = menu.addAction(f"{theme['emoji']}  {theme['name']}")
            action.setData(key)
            if key == _current_theme_key:
                action.setText(f"{theme['emoji']}  {theme['name']}  ✓")
        chosen = menu.exec(self.btn_theme.mapToGlobal(
            QPoint(0, self.btn_theme.height() + 4)))
        if chosen and chosen.data():
            self._apply_theme(chosen.data())

    def _apply_theme(self, theme_key: str):
        set_theme(theme_key)
        # 保存设置
        self.settings["theme"] = theme_key
        save_settings(self.settings)
        # 重新应用样式
        new_style = build_style(C)
        self.setStyleSheet(new_style)
        # 更新 header 背景
        self._refresh_header_style()
        # 刷新详情面板和日志
        self._refresh_panel_styles()
        # 刷新卡片网格（颜色可能变化）
        self._refresh_grid()

    def _refresh_header_style(self):
        """更新 header 等固定样式组件"""
        # header 背景
        for child in self.findChildren(QWidget):
            if hasattr(child, 'objectName'):
                pass  # Qt 的 setStyleSheet 已经级联更新了
        # 单独更新 status_lbl 颜色
        self.status_lbl.setStyleSheet(
            f"color:{C['text2']};font-size:12px;background:transparent;")

    def _refresh_panel_styles(self):
        """更新详情面板等动态颜色组件"""
        self.detail_panel.setStyleSheet(
            f"background-color:{C['panel']};border:1px solid {C['border']};border-radius:12px;")
        self.detail_name.setStyleSheet(
            f"font-size:15px;font-weight:bold;color:{C['text']};background:transparent;")
        self.detail_steps.setStyleSheet(
            f"font-size:11px;color:{C['text2']};background:transparent;")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(50, self._refresh_grid)

    # ── 主窗口文件拖放 ──
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.isLocalFile() for u in e.mimeData().urls()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            if url.isLocalFile():
                self._create_from_file(url.toLocalFile())
        e.acceptProposedAction()

    def _create_from_file(self, file_path: str):
        from pathlib import Path
        p = Path(file_path)
        suffix = p.suffix.lower()
        if suffix == ".uproject":
            atype, name = "ue_project", p.stem
        elif suffix in (".exe", ".bat", ".cmd", ".lnk"):
            atype, name = "open_software", p.stem
        elif p.is_dir():
            atype, name = "open_path", p.name
        else:
            atype, name = "open_path", p.stem

        task = new_task(name)
        action = new_action(atype)
        action["label"] = name
        if atype == "open_software": action["exe_path"] = file_path
        elif atype == "ue_project":  action["uproject_path"] = file_path
        elif atype == "open_path":   action["path"] = file_path
        task["actions"] = [action]

        self.tasks.append(task)
        save_tasks(self.tasks)
        self.scheduler.reload_all(self.tasks)
        self._refresh_grid()
        self._select(task["id"])
        self._append_log(f"ℹ️  已创建任务: {name}  ({atype})")

    # ── 选中 & 详情 ──
    def _select(self, tid: str):
        if self.selected_task_id and self.selected_task_id in self._cards:
            self._cards[self.selected_task_id].set_selected(False)
        self.selected_task_id = tid
        if tid in self._cards:
            self._cards[tid].set_selected(True)
        self._update_detail(self._get(tid))

    def _on_dbl(self, tid: str):
        self._select(tid)
        self._run_task()

    def _toggle_log(self, checked: bool):
        """展开 / 折叠日志区"""
        self._log_visible = checked
        self.log_container.setVisible(checked)
        self.btn_log_toggle.setText("📋  日志 ▲" if checked else "📋  日志")

    def _update_detail(self, task: Optional[Dict]):
        has = task is not None
        self.btn_run.setEnabled(has)
        self.btn_edit2.setEnabled(has)
        self.btn_del2.setEnabled(has)
        if not task:
            self.detail_name.setText("← 选择一个任务")
            self.detail_steps.setText("")
            return

        suffix = "" if task.get("enabled", True) else "  · 已禁用"
        self.detail_name.setText(task.get("name", "") + suffix)

        type_map = {"open_software":"启动程序","open_path":"打开路径",
                    "run_command":"执行命令","p4_sync":"P4同步","ue_project":"UE项目"}
        actions = task.get("actions", [])
        if actions:
            steps = [type_map.get(a.get("type",""), a.get("type","")) +
                     (f" · {a['label']}" if a.get("label") else "")
                     for a in actions]
            txt = "  →  ".join(steps)
        else:
            txt = "暂未配置操作"

        sched = task.get("schedule")
        if sched:
            nr = self.scheduler.get_next_run(task["id"])
            txt += f"   ·   ⏰ {('下次 '+nr) if nr else '已定时'}"
        lr = task.get("last_run", "")
        if lr:
            result = task.get("last_result", "")
            dot = "🟢" if result == "成功" else "🟡"
            txt += f"   ·   {dot} 上次 {lr}"
        self.detail_steps.setText(txt)

    # ── 任务操作 ──
    def _new_task(self):
        task = new_task("新任务")
        dlg = TaskEditorDialog(task, parent=self, is_new=True)
        if dlg.exec():
            self.tasks.append(task)
            save_tasks(self.tasks)
            self.scheduler.reload_all(self.tasks)
            self._refresh_grid()
            self._select(task["id"])

    def _edit_task(self):
        task = self._get(self.selected_task_id)
        if not task: return
        tc = copy.deepcopy(task)
        dlg = TaskEditorDialog(tc, parent=self, is_new=False)
        if dlg.exec():
            idx = next((i for i, t in enumerate(self.tasks) if t["id"] == task["id"]), None)
            if idx is not None:
                self.tasks[idx] = tc
            save_tasks(self.tasks)
            self.scheduler.reload_all(self.tasks)
            self._refresh_grid()
            self._select(tc["id"])

    def _delete_task(self):
        task = self._get(self.selected_task_id)
        if not task: return
        if QMessageBox.question(self, "确认删除", f"确定删除「{task.get('name')}」？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes:
            self.tasks = [t for t in self.tasks if t["id"] != task["id"]]
            save_tasks(self.tasks)
            self.scheduler.reload_all(self.tasks)
            self.selected_task_id = None
            self._refresh_grid()
            self._update_detail(None)

    def _run_task(self):
        task = self._get(self.selected_task_id)
        if not task: return
        self.btn_run.setEnabled(False)
        self.btn_run.setText("执行中...")
        self.status_lbl.setText(f"⚙  {task.get('name')}")

        def done(ok, msg):
            task["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task["last_result"] = "成功" if ok else "有失败步骤"
            save_tasks(self.tasks)
            QTimer.singleShot(0, self._run_done)

        self.executor.execute_task(task, on_done=done, async_run=True)

    def _run_task_as_admin(self, task: Optional[Dict] = None):
        """以管理员身份运行选中任务（仅对 open_software / open_path / run_command 生效）"""
        if task is None:
            task = self._get(self.selected_task_id)
        if not task:
            return
        self.btn_run.setEnabled(False)
        self.btn_run.setText("执行中...")
        self.status_lbl.setText(f"🛡  {task.get('name')}")

        def done(ok, msg):
            task["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task["last_result"] = "成功" if ok else "有失败步骤"
            save_tasks(self.tasks)
            QTimer.singleShot(0, self._run_done)

        self.executor.execute_task(task, on_done=done, async_run=True, as_admin=True)

    def _run_done(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("▶  立即执行")
        self.status_lbl.setText("就绪")
        task = self._get(self.selected_task_id)
        self._update_detail(task)
        if task and task["id"] in self._cards:
            self._cards[task["id"]].update_task(task)

    def _on_scheduled(self, task):
        self.log_signal.emit(f"ℹ️  定时触发: {task.get('name')}")
        self.executor.execute_task(task, async_run=True)

    # ── 日志（多色） ──
    def _append_log(self, msg: str):
        # 任务开始时自动展开日志
        if not self._log_visible and ("▶" in msg or "开始执行" in msg):
            self._log_visible = True
            self.log_container.setVisible(True)
            self.btn_log_toggle.setChecked(True)
            self.btn_log_toggle.setText("📋  日志 ▲")

        # 根据内容着色
        if "✅" in msg or "成功" in msg or "完成" in msg:
            color = "#22c55e"
        elif "❌" in msg or "失败" in msg or "错误" in msg or "error" in msg.lower():
            color = "#ef4444"
        elif "⚠️" in msg or "警告" in msg:
            color = "#f59e0b"
        elif "▶" in msg or "开始执行" in msg:
            color = "#7c6aff"
        elif "ℹ️" in msg or "步骤" in msg or "→" in msg:
            color = "#38bdf8"
        elif "═" in msg or "━" in msg or "─" in msg:
            color = "#383860"
        else:
            color = "#8888aa"

        import html
        safe = html.escape(msg)
        self.log_view.append(f'<span style="color:{color};">{safe}</span>')

        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

        max_lines = self.settings.get("log_max_lines", 500)
        doc = self.log_view.document()
        while doc.blockCount() > max_lines:
            cur = self.log_view.textCursor()
            cur.movePosition(cur.MoveOperation.Start)
            cur.select(cur.SelectionType.BlockUnderCursor)
            cur.removeSelectedText()
            cur.deleteChar()

    # ── 托盘/关闭 ──
    def show_window(self):
        self.show(); self.raise_(); self.activateWindow()

    def _quit(self):
        self.scheduler.shutdown()
        QApplication.quit()

    def closeEvent(self, e):
        if self.settings.get("minimize_to_tray", True):
            e.ignore(); self.hide()
            self.tray.showMessage("AutoTasker", "已最小化到托盘，双击重新打开。",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            self.scheduler.shutdown(); e.accept()

    def _get(self, tid: Optional[str]) -> Optional[Dict]:
        if not tid: return None
        return next((t for t in self.tasks if t["id"] == tid), None)


# ══════════════════════════════════════════════
#  分类管理对话框
# ══════════════════════════════════════════════
EMOJI_OPTIONS = ["⭐", "📋", "🎨", "🛠", "🎮", "📁", "🚀", "🔧", "💡", "📦",
                 "🌐", "🎬", "📷", "🖥", "🔥", "⚡", "🎯", "💻", "🗂", "📌"]

class GroupManagerDialog(QDialog):
    """分类管理：增加/删除/重命名/调整顺序"""

    def __init__(self, groups: List[Dict], parent=None):
        super().__init__(parent)
        import copy
        self._groups = copy.deepcopy(groups)
        self.setWindowTitle("管理分类")
        self.setMinimumSize(420, 380)
        self.setModal(True)
        if parent:
            self.setStyleSheet(parent.styleSheet())
        self._build()

    def _build(self):
        c = C
        self.setStyleSheet(f"""
            QDialog {{ background:{c['bg']}; color:{c['text']}; }}
            QListWidget {{ background:{c['card']}; border:1px solid {c['border']};
                border-radius:8px; color:{c['text']}; font-size:13px; outline:none; }}
            QListWidget::item {{ padding:8px 12px; border-radius:6px; margin:1px 4px; }}
            QListWidget::item:selected {{ background:{c['card_hover']}; color:{c['accent']}; }}
            QPushButton {{ background:{c['card']}; color:{c['text2']}; border:1px solid {c['border']};
                border-radius:7px; padding:6px 14px; font-size:12px; }}
            QPushButton:hover {{ background:{c['card_hover']}; color:{c['text']}; border-color:{c['accent']}66; }}
            QPushButton#btn_add {{ background:{c['accent2']}cc; color:#fff; border:none; font-weight:600; }}
            QPushButton#btn_add:hover {{ background:{c['accent2']}; color:#fff; }}
            QPushButton#btn_del {{ background:{c['danger']}22; color:{c['danger']}; border:1px solid {c['danger']}44; }}
            QPushButton#btn_del:hover {{ background:{c['danger']}33; border-color:{c['danger']}88; }}
            QLabel {{ color:{c['text']}; background:transparent; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        hint = QLabel("拖拽列表项可调整排序 · 双击重命名")
        hint.setStyleSheet(f"color:{c['text2']};font-size:11px;")
        layout.addWidget(hint)

        self.list_w = QListWidget()
        self.list_w.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_w.itemDoubleClicked.connect(self._rename_item)
        layout.addWidget(self.list_w)
        self._reload_list()

        # 按钮行
        btn_row = QHBoxLayout()
        btn_add = QPushButton("＋  新增分类")
        btn_add.setObjectName("btn_add")
        btn_add.clicked.connect(self._add_group)

        btn_rename = QPushButton("✏  重命名")
        btn_rename.clicked.connect(self._rename_selected)

        btn_emoji = QPushButton("😀  图标")
        btn_emoji.clicked.connect(self._change_emoji)

        btn_del = QPushButton("🗑  删除")
        btn_del.setObjectName("btn_del")
        btn_del.clicked.connect(self._del_group)

        btn_row.addWidget(btn_add)
        btn_row.addStretch()
        btn_row.addWidget(btn_rename)
        btn_row.addWidget(btn_emoji)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)

        # OK / Cancel
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.setStyleSheet(f"""
            QPushButton {{ background:{c['card']}; color:{c['text']}; border:1px solid {c['border']};
                border-radius:7px; padding:6px 18px; }}
            QPushButton:hover {{ background:{c['card_hover']}; border-color:{c['accent']}66; }}
            QPushButton[text="OK"], QPushButton[text="确定"] {{
                background:{c['accent']}cc; color:#fff; border:none; font-weight:600; }}
        """)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _reload_list(self):
        self.list_w.clear()
        for g in self._groups:
            item = QListWidgetItem(f"{g.get('emoji','📁')}  {g['name']}")
            item.setData(Qt.ItemDataRole.UserRole, g["id"])
            self.list_w.addItem(item)

    def _add_group(self):
        name, ok = QInputDialog.getText(self, "新增分类", "分类名称:")
        if ok and name.strip():
            g = new_group(name.strip(), "📁", len(self._groups))
            self._groups.append(g)
            self._reload_list()

    def _rename_item(self, item: QListWidgetItem):
        gid = item.data(Qt.ItemDataRole.UserRole)
        g = next((x for x in self._groups if x["id"] == gid), None)
        if not g:
            return
        name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=g["name"])
        if ok and name.strip():
            g["name"] = name.strip()
            self._reload_list()

    def _rename_selected(self):
        item = self.list_w.currentItem()
        if item:
            self._rename_item(item)

    def _change_emoji(self):
        item = self.list_w.currentItem()
        if not item:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        g = next((x for x in self._groups if x["id"] == gid), None)
        if not g:
            return
        emoji, ok = QInputDialog.getItem(
            self, "选择图标", "选择分类图标:",
            EMOJI_OPTIONS, EMOJI_OPTIONS.index(g.get("emoji","📁")) if g.get("emoji","📁") in EMOJI_OPTIONS else 5,
            False
        )
        if ok:
            g["emoji"] = emoji
            self._reload_list()

    def _del_group(self):
        item = self.list_w.currentItem()
        if not item:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        if len(self._groups) <= 1:
            QMessageBox.warning(self, "无法删除", "至少保留一个分类")
            return
        g = next((x for x in self._groups if x["id"] == gid), None)
        if not g:
            return
        ret = QMessageBox.question(
            self, "删除分类",
            f"确定删除「{g['name']}」？\n该分类中的任务将移入最后一个分类。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._groups = [x for x in self._groups if x["id"] != gid]
            self._reload_list()

    def _on_ok(self):
        # 按照列表当前顺序重新排序
        order_map = {}
        for i in range(self.list_w.count()):
            item = self.list_w.item(i)
            gid = item.data(Qt.ItemDataRole.UserRole)
            order_map[gid] = i
        for g in self._groups:
            g["order"] = order_map.get(g["id"], 99)
        self._groups.sort(key=lambda x: x["order"])
        self.accept()

    def get_groups(self) -> List[Dict]:
        return self._groups

