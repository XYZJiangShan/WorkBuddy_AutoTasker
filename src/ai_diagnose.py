"""
AI 日志诊断
通过 OpenAI 兼容协议（/v1/chat/completions）把任务失败上下文发给大模型，
返回中文的"问题定位 + 修复步骤"。

配置存于 %APPDATA%\AutoTasker\ai_config.json：
{
  "base_url": "https://api.openai.com/v1",
  "api_key":  "sk-...",
  "model":    "gpt-4o-mini",
  "timeout":  60,
  "extra_headers": {}   # 可选，某些网关需要额外头
}
"""
from __future__ import annotations
import json
import os
import ssl
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, List

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "AutoTasker"
AI_CONFIG_FILE = CONFIG_DIR / "ai_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "timeout": 60,
    "extra_headers": {},
}

SYSTEM_PROMPT = (
    "你是一个 Windows / Unreal Engine / Perforce 工程助手，精通 UE5 源码编译、"
    "UnrealBuildTool、MSBuild、P4 sync、.NET 运行时和 Windows 命令行。"
    "用户会贴一段任务失败的日志，你需要：\n"
    "1. 用一句话给出【问题结论】；\n"
    "2. 给出【根因分析】（最多 3 条，说清楚为什么会这样）；\n"
    "3. 给出【修复步骤】（编号列表，直接可执行的命令 / 路径 / 配置项改动，不要泛泛而谈）；\n"
    "4. 如信息不足，明确指出还需要哪些信息。\n"
    "使用简体中文，结论先行，不要寒暄，不要重复用户给的日志原文。"
)


# -------- 配置读写 --------
def load_ai_config() -> Dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = dict(DEFAULT_CONFIG)
    if AI_CONFIG_FILE.exists():
        try:
            raw = AI_CONFIG_FILE.read_text(encoding="utf-8")
            if raw.strip():
                user = json.loads(raw)
                if isinstance(user, dict):
                    data.update(user)
        except Exception:
            pass
    # 兜底：extra_headers 必须是 dict
    if not isinstance(data.get("extra_headers"), dict):
        data["extra_headers"] = {}
    return data


def save_ai_config(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    AI_CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def is_configured() -> bool:
    cfg = load_ai_config()
    return bool(cfg.get("api_key")) and bool(cfg.get("base_url")) and bool(cfg.get("model"))


# -------- 上下文构造 --------
def build_user_prompt(
    step_label: str,
    command: Optional[List[str]],
    error_message: str,
    log_tail: str,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """组装要发给 AI 的正文。尽量紧凑，避免烧 token。"""
    parts: List[str] = []
    parts.append(f"【失败步骤】{step_label}")
    if command:
        # 命令行可能很长，只取前 800 字符
        cmd_str = " ".join(str(c) for c in command)
        if len(cmd_str) > 800:
            cmd_str = cmd_str[:800] + " ..."
        parts.append(f"【执行命令】{cmd_str}")
    if error_message:
        parts.append(f"【错误摘要】{error_message}")
    if extra:
        for k, v in extra.items():
            if v:
                parts.append(f"【{k}】{v}")
    # 日志段：截取后 6000 字符（报错通常在末尾）
    tail = log_tail.strip()
    if len(tail) > 6000:
        tail = "... (前文已截断)\n" + tail[-6000:]
    parts.append("【日志尾部】\n" + tail)
    return "\n\n".join(parts)


# -------- 调用 LLM --------
class AIDiagnoseError(Exception):
    pass


def diagnose(
    step_label: str,
    command: Optional[List[str]],
    error_message: str,
    log_tail: str,
    extra: Optional[Dict[str, Any]] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> str:
    """同步调用 LLM，返回 markdown/纯文本诊断结果。失败抛 AIDiagnoseError。"""
    cfg = cfg or load_ai_config()
    api_key = (cfg.get("api_key") or "").strip()
    base_url = (cfg.get("base_url") or "").strip().rstrip("/")
    model = (cfg.get("model") or "").strip()
    timeout = int(cfg.get("timeout") or 60)

    if not api_key:
        raise AIDiagnoseError("未配置 AI API Key，请先在日志面板点「⚙ AI 设置」")
    if not base_url:
        raise AIDiagnoseError("未配置 AI Base URL")
    if not model:
        raise AIDiagnoseError("未配置 AI Model")

    user_prompt = build_user_prompt(step_label, command, error_message, log_tail, extra)

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "stream": False,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    for k, v in (cfg.get("extra_headers") or {}).items():
        if isinstance(k, str) and isinstance(v, str):
            headers[k] = v

    url = base_url + "/chat/completions"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    # 某些企业网络缺证书，给个兜底：先严，失败再宽（默认严格）
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise AIDiagnoseError(f"HTTP {e.code} {e.reason}: {detail[:500]}") from e
    except urllib.error.URLError as e:
        raise AIDiagnoseError(f"网络错误: {e.reason}") from e
    except Exception as e:
        raise AIDiagnoseError(f"请求失败: {e}") from e

    try:
        obj = json.loads(raw)
        content = obj["choices"][0]["message"]["content"]
    except Exception as e:
        raise AIDiagnoseError(f"响应解析失败: {e}; 原始内容前 200 字: {raw[:200]}") from e

    return (content or "").strip() or "(AI 返回为空)"
