"""
任务编辑对话框 - 重设计版
布局：自定义标题栏 + 上方基本信息 + 中间左右分栏（步骤列表 | 步骤配置）+ 下方定时/保存
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox,
    QComboBox, QWidget, QFrame, QFileDialog, QSpinBox,
    QMessageBox, QScrollArea, QStackedWidget, QSizePolicy,
    QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QColor, QFont

from config_manager import new_action
from scheduler import SCHEDULE_PRESETS
import i18n

# ──────────────────────────────────────────
#  从主窗口引入主题（运行时动态获取）
# ──────────────────────────────────────────
def _C():
    """延迟获取当前主题颜色字典，避免循环导入"""
    try:
        from main_window import C
        return C
    except Exception:
        return {
            "bg": "#111318", "panel": "#1c1e26", "card": "#22252f",
            "card_hover": "#2a2e3a", "border": "#32374a",
            "accent": "#6d8ff5", "accent2": "#56c9a0",
            "danger": "#e05c6e", "warn": "#e8a644",
            "text": "#d4d8f0", "text2": "#5c6485",
        }

def _build_editor_style() -> str:
    c = _C()
    return f"""
QDialog, QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
    border: none;
}}
QLabel {{ color: {c['text2']}; background: transparent; }}
QLineEdit, QTextEdit, QSpinBox {{
    background-color: {c['card']};
    color: {c['text']};
    border: none;
    border-radius: 6px;
    padding: 5px 9px;
    selection-background-color: {c['accent']}44;
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
    background-color: {c['card_hover']};
}}
QComboBox {{
    background-color: {c['card']};
    color: {c['text']};
    border: none;
    border-radius: 6px;
    padding: 5px 9px;
}}
QComboBox:focus {{ background-color: {c['card_hover']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {c['panel']};
    color: {c['text']};
    border: none;
    selection-background-color: {c['card_hover']};
    outline: none;
}}
QCheckBox {{ color: {c['text']}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1.5px solid {c['border']};
    border-radius: 4px;
    background: {c['card']};
}}
QCheckBox::indicator:checked {{
    background: {c['accent']};
    border-color: {c['accent']};
}}
QPushButton {{
    background-color: {c['card']};
    color: {c['text']};
    border: none;
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 13px;
}}
QPushButton:hover {{ background-color: {c['card_hover']}; }}
QPushButton:pressed {{ background-color: {c['border']}; }}
QPushButton#btn_save {{
    background-color: {c['accent']};
    color: #ffffff;
    font-weight: 600;
    padding: 7px 24px;
}}
QPushButton#btn_save:hover {{ background-color: {c['accent']}cc; }}
QPushButton#btn_add_step {{
    background-color: {c['accent2']}22;
    color: {c['accent2']};
    font-weight: 600;
}}
QPushButton#btn_add_step:hover {{ background-color: {c['accent2']}38; }}
QPushButton#btn_del_step {{
    background-color: transparent;
    color: {c['danger']};
    padding: 4px 10px;
}}
QPushButton#btn_del_step:hover {{ background-color: {c['danger']}18; }}
QPushButton#btn_win_close {{
    background: transparent;
    color: {c['text2']};
    border: none;
    border-radius: 6px;
    font-size: 13px;
    padding: 0;
}}
QPushButton#btn_win_close:hover {{
    background: {c['danger']};
    color: #ffffff;
}}
QListWidget {{
    background-color: {c['card']};
    border: none;
    border-radius: 8px;
    outline: none;
}}
QListWidget::item {{
    padding: 9px 12px;
    border-radius: 6px;
    margin: 1px 4px;
    color: {c['text']};
}}
QListWidget::item:selected {{
    background-color: {c['accent']}22;
    color: {c['accent']};
}}
QListWidget::item:hover:!selected {{ background-color: {c['card_hover']}; }}
QFrame#config_panel {{
    background-color: {c['panel']};
    border-radius: 10px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 3px; margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {c['border']}; border-radius: 2px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

def _tr(key: str, **kwargs) -> str:
    return i18n.t(key, **kwargs)


def _action_type_options():
    return [
        (_tr("action_p4_sync"), "p4_sync"),
        (_tr("action_ue_project"), "ue_project"),
        (_tr("action_open_software"), "open_software"),
        (_tr("action_open_path"), "open_path"),
        (_tr("action_run_command"), "run_command"),
    ]


def _action_type_names():
    return {v: k for k, v in _action_type_options()}


def _schedule_label(label: str) -> str:
    mapping = {
        "不设定时": "schedule_none",
        "每天 09:00": "schedule_daily_9",
        "每天 10:00": "schedule_daily_10",
        "每天 18:00": "schedule_daily_18",
        "每周一 09:00": "schedule_weekly_mon_9",
        "每小时": "schedule_hourly",
        "每30分钟": "schedule_30min",
        "自定义...": "schedule_custom",
    }
    key = mapping.get(label)
    return _tr(key) if key else label


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    c = _C()
    f.setStyleSheet(f"background-color:{c['border']}44;max-height:1px;border:none;")
    return f


def _section(text: str) -> QLabel:
    c = _C()
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size:12px;font-weight:bold;color:{c['accent']};padding:2px 0;background:transparent;")
    return lbl


def _browse_btn(callback) -> QPushButton:
    btn = QPushButton(_tr("browse"))
    btn.setFixedWidth(52)
    btn.setStyleSheet("padding:4px 6px;font-size:12px;")
    btn.clicked.connect(callback)
    return btn


def _field_row(label: str, widget, browse_cb=None) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    c = _C()
    lbl = QLabel(label)
    lbl.setFixedWidth(76)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet(f"color:{c['text2']};font-size:12px;background:transparent;")
    row.addWidget(lbl)
    row.addWidget(widget, stretch=1)
    if browse_cb:
        row.addWidget(_browse_btn(browse_cb))
    return row


def _hint(text: str) -> QLabel:
    c = _C()
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{c['text2']};font-size:11px;background:transparent;")
    lbl.setWordWrap(True)
    return lbl




# ══════════════════════════════════════════════════════
#  各操作类型的配置面板
# ══════════════════════════════════════════════════════

class P4SyncPanel(QWidget):
    def __init__(self, action: Dict[str, Any]):
        super().__init__()
        self.action = action
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
        layout.addWidget(_section(_tr("p4_config")))
        layout.addWidget(_sep())

        self.depot = QLineEdit(action.get("depot_path", ""))
        self.depot.setPlaceholderText(_tr("depot_placeholder"))
        layout.addLayout(_field_row(_tr("depot_path"), self.depot))

        layout.addWidget(_section(_tr("connection_info")))

        self.port = QLineEdit(action.get("p4_port", ""))
        self.port.setPlaceholderText("例: 21.214.252.179:1666")
        layout.addLayout(_field_row(_tr("p4_server"), self.port))

        self.user = QLineEdit(action.get("p4_user", ""))
        self.user.setPlaceholderText(_tr("username"))
        layout.addLayout(_field_row(_tr("username"), self.user))

        self.passwd = QLineEdit(action.get("p4_passwd", ""))
        self.passwd.setPlaceholderText(_tr("password_placeholder"))
        self.passwd.setEchoMode(QLineEdit.EchoMode.Password)
        show_pw = QCheckBox(_tr("show"))
        show_pw.setFixedWidth(54)
        show_pw.toggled.connect(lambda c: self.passwd.setEchoMode(
            QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password))
        pw_row = QHBoxLayout()
        pw_row.setSpacing(6)
        lbl = QLabel(_tr("password"))
        lbl.setFixedWidth(80)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet("color: #8a8aaa; font-size: 12px;")
        pw_row.addWidget(lbl)
        pw_row.addWidget(self.passwd, stretch=1)
        pw_row.addWidget(show_pw)
        layout.addLayout(pw_row)

        self.client = QLineEdit(action.get("p4_client", ""))
        self.client.setPlaceholderText(_tr("workspace_placeholder"))
        layout.addLayout(_field_row(_tr("workspace"), self.client))

        self.auto_login = QCheckBox(_tr("auto_login"))
        self.auto_login.setChecked(action.get("auto_login", True))
        self.force = QCheckBox(_tr("force_sync"))
        self.force.setChecked(action.get("force", False))
        opts_row = QHBoxLayout()
        opts_row.addWidget(self.auto_login)
        opts_row.addSpacing(20)
        opts_row.addWidget(self.force)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        layout.addSpacing(4)
        layout.addWidget(_section(_tr("dll_fix")))
        layout.addWidget(_sep())

        self.revert_dll_before = QCheckBox(_tr("revert_dll"))
        self.revert_dll_before.setToolTip(_tr("revert_dll_tip"))
        self.revert_dll_before.setChecked(action.get("revert_dll_before_sync", False))
        layout.addWidget(self.revert_dll_before)

        self.refresh_dll_after = QCheckBox(_tr("refresh_dll"))
        self.refresh_dll_after.setToolTip(_tr("refresh_dll_tip"))
        self.refresh_dll_after.setChecked(action.get("refresh_dll_after_sync", False))
        layout.addWidget(self.refresh_dll_after)

        self.dll_depot = QLineEdit(action.get("dll_depot_path", ""))
        self.dll_depot.setPlaceholderText(_tr("dll_path_placeholder"))
        layout.addLayout(_field_row(_tr("dll_path"), self.dll_depot))
        layout.addWidget(_hint(_tr("dll_hint")))

        layout.addStretch()

    def save(self):
        self.action["depot_path"] = self.depot.text().strip()
        self.action["p4_port"] = self.port.text().strip()
        self.action["p4_user"] = self.user.text().strip()
        self.action["p4_passwd"] = self.passwd.text()
        self.action["p4_client"] = self.client.text().strip()
        self.action["auto_login"] = self.auto_login.isChecked()
        self.action["force"] = self.force.isChecked()
        self.action["revert_dll_before_sync"] = self.revert_dll_before.isChecked()
        self.action["refresh_dll_after_sync"] = self.refresh_dll_after.isChecked()
        self.action["dll_depot_path"] = self.dll_depot.text().strip()


class UEProjectPanel(QWidget):
    def __init__(self, action: Dict[str, Any]):
        super().__init__()
        self.action = action
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        layout.addWidget(_section(_tr("project_file")))
        layout.addWidget(_sep())

        self.uproject = QLineEdit(action.get("uproject_path", ""))
        self.uproject.setPlaceholderText(_tr("uproject_placeholder"))
        layout.addLayout(_field_row(".uproject", self.uproject,
            lambda: self._browse_file(self.uproject, _tr("ue_project_filter"))))

        self.engine = QLineEdit(action.get("engine_path", ""))
        self.engine.setPlaceholderText(_tr("engine_placeholder"))
        layout.addLayout(_field_row(_tr("engine_path"), self.engine,
            lambda: self._browse_engine(self.engine)))

        layout.addSpacing(4)
        layout.addWidget(_section(_tr("execution_steps")))
        layout.addWidget(_sep())

        self.do_gen = QCheckBox(_tr("do_generate"))
        self.do_gen.setChecked(action.get("do_generate", True) is not False)

        self.do_sln = QCheckBox(_tr("do_open_sln"))
        self.do_sln.setChecked(action.get("do_open_sln", True) is not False)

        self.do_build = QCheckBox(_tr("do_build"))
        self.do_build.setChecked(action.get("do_build", False) is True)
        self.do_build.toggled.connect(self._toggle_build_opts)

        self.do_launch = QCheckBox(_tr("do_launch"))
        self.do_launch.setChecked(action.get("do_launch_editor", False) is True)

        layout.addWidget(self.do_gen)
        layout.addWidget(self.do_sln)
        layout.addWidget(self.do_build)
        layout.addWidget(self.do_launch)

        # 编译选项
        self.build_opts = QWidget()
        bo_layout = QHBoxLayout(self.build_opts)
        bo_layout.setContentsMargins(22, 0, 0, 0)
        bo_layout.setSpacing(10)

        self.cfg_combo = QComboBox()
        for c in ["Development Editor", "DebugGame Editor", "Debug Editor", "Shipping", "Development"]:
            self.cfg_combo.addItem(c)
        cur = action.get("build_config", "Development Editor")
        idx = self.cfg_combo.findText(cur)
        if idx >= 0:
            self.cfg_combo.setCurrentIndex(idx)

        self.plt_combo = QComboBox()
        for p in ["Win64", "Win32", "Linux", "Mac"]:
            self.plt_combo.addItem(p)
        cur_p = action.get("build_platform", "Win64")
        idx2 = self.plt_combo.findText(cur_p)
        if idx2 >= 0:
            self.plt_combo.setCurrentIndex(idx2)

        bo_layout.addWidget(QLabel(_tr("config")))
        bo_layout.addWidget(self.cfg_combo)
        bo_layout.addWidget(QLabel(_tr("platform")))
        bo_layout.addWidget(self.plt_combo)
        btn_debug_game = QPushButton(_tr("use_debug_game"))
        btn_debug_game.setToolTip(_tr("use_debug_game_tip"))
        btn_debug_game.clicked.connect(lambda: self.cfg_combo.setCurrentText("DebugGame Editor"))
        bo_layout.addWidget(btn_debug_game)
        bo_layout.addStretch()
        self.build_opts.setVisible(self.do_build.isChecked())
        layout.addWidget(self.build_opts)

        layout.addWidget(_hint(_tr("ue_hint")))
        layout.addStretch()

    def _browse_file(self, edit: QLineEdit, filt: str):
        path, _ = QFileDialog.getOpenFileName(self, _tr("select_file"), "", filt + ";;" + _tr("all_files"))
        if path:
            edit.setText(path)

    def _browse_dir(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, _tr("select_folder"))
        if path:
            edit.setText(path)

    def _browse_engine(self, edit: QLineEdit):
        """引擎路径：先让用户选 exe（自动反推引擎根），取消则退回到选文件夹"""
        start_dir = edit.text().strip() or ""
        path, _ = QFileDialog.getOpenFileName(
            self, _tr("select_engine_exe"),
            start_dir,
            _tr("ue_file_filter")
        )
        if path:
            root = self._resolve_engine_root_from_exe(path)
            edit.setText(root or path)
            return
        # 用户取消 → 退回选文件夹模式
        folder = QFileDialog.getExistingDirectory(self, _tr("select_engine_root"), start_dir)
        if folder:
            edit.setText(folder)

    @staticmethod
    def _resolve_engine_root_from_exe(exe_path: str) -> str:
        """从一个 UE 可执行文件向上回溯，找到包含 Engine/Binaries 或 Engine/Build 的引擎根目录。

        典型：<root>/Engine/Binaries/Win64/UnrealEditor.exe  → 返回 <root>
        找不到时返回空串。
        """
        try:
            p = Path(exe_path).resolve()
            if p.is_file():
                cur = p.parent
            else:
                cur = p
            # 向上最多回溯 8 层
            for _ in range(8):
                if (cur / "Engine" / "Binaries").is_dir() or (cur / "Engine" / "Build").is_dir():
                    return str(cur)
                if cur.parent == cur:
                    break
                cur = cur.parent
        except Exception:
            return ""
        return ""

    def _toggle_build_opts(self, checked: bool):
        self.build_opts.setVisible(checked)

    def save(self):
        self.action["uproject_path"] = self.uproject.text().strip()
        self.action["engine_path"] = self.engine.text().strip()
        self.action["do_generate"] = self.do_gen.isChecked()
        self.action["do_open_sln"] = self.do_sln.isChecked()
        self.action["do_build"] = self.do_build.isChecked()
        self.action["do_launch_editor"] = self.do_launch.isChecked()
        self.action["build_config"] = self.cfg_combo.currentText()
        self.action["build_platform"] = self.plt_combo.currentText()


class OpenSoftwarePanel(QWidget):
    def __init__(self, action: Dict[str, Any]):
        super().__init__()
        self.action = action
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
        layout.addWidget(_section(_tr("program")))
        layout.addWidget(_sep())

        self.exe = QLineEdit(action.get("exe_path", ""))
        self.exe.setPlaceholderText(_tr("program_placeholder"))
        layout.addLayout(_field_row(_tr("program_path"), self.exe,
            lambda: self._browse()))

        self.args = QLineEdit(action.get("args", ""))
        self.args.setPlaceholderText(_tr("args_placeholder"))
        layout.addLayout(_field_row(_tr("args"), self.args))
        layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, _tr("select_program"), "",
            _tr("exe_filter"))
        if path:
            self.exe.setText(path)

    def save(self):
        self.action["exe_path"] = self.exe.text().strip()
        self.action["args"] = self.args.text().strip()


class OpenPathPanel(QWidget):
    def __init__(self, action: Dict[str, Any]):
        super().__init__()
        self.action = action
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
        layout.addWidget(_section(_tr("open_path")))
        layout.addWidget(_sep())

        self.path = QLineEdit(action.get("path", ""))
        self.path.setPlaceholderText(_tr("path_placeholder"))
        layout.addLayout(_field_row(_tr("path"), self.path))

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(86, 0, 0, 0)
        b1 = QPushButton(_tr("select_folder"))
        b1.clicked.connect(lambda: self._browse_dir())
        b2 = QPushButton(_tr("select_file_button"))
        b2.clicked.connect(lambda: self._browse_file())
        btn_row.addWidget(b1)
        btn_row.addWidget(b2)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

    def _browse_dir(self):
        p = QFileDialog.getExistingDirectory(self, _tr("select_folder"))
        if p:
            self.path.setText(p)

    def _browse_file(self):
        p, _ = QFileDialog.getOpenFileName(self, _tr("select_file"), "", _tr("all_files"))
        if p:
            self.path.setText(p)

    def save(self):
        self.action["path"] = self.path.text().strip()


class RunCommandPanel(QWidget):
    def __init__(self, action: Dict[str, Any]):
        super().__init__()
        self.action = action
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
        layout.addWidget(_section(_tr("run_command")))
        layout.addWidget(_sep())

        self.cmd = QTextEdit()
        self.cmd.setPlainText(action.get("command", ""))
        self.cmd.setPlaceholderText(_tr("command_placeholder"))
        self.cmd.setFixedHeight(80)
        layout.addLayout(_field_row(_tr("command"), self.cmd))

        self.workdir = QLineEdit(action.get("working_dir", ""))
        self.workdir.setPlaceholderText(_tr("working_dir_placeholder"))
        layout.addLayout(_field_row(_tr("working_dir"), self.workdir,
            lambda: self._browse()))

        self.shell = QCheckBox(_tr("use_shell"))
        self.shell.setChecked(action.get("shell", True))
        layout.addWidget(self.shell)
        layout.addStretch()

    def _browse(self):
        p = QFileDialog.getExistingDirectory(self, _tr("working_dir"))
        if p:
            self.workdir.setText(p)

    def save(self):
        self.action["command"] = self.cmd.toPlainText().strip()
        self.action["working_dir"] = self.workdir.text().strip()
        self.action["shell"] = self.shell.isChecked()


PANEL_MAP = {
    "p4_sync":      P4SyncPanel,
    "ue_project":   UEProjectPanel,
    "open_software": OpenSoftwarePanel,
    "open_path":    OpenPathPanel,
    "run_command":  RunCommandPanel,
}

# ══════════════════════════════════════════════════════
#  主编辑对话框
# ══════════════════════════════════════════════════════

class TaskEditorDialog(QDialog):
    def __init__(self, task: Dict[str, Any], parent=None, is_new: bool = False):
        super().__init__(parent)
        self.task = task
        self.is_new = is_new
        self.step_entries: List[Dict] = []
        self._drag_pos = None

        self.setModal(True)
        self.resize(800, 600)
        self.setMinimumSize(700, 520)
        # 无边框
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setStyleSheet(_build_editor_style())

        self._build_ui()
        self._load_steps()

    # ──────────────────────────────────────
    def _build_ui(self):
        c = _C()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ═══ 自定义标题栏 ═══
        title_bar = QWidget()
        title_bar.setFixedHeight(46)
        title_bar.setStyleSheet(f"background-color:{c['panel']};border-radius:0px;")
        title_bar.mousePressEvent   = self._tb_press
        title_bar.mouseMoveEvent    = self._tb_move
        title_bar.mouseReleaseEvent = self._tb_release
        tb_l = QHBoxLayout(title_bar)
        tb_l.setContentsMargins(16, 0, 8, 0)
        tb_l.setSpacing(10)

        title_lbl = QLabel(_tr("task_new_title") if self.is_new else _tr("task_edit_title", name=self.task.get("name", "")))
        title_lbl.setStyleSheet(
            f"font-size:14px;font-weight:bold;color:{c['text']};background:transparent;")
        btn_close = QPushButton("✕")
        btn_close.setObjectName("btn_win_close")
        btn_close.setFixedSize(30, 30)
        btn_close.setToolTip(_tr("close"))
        btn_close.clicked.connect(self.reject)

        tb_l.addWidget(title_lbl)
        tb_l.addStretch()
        tb_l.addWidget(btn_close)
        root.addWidget(title_bar)

        # ═══ 主体内容 ═══
        content = QWidget()
        content.setStyleSheet(f"background-color:{c['bg']};")
        content_l = QVBoxLayout(content)
        content_l.setContentsMargins(16, 12, 16, 12)
        content_l.setSpacing(10)

        # ── 基本信息行 ──
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        name_lbl = QLabel(_tr("task_name"))
        name_lbl.setStyleSheet(f"color:{c['text2']};font-size:12px;background:transparent;")
        name_lbl.setFixedWidth(56)
        self.name_edit = QLineEdit(self.task.get("name", ""))
        self.name_edit.setPlaceholderText(_tr("task_name_placeholder"))
        self.name_edit.setFixedHeight(32)

        desc_lbl = QLabel(_tr("description"))
        desc_lbl.setStyleSheet(f"color:{c['text2']};font-size:12px;background:transparent;")
        desc_lbl.setFixedWidth(30)
        self.desc_edit = QLineEdit(self.task.get("description", ""))
        self.desc_edit.setPlaceholderText(_tr("optional"))
        self.desc_edit.setFixedHeight(32)

        info_row.addWidget(name_lbl)
        info_row.addWidget(self.name_edit, stretch=2)
        info_row.addWidget(desc_lbl)
        info_row.addWidget(self.desc_edit, stretch=3)
        content_l.addLayout(info_row)
        content_l.addWidget(_sep())

        # ── 中间：左步骤列表 | 右配置面板 ──
        body = QHBoxLayout()
        body.setSpacing(10)

        # 左侧步骤列表
        left = QWidget()
        left.setFixedWidth(176)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        left_layout.addWidget(_section(_tr("steps")))
        self.step_list = QListWidget()
        self.step_list.setMinimumHeight(180)
        self.step_list.currentRowChanged.connect(self._on_step_selected)
        left_layout.addWidget(self.step_list, stretch=1)

        step_btns = QHBoxLayout()
        step_btns.setSpacing(4)
        self.btn_up = QPushButton("↑")
        self.btn_up.setFixedSize(28, 28)
        self.btn_up.setToolTip(_tr("move_up"))
        self.btn_up.clicked.connect(lambda: self._move_step(-1))
        self.btn_dn = QPushButton("↓")
        self.btn_dn.setFixedSize(28, 28)
        self.btn_dn.setToolTip(_tr("move_down"))
        self.btn_dn.clicked.connect(lambda: self._move_step(1))
        self.chk_step_enabled = QCheckBox(_tr("enabled"))
        self.chk_step_enabled.setToolTip(_tr("enabled_tip"))
        self.chk_step_enabled.setEnabled(False)  # 未选中步骤时禁用
        self.chk_step_enabled.toggled.connect(self._on_step_enabled_toggled)
        self.btn_del_step = QPushButton(_tr("delete"))
        self.btn_del_step.setObjectName("btn_del_step")
        self.btn_del_step.setFixedHeight(28)
        self.btn_del_step.clicked.connect(self._delete_step)
        step_btns.addWidget(self.btn_up)
        step_btns.addWidget(self.btn_dn)
        step_btns.addWidget(self.chk_step_enabled)
        step_btns.addStretch()
        step_btns.addWidget(self.btn_del_step)
        left_layout.addLayout(step_btns)

        left_layout.addWidget(_sep())
        add_lbl = QLabel(_tr("add_step"))
        add_lbl.setStyleSheet(f"color:{c['text2']};font-size:11px;background:transparent;")
        left_layout.addWidget(add_lbl)
        self.type_combo = QComboBox()
        for name, key in _action_type_options():
            self.type_combo.addItem(name, key)
        left_layout.addWidget(self.type_combo)
        btn_add = QPushButton(_tr("add"))
        btn_add.setObjectName("btn_add_step")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._add_step)
        left_layout.addWidget(btn_add)
        body.addWidget(left)

        # 右侧配置面板
        right = QFrame()
        right.setObjectName("config_panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_stack = QStackedWidget()
        empty_page = QWidget()
        ep_layout = QVBoxLayout(empty_page)
        empty_lbl = QLabel(_tr("empty_step_hint"))
        empty_lbl.setStyleSheet(f"color:{c['text2']};font-size:13px;background:transparent;")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ep_layout.addWidget(empty_lbl)
        self.panel_stack.addWidget(empty_page)
        right_layout.addWidget(self.panel_stack)
        body.addWidget(right, stretch=1)

        content_l.addLayout(body, stretch=1)
        content_l.addWidget(_sep())

        # ── 底部：定时 + 保存 ──
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        sched_lbl = QLabel(_tr("schedule"))
        sched_lbl.setStyleSheet(f"color:{c['text2']};font-size:12px;background:transparent;")
        self.sched_combo = QComboBox()
        self.sched_combo.setMinimumWidth(150)
        for label, val in SCHEDULE_PRESETS:
            self.sched_combo.addItem(_schedule_label(label), val)
        self.sched_combo.currentIndexChanged.connect(self._on_sched_changed)

        self.custom_sched = QWidget()
        cs_layout = QHBoxLayout(self.custom_sched)
        cs_layout.setContentsMargins(0, 0, 0, 0)
        cs_layout.setSpacing(6)
        self.sched_type = QComboBox()
        self.sched_type.addItem(_tr("schedule_daily_custom"), "cron")
        self.sched_type.addItem(_tr("schedule_interval"), "interval")
        self.cron_h = QSpinBox(); self.cron_h.setRange(0, 23); self.cron_h.setFixedWidth(50)
        self.cron_m = QSpinBox(); self.cron_m.setRange(0, 59); self.cron_m.setFixedWidth(50)
        self.int_h = QSpinBox(); self.int_h.setRange(0, 23); self.int_h.setSuffix("h"); self.int_h.setFixedWidth(56)
        self.int_m = QSpinBox(); self.int_m.setRange(0, 59); self.int_m.setSuffix("m"); self.int_m.setFixedWidth(56)
        cs_layout.addWidget(self.sched_type)
        cs_layout.addWidget(QLabel(_tr("hour_label")))
        cs_layout.addWidget(self.cron_h)
        cs_layout.addWidget(QLabel(":"))
        cs_layout.addWidget(self.cron_m)
        cs_layout.addWidget(self.int_h)
        cs_layout.addWidget(self.int_m)
        self.custom_sched.setVisible(False)

        bottom.addWidget(sched_lbl)
        bottom.addWidget(self.sched_combo)
        bottom.addWidget(self.custom_sched)
        bottom.addStretch()

        btn_cancel = QPushButton(_tr("cancel"))
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton(_tr("save_task"))
        self.btn_save.setObjectName("btn_save")
        self.btn_save.setFixedHeight(34)
        self.btn_save.clicked.connect(self._save)
        bottom.addWidget(btn_cancel)
        bottom.addWidget(self.btn_save)
        content_l.addLayout(bottom)

        root.addWidget(content)
        self._prefill_schedule()

    # ── 标题栏拖动 ──
    def _tb_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _tb_move(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def _tb_release(self, e):
        self._drag_pos = None



    # ──────────────────────────────────────
    #  步骤管理
    # ──────────────────────────────────────
    def _load_steps(self):
        for action in self.task.get("actions", []):
            self._append_step(action)
        self._refresh_list_labels()
        if self.step_list.count() > 0:
            self.step_list.setCurrentRow(0)

    def _append_step(self, action: Dict[str, Any]):
        panel_cls = PANEL_MAP.get(action["type"], RunCommandPanel)
        panel = panel_cls(action)

        # 包一层 ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)

        stack_idx = self.panel_stack.addWidget(scroll)
        self.step_entries.append({"action": action, "panel": panel, "stack_idx": stack_idx})

        # 列表项
        type_label = _action_type_names().get(action["type"], action["type"])
        label = action.get("label") or type_label
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.UserRole, len(self.step_entries) - 1)
        self.step_list.addItem(item)

    def _add_step(self):
        atype = self.type_combo.currentData()
        action = new_action(atype)
        self._append_step(action)
        self.step_list.setCurrentRow(self.step_list.count() - 1)

    def _on_step_selected(self, row: int):
        if row < 0 or row >= len(self.step_entries):
            self.panel_stack.setCurrentIndex(0)
            self.chk_step_enabled.setEnabled(False)
            self.chk_step_enabled.blockSignals(True)
            self.chk_step_enabled.setChecked(False)
            self.chk_step_enabled.blockSignals(False)
            return
        entry = self.step_entries[row]
        self.panel_stack.setCurrentIndex(entry["stack_idx"])
        # 同步"启用"开关
        self.chk_step_enabled.setEnabled(True)
        self.chk_step_enabled.blockSignals(True)
        self.chk_step_enabled.setChecked(entry["action"].get("enabled", True))
        self.chk_step_enabled.blockSignals(False)
        # 更新列表项文字
        self._refresh_list_labels()

    def _on_step_enabled_toggled(self, checked: bool):
        row = self.step_list.currentRow()
        if row < 0 or row >= len(self.step_entries):
            return
        self.step_entries[row]["action"]["enabled"] = checked
        self._refresh_list_labels()

    def _refresh_list_labels(self):
        from PyQt6.QtGui import QColor, QFont
        for i, entry in enumerate(self.step_entries):
            type_label = _action_type_names().get(entry["action"]["type"], entry["action"]["type"])
            label = entry["action"].get("label") or type_label
            enabled = entry["action"].get("enabled", True)
            prefix = "" if enabled else "🚫 "
            if i < self.step_list.count():
                item = self.step_list.item(i)
                item.setText(f"{prefix}{i+1}. {label}")
                # 视觉弱化：未启用项灰色 + 斜体
                f = item.font()
                f.setItalic(not enabled)
                item.setFont(f)
                item.setForeground(QColor("#888") if not enabled else QColor("#e6e6e6"))

    def _delete_step(self):
        row = self.step_list.currentRow()
        if row < 0 or row >= len(self.step_entries):
            return
        entry = self.step_entries.pop(row)
        self.panel_stack.removeWidget(self.panel_stack.widget(entry["stack_idx"]))
        self.step_list.takeItem(row)
        # 修正后面所有 stack_idx（removeWidget 后 index 不变，但 list 中要重建索引）
        self._rebuild_stack()

    def _rebuild_stack(self):
        """删除步骤后重建 panel_stack，保持 stack_idx 准确"""
        # 清空 stack（保留 index 0 的空状态页）
        while self.panel_stack.count() > 1:
            w = self.panel_stack.widget(1)
            self.panel_stack.removeWidget(w)
        self.step_list.clear()
        for i, entry in enumerate(self.step_entries):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(entry["panel"])
            idx = self.panel_stack.addWidget(scroll)
            entry["stack_idx"] = idx
            type_label = _action_type_names().get(entry["action"]["type"], entry["action"]["type"])
            label = entry["action"].get("label") or type_label
            item = QListWidgetItem(f"{i+1}. {label}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.step_list.addItem(item)
        # 统一刷新禁用态样式
        self._refresh_list_labels()
        if self.step_list.count() > 0:
            self.step_list.setCurrentRow(0)

    def _move_step(self, direction: int):
        row = self.step_list.currentRow()
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.step_entries):
            return
        self.step_entries[row], self.step_entries[new_row] = \
            self.step_entries[new_row], self.step_entries[row]
        self._rebuild_stack()
        self.step_list.setCurrentRow(new_row)

    # ──────────────────────────────────────
    #  定时
    # ──────────────────────────────────────
    def _prefill_schedule(self):
        schedule = self.task.get("schedule")
        if not schedule:
            self.sched_combo.setCurrentIndex(0)
            return
        for i, (_, val) in enumerate(SCHEDULE_PRESETS):
            if val == schedule:
                self.sched_combo.setCurrentIndex(i)
                return
        for i, (_, val) in enumerate(SCHEDULE_PRESETS):
            if val == "custom":
                self.sched_combo.setCurrentIndex(i)
                break
        self.custom_sched.setVisible(True)
        if schedule.get("type") == "interval":
            self.sched_type.setCurrentIndex(1)
            self.int_h.setValue(int(schedule.get("hours", 0)))
            self.int_m.setValue(int(schedule.get("minutes", 0)))
        else:
            self.sched_type.setCurrentIndex(0)
            self.cron_h.setValue(int(schedule.get("hour", 9)))
            self.cron_m.setValue(int(schedule.get("minute", 0)))

    def _on_sched_changed(self, _):
        self.custom_sched.setVisible(self.sched_combo.currentData() == "custom")

    def _build_schedule(self) -> Optional[Dict]:
        val = self.sched_combo.currentData()
        if val is None:
            return None
        if val == "custom":
            if self.sched_type.currentData() == "interval":
                return {"type": "interval",
                        "hours": str(self.int_h.value()),
                        "minutes": str(self.int_m.value())}
            else:
                return {"type": "cron",
                        "hour": str(self.cron_h.value()),
                        "minute": str(self.cron_m.value()),
                        "day_of_week": "*"}
        return val

    # ──────────────────────────────────────
    #  保存
    # ──────────────────────────────────────
    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            msg = QMessageBox(self)
            msg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            msg.setStyleSheet(self.styleSheet())
            msg.setText(_tr("enter_task_name"))
            msg.exec()
            self.name_edit.setFocus()
            return

        self.task["name"] = name
        self.task["description"] = self.desc_edit.text().strip()
        # 移除了任务级启用开关；为避免历史数据里 enabled=False 导致任务无法运行，统一置 True
        self.task["enabled"] = True
        self.task["schedule"] = self._build_schedule()

        actions = []
        for entry in self.step_entries:
            entry["panel"].save()
            actions.append(entry["action"])
        self.task["actions"] = actions

        self.accept()
