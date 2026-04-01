"""
配置管理器 - 负责任务配置的持久化存储
"""
import json
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional


# 配置文件路径
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "AutoTasker"
CONFIG_FILE = CONFIG_DIR / "tasks.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# ---------- 任务数据结构 ----------
def new_task(name: str = "新任务") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "enabled": True,
        "description": "",
        "actions": [],
        "schedule": None,
        "pinned": False,        # True = 常用任务区，False = 其他任务区
        "created_at": "",
        "last_run": None,
        "last_result": None,
    }


def new_action(action_type: str) -> Dict[str, Any]:
    """
    action_type 可选值:
      - open_software  : 打开软件/程序
      - open_path      : 打开文件夹/文件
      - run_command    : 执行命令/脚本
      - p4_sync        : P4 同步指定路径
      - ue_project     : UE 项目操作（Generate VS Files / 编译）
    """
    base = {
        "id": str(uuid.uuid4()),
        "type": action_type,
        "label": "",
    }
    defaults = {
        "open_software": {"exe_path": "", "args": ""},
        "open_path":     {"path": ""},
        "run_command":   {"command": "", "working_dir": "", "shell": True},
        "p4_sync":       {"depot_path": "", "p4_port": "", "p4_user": "", "p4_passwd": "", "p4_client": "", "force": False, "auto_login": True},
        "ue_project":    {
            "uproject_path": "",
            "engine_path": "",
            "do_generate": True,
            "do_open_sln": True,
            "do_build": False,
            "do_launch_editor": False,
            "build_config": "Development Editor",
            "build_platform": "Win64",
            "msbuild_path": "",
        },
    }
    base.update(defaults.get(action_type, {}))
    return base


# ---------- 持久化 ----------
def load_tasks() -> List[Dict[str, Any]]:
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        return []
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_tasks(tasks: List[Dict[str, Any]]):
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def load_settings() -> Dict[str, Any]:
    ensure_config_dir()
    defaults = {
        "minimize_to_tray": True,
        "start_with_windows": False,
        "theme": "nebula",        # 默认星云主题
        "log_max_lines": 500,
    }
    if not SETTINGS_FILE.exists():
        return defaults
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            defaults.update(data)
            return defaults
    except Exception:
        return defaults


def save_settings(settings: Dict[str, Any]):
    ensure_config_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
