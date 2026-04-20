"""
任务执行引擎 - 负责实际执行各类操作
"""
import os
import ctypes
import glob
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional


class ActionResult:
    def __init__(self, success: bool, message: str, output: str = ""):
        self.success = success
        self.message = message
        self.output = output
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"[{self.timestamp}] {status} {self.message}"


class TaskExecutor:
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback or (lambda x: None)

    def _log(self, msg: str):
        self.log_callback(msg)

    # ---- 单个 Action 执行 ----
    def execute_action(self, action: Dict[str, Any], as_admin: bool = False) -> ActionResult:
        atype = action.get("type", "")
        label = action.get("label") or atype

        try:
            if atype == "open_software":
                return self._open_software(action, label, as_admin=as_admin)
            elif atype == "open_path":
                return self._open_path(action, label, as_admin=as_admin)
            elif atype == "run_command":
                return self._run_command(action, label, as_admin=as_admin)
            elif atype == "p4_sync":
                return self._p4_sync(action, label)
            elif atype == "ue_project":
                return self._ue_project(action, label)
            else:
                return ActionResult(False, f"未知操作类型: {atype}")
        except Exception as e:
            return ActionResult(False, f"{label} 执行异常: {e}")

    def _open_software(self, action: Dict, label: str, as_admin: bool = False) -> ActionResult:
        exe_path = action.get("exe_path", "").strip()
        args = action.get("args", "").strip()
        if not exe_path:
            return ActionResult(False, f"[{label}] 未配置程序路径")
        if as_admin:
            try:
                # ShellExecute runas 会弹出 UAC 提权窗口
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", exe_path, args or None, None, 1
                )
                return ActionResult(True, f"[{label}] 已以管理员身份启动: {os.path.basename(exe_path)}")
            except Exception as ex:
                return ActionResult(False, f"[{label}] 管理员启动失败: {ex}")
        cmd = f'"{exe_path}"'
        if args:
            cmd += f" {args}"
        subprocess.Popen(cmd, shell=True)
        return ActionResult(True, f"[{label}] 已启动: {os.path.basename(exe_path)}")

    def _open_path(self, action: Dict, label: str, as_admin: bool = False) -> ActionResult:
        path = action.get("path", "").strip()
        if not path:
            return ActionResult(False, f"[{label}] 未配置路径")
        if as_admin and os.path.isfile(path):
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", path, None, None, 1)
                return ActionResult(True, f"[{label}] 已以管理员身份打开: {path}")
            except Exception as ex:
                return ActionResult(False, f"[{label}] 管理员打开失败: {ex}")
        os.startfile(path)
        return ActionResult(True, f"[{label}] 已打开: {path}")

    def _run_command(self, action: Dict, label: str, as_admin: bool = False) -> ActionResult:
        command = action.get("command", "").strip()
        working_dir = action.get("working_dir", "").strip() or None
        use_shell = action.get("shell", True)
        if not command:
            return ActionResult(False, f"[{label}] 未配置命令")

        if as_admin:
            # 以管理员身份在新 cmd 窗口运行命令（会弹 UAC）
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "cmd.exe",
                    f'/c "{command}"',
                    working_dir, 1
                )
                return ActionResult(True, f"[{label}] 已以管理员身份提交命令（新窗口执行）")
            except Exception as ex:
                return ActionResult(False, f"[{label}] 管理员命令启动失败: {ex}")

        result = subprocess.run(
            command,
            shell=use_shell,
            cwd=working_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            return ActionResult(True, f"[{label}] 命令执行成功", output)
        else:
            return ActionResult(False, f"[{label}] 命令返回错误码 {result.returncode}", output)

    def _p4_sync(self, action: Dict, label: str) -> ActionResult:
        depot_path = action.get("depot_path", "").strip()
        p4_port = action.get("p4_port", "").strip()
        p4_user = action.get("p4_user", "").strip()
        p4_passwd = action.get("p4_passwd", "").strip()
        p4_client = action.get("p4_client", "").strip()
        force = action.get("force", False)
        auto_login = action.get("auto_login", True)

        if not depot_path:
            return ActionResult(False, f"[{label}] 未配置 Depot 路径")

        env = os.environ.copy()
        if p4_port:
            env["P4PORT"] = p4_port
        if p4_user:
            env["P4USER"] = p4_user
        if p4_client:
            env["P4CLIENT"] = p4_client

        # ---- 自动登录 ----
        if auto_login and p4_passwd:
            self._log(f"  → 正在登录 P4（用户: {p4_user or '环境变量'}）...")
            login_result = self._p4_login(env, p4_passwd, label)
            if not login_result.success:
                return login_result
            self._log(f"  ✅ P4 登录成功")

        # ---- 执行 sync ----
        cmd = ["p4", "sync"]
        if force:
            cmd.append("-f")
        cmd.append(depot_path)

        self._log(f"  → 开始同步: {depot_path}")
        if force:
            self._log(f"  ⚠️  已启用强制同步 (-f)，将重新下载所有文件")

        try:
            import time
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合流，简化读取
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,  # 行缓冲
            )

            # 分类统计 + 进度心跳
            added = updated = deleted = refreshed = other = 0
            last_sample_line = ""
            start_ts = time.time()
            last_beat_ts = start_ts
            captured_tail: list[str] = []  # 只留最后若干行用于错误诊断
            TAIL_MAX = 200
            BEAT_INTERVAL = 2.0  # 秒

            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.rstrip()
                if not line:
                    continue

                # 保留尾部日志（错误诊断用）
                captured_tail.append(line)
                if len(captured_tail) > TAIL_MAX:
                    captured_tail.pop(0)

                low = line.lower()
                # 典型 p4 sync 输出：
                #   //depot/... - added as E:\...
                #   //depot/... - updating E:\...
                #   //depot/... - deleted as E:\...
                #   //depot/... - refreshing E:\...
                if " - added as " in line or " - added " in low:
                    added += 1
                elif " - updating " in line or " - updated " in low:
                    updated += 1
                elif " - deleted as " in line or " - deleted " in low:
                    deleted += 1
                elif " - refreshing " in line or " - refreshed " in low:
                    refreshed += 1
                else:
                    other += 1

                last_sample_line = line

                # 每 BEAT_INTERVAL 秒打一次心跳
                now = time.time()
                if now - last_beat_ts >= BEAT_INTERVAL:
                    total = added + updated + deleted + refreshed
                    elapsed = int(now - start_ts)
                    self._log(
                        f"  ⏳ 同步中… 已处理 {total} 个文件 "
                        f"(+{added} 新增 / ~{updated} 更新 / -{deleted} 删除 / ↻{refreshed} 刷新) "
                        f"耗时 {elapsed}s"
                    )
                    last_beat_ts = now

            proc.wait(timeout=600)
            elapsed = int(time.time() - start_ts)
            output = "\n".join(captured_tail)

            # 汇总一行
            total = added + updated + deleted + refreshed
            summary = (
                f"共 {total} 个文件："
                f"+{added} 新增 / ~{updated} 更新 / -{deleted} 删除 / ↻{refreshed} 刷新"
                f"，耗时 {elapsed}s"
            )

            # P4 有时返回 0 但 stderr 里报错（比如 "file(s) not in client view"），
            # 这类属于实际失败，需要单独识别；同时给出"人话"提示
            # 关键字按特异性从高到低排列，命中第一个即停
            p4_err_hints = [
                ("not in client view",
                 "🔧 当前 Workspace 没映射到该路径。请检查 P4 Client 的 View 是否包含该 depot 分支"),
                ("your session has expired",
                 "🔐 P4 会话已过期，请重新登录（可在步骤里勾选\"自动登录\"）"),
                ("perforce password (p4passwd) invalid",
                 "🔐 P4 密码错误或未登录，请检查密码 / 重新登录"),
                ("password invalid",
                 "🔐 P4 密码错误，请检查账号密码"),
                ("client unknown",
                 "🏷️ P4 Workspace（Client）不存在，请确认名称是否正确"),
                ("unknown - use 'client' command",
                 "🏷️ P4 Workspace（Client）不存在，请用 P4V 创建或换一个正确的 Workspace"),
                ("access denied",
                 "🚫 权限不足，你的账号可能没有访问该 depot 的权限，请联系 P4 管理员"),
                ("connect to server failed",
                 "🌐 连不上 P4 服务器，检查 VPN / 网络 / P4PORT 是否正确"),
                ("tcp connect to",
                 "🌐 网络不通，无法连接 P4 服务器，请检查 VPN / 网络"),
                ("no such file",
                 "📂 depot 路径不存在，请检查路径拼写（P4 区分大小写）"),
                ("file(s) up-to-date",
                 "ℹ️ 文件已是最新，无需同步"),  # 这个其实不是错误
            ]
            lower_out = output.lower()
            hit = next(((kw, hint) for kw, hint in p4_err_hints if kw in lower_out), None)

            # "file(s) up-to-date" 是成功场景，单独放行
            if hit and hit[0] == "file(s) up-to-date":
                return ActionResult(True, f"[{label}] P4 Sync 完成：{hit[1]}", output)

            if proc.returncode == 0 and not hit:
                return ActionResult(True, f"[{label}] P4 Sync 成功（{summary}）", output)
            else:
                if hit:
                    reason = hit[1]
                elif proc.returncode != 0:
                    reason = f"p4 进程返回错误码 {proc.returncode}"
                else:
                    reason = "未知错误"
                return ActionResult(False, f"[{label}] P4 Sync 失败：{reason}", output)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            return ActionResult(False, f"[{label}] P4 Sync 超时（>10 分钟），已强制终止")
        except FileNotFoundError:
            return ActionResult(False, f"[{label}] 未找到 p4 命令，请确保 Perforce 客户端已安装并在 PATH 中")

    def _p4_login(self, env: dict, passwd: str, label: str) -> ActionResult:
        """用密码执行 p4 login（通过 stdin 传入密码）"""
        try:
            result = subprocess.run(
                ["p4", "login"],
                input=passwd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                return ActionResult(True, f"[{label}] 登录成功", output)
            else:
                lower = output.lower()
                if "connect to server failed" in lower or "tcp connect to" in lower:
                    reason = "🌐 连不上 P4 服务器，请检查 VPN / 网络 / P4PORT"
                elif "password invalid" in lower or "p4passwd" in lower:
                    reason = "🔐 密码错误，请确认账号密码"
                elif "user" in lower and "doesn't exist" in lower:
                    reason = "👤 P4 账号不存在，请确认用户名"
                else:
                    reason = "登录失败"
                return ActionResult(False, f"[{label}] P4 登录失败：{reason}", output)
        except FileNotFoundError:
            return ActionResult(False, f"[{label}] 未找到 p4 命令")

    def _ue_project(self, action: Dict, label: str) -> ActionResult:
        """UE 项目操作：Generate VS Project Files → 打开 SLN → 编译 → 启动编辑器"""
        uproject_path = action.get("uproject_path", "").strip()
        engine_path = action.get("engine_path", "").strip()
        do_generate = action.get("do_generate", True)
        do_open_sln = action.get("do_open_sln", True)
        do_build = action.get("do_build", False)
        do_launch_editor = action.get("do_launch_editor", False)
        build_config = action.get("build_config", "Development Editor")
        build_platform = action.get("build_platform", "Win64")
        msbuild_path = action.get("msbuild_path", "").strip()

        if not uproject_path:
            return ActionResult(False, f"[{label}] 未配置 .uproject 路径")

        uproject = Path(uproject_path)
        if not uproject.exists():
            return ActionResult(False, f"[{label}] .uproject 文件不存在: {uproject_path}")

        project_dir = uproject.parent
        project_name = uproject.stem
        logs = []

        # ---- 1. 自动定位 UE 引擎 ----
        gen_script = self._find_uat(engine_path, uproject_path)
        if do_generate and not gen_script:
            return ActionResult(False, f"[{label}] 未找到 UE 引擎，请在操作配置中手动填写引擎根目录")

        # ---- 2. Generate VS Project Files ----
        if do_generate:
            # 2.0 前置检查：UBT 动态编译依赖 System.CodeDom.dll，缺失则自动补齐
            self._ensure_ubt_codedom_dll(gen_script)

            self._log(f"  → 正在生成 VS 工程文件...")
            # 判断是 bat 还是 UBT.exe
            if gen_script.suffix.lower() == ".bat":
                gen_cmd = [
                    str(gen_script),
                    "GenerateProjectFiles",
                    f"-project={uproject_path}",
                    "-game",
                    "-engine",
                ]
            else:
                # UnrealBuildTool.exe 模式（源码版/腾讯版）
                gen_cmd = [
                    str(gen_script),
                    "-ProjectFiles",
                    f"-project={uproject_path}",
                    "-game",
                    "-engine",
                ]
            try:
                result = subprocess.run(
                    gen_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=300,
                    cwd=str(project_dir),
                )
                output = (result.stdout + result.stderr).strip()
                if result.returncode != 0:
                    # 识别已知环境问题，给出可执行的修复指引
                    hint = self._diagnose_ubt_error(output)
                    msg = f"[{label}] Generate VS Files 失败 (code {result.returncode})"
                    if hint:
                        msg += f"\n💡 {hint}"
                    return ActionResult(False, msg, output)
                logs.append("Generate VS Files 成功")
                self._log(f"  ✅ Generate VS Files 完成")
                if output:
                    lines = output.splitlines()
                    self._log("\n".join(lines[-10:]))
            except subprocess.TimeoutExpired:
                return ActionResult(False, f"[{label}] Generate VS Files 超时（>5分钟）")

        # ---- 3. 找到 .sln 文件 ----
        sln_path = self._find_sln(project_dir, project_name)

        # ---- 4. 打开 .sln ----
        if do_open_sln:
            if not sln_path:
                return ActionResult(False, f"[{label}] 未找到 .sln 文件（生成可能失败），路径: {project_dir}")
            self._log(f"  → 正在打开 Visual Studio: {sln_path.name}")
            os.startfile(str(sln_path))
            logs.append(f"已打开 {sln_path.name}")

        # ---- 5. 编译 ----
        if do_build:
            self._log(f"  → 正在编译 [{build_config}|{build_platform}]，这可能需要几分钟...")

            # 优先用 UBT 直接编译（比 MSBuild /t:Target 更可靠）
            ubt = self._find_ubt(engine_path)
            if ubt:
                # UBT 编译目标格式：TargetName Platform Configuration -Project=xxx
                target_name = f"{project_name}Editor" if "Editor" in build_config else project_name
                config_name = build_config.replace(" Editor", "").strip()  # "Development Editor" → "Development"
                build_cmd = [
                    str(ubt),
                    target_name,
                    build_platform,
                    config_name,
                    f"-Project={uproject_path}",
                    "-NoHotReload",
                ]
                timeout = 1800
            else:
                # 降级到 MSBuild
                msbuild = self._find_msbuild(msbuild_path)
                if not msbuild:
                    return ActionResult(False, f"[{label}] 未找到 UBT 或 MSBuild，无法编译")
                if not sln_path:
                    return ActionResult(False, f"[{label}] 未找到 .sln 文件，无法编译")
                # MSBuild 不用 /t:Target，直接 Build 整个 sln
                build_cmd = [
                    str(msbuild),
                    str(sln_path),
                    f"/p:Configuration={build_config}",
                    f"/p:Platform={build_platform}",
                    "/m", "/nologo", "/verbosity:minimal",
                ]
                timeout = 1800

            try:
                result = subprocess.run(
                    build_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                )
                output = (result.stdout + result.stderr).strip()
                if result.returncode != 0:
                    return ActionResult(False, f"[{label}] 编译失败 (code {result.returncode})", output)
                logs.append(f"编译成功 [{build_config}|{build_platform}]")
                self._log(f"  ✅ 编译完成")
            except subprocess.TimeoutExpired:
                return ActionResult(False, f"[{label}] 编译超时（>30分钟）")

        # ---- 6. 启动 UE Editor（本地调试模式）----
        if do_launch_editor:
            editor_exe = self._find_ue_editor(engine_path)
            if not editor_exe:
                return ActionResult(False, f"[{label}] 未找到 UE Editor 可执行文件，请检查引擎目录")
            self._log(f"  → 正在启动 UE Editor...")
            # -game 是游戏模式，不加则是编辑器模式；加 -debug 会等待调试器附加
            launch_cmd = [str(editor_exe), uproject_path]
            subprocess.Popen(launch_cmd)
            logs.append("已启动 UE Editor")
            self._log(f"  ✅ UE Editor 已启动")

        summary = " → ".join(logs) if logs else "操作完成"
        return ActionResult(True, f"[{label}] {summary}")

    # ---- UE 辅助：查找 UAT 脚本 ----
    def _find_uat(self, engine_path: str, uproject_path: str) -> Optional[Path]:
        """查找 Generate 入口：优先 GenerateProjectFiles.bat，找不到则找 UnrealBuildTool.exe"""

        def _bat_candidates(root: Path):
            return [
                root / "Engine" / "Build" / "BatchFiles" / "GenerateProjectFiles.bat",
                root / "Build" / "BatchFiles" / "GenerateProjectFiles.bat",
            ]

        # 1. 用户指定引擎目录
        if engine_path:
            for c in _bat_candidates(Path(engine_path)):
                if c.exists():
                    return c
            # 同目录下找 UBT.exe
            ubt = Path(engine_path) / "Engine" / "Binaries" / "DotNET" / "AutomationTool" / "UnrealBuildTool.exe"
            if ubt.exists():
                return ubt

        # 2. 从 .uproject 向上找 bat
        check = Path(uproject_path).parent
        for _ in range(6):
            for c in _bat_candidates(check):
                if c.exists():
                    return c
            check = check.parent

        # 3. 常见安装路径
        for root in [r"C:\Program Files\Epic Games", r"D:\Program Files\Epic Games", r"E:\Program Files\Epic Games"]:
            matches = sorted(glob.glob(
                os.path.join(root, "UE_*", "Engine", "Build", "BatchFiles", "GenerateProjectFiles.bat")
            ), reverse=True)
            if matches:
                return Path(matches[0])

        # 4. 从引擎目录找 UBT.exe（源码版/腾讯版）
        search_root = Path(engine_path) if engine_path else Path(uproject_path).parent.parent
        for rel in [
            "Engine/Binaries/DotNET/AutomationTool/UnrealBuildTool.exe",
            "Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe",
        ]:
            p = search_root / rel
            if p.exists():
                return p

        return None

    # ---- UE 辅助：查找 UE Editor 可执行文件 ----
    def _find_ue_editor(self, engine_path: str) -> Optional[Path]:
        """查找 UnrealEditor.exe 或 UE4Editor.exe"""
        if not engine_path:
            return None
        root = Path(engine_path)
        candidates = [
            root / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe",   # UE5
            root / "Engine" / "Binaries" / "Win64" / "UE4Editor.exe",      # UE4
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    # ---- UE 辅助：专门查找 UBT 用于编译 ----
    def _find_ubt(self, engine_path: str) -> Optional[Path]:
        """查找 UnrealBuildTool.exe，用于编译目标"""
        candidates = []
        if engine_path:
            root = Path(engine_path)
            candidates = [
                root / "Engine" / "Binaries" / "DotNET" / "AutomationTool" / "UnrealBuildTool.exe",
                root / "Engine" / "Binaries" / "DotNET" / "UnrealBuildTool" / "UnrealBuildTool.exe",
            ]
        for p in candidates:
            if p.exists():
                return p
        return None

    # ---- UE 辅助：查找 .sln ----
    def _find_sln(self, project_dir: Path, project_name: str) -> Optional[Path]:
        """在项目目录查找 .sln 文件，优先匹配项目同名"""
        # 优先：项目名.sln
        named = project_dir / f"{project_name}.sln"
        if named.exists():
            return named
        # 次选：目录下任意 .sln
        slns = list(project_dir.glob("*.sln"))
        if slns:
            return slns[0]
        return None

    # ---- UE 辅助：查找 MSBuild ----
    def _find_msbuild(self, msbuild_path: str) -> Optional[Path]:
        """查找 MSBuild.exe"""
        if msbuild_path:
            p = Path(msbuild_path)
            if p.exists():
                return p

        # vswhere 查找（最可靠）
        vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
        if vswhere.exists():
            try:
                result = subprocess.run(
                    [str(vswhere), "-latest", "-requires", "Microsoft.Component.MSBuild",
                     "-find", r"MSBuild\**\Bin\MSBuild.exe"],
                    capture_output=True, text=True, timeout=10
                )
                line = result.stdout.strip().splitlines()
                if line:
                    p = Path(line[0].strip())
                    if p.exists():
                        return p
            except Exception:
                pass

        # 常见固定路径
        candidates = [
            r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return Path(c)

        # 最后尝试 PATH
        try:
            result = subprocess.run(["where", "MSBuild"], capture_output=True, text=True, timeout=5)
            line = result.stdout.strip().splitlines()
            if line:
                return Path(line[0].strip())
        except Exception:
            pass

        return None

    # ---- UE 辅助：确保 UBT 目录下有 System.CodeDom.dll（lib/net8.0/ 子目录）----
    def _ensure_ubt_codedom_dll(self, gen_script: Path) -> None:
        """
        UBT 动态编译 *.Build.cs 时会 Assembly.Load("System.CodeDom")，
        .NET 运行时按 deps.json 登记的相对路径 lib/net8.0/System.CodeDom.dll
        构建 TPA 列表。部分腾讯源码版 UE 缺失这个子目录/文件，导致
        FileNotFoundException: System.CodeDom。此处做前置自动修复。

        仅当 gen_script 是 UnrealBuildTool.exe 时处理；bat 模式无需。
        """
        try:
            if gen_script.suffix.lower() != ".exe":
                return
            if gen_script.name.lower() != "unrealbuildtool.exe":
                return
            ubt_dir = gen_script.parent
            target = ubt_dir / "lib" / "net8.0" / "System.CodeDom.dll"
            if target.exists() and target.stat().st_size > 100 * 1024:
                return  # 已存在且大小合理（>100KB），跳过

            # 在本机 .NET 8 SDK 里找一份 System.CodeDom.dll
            src = self._locate_system_codedom_dll()
            if not src:
                self._log("  ⚠️ 未找到 System.CodeDom.dll 源文件（需要 .NET 8 SDK），跳过自动补齐")
                return

            target.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(str(src), str(target))
            self._log(f"  🔧 已自动补齐 System.CodeDom.dll → {target}")
        except Exception as e:
            # 前置修复失败不阻断主流程，继续走后面的 UBT 调用
            self._log(f"  ⚠️ System.CodeDom.dll 自动补齐失败: {e}")

    @staticmethod
    def _locate_system_codedom_dll() -> Optional[Path]:
        """
        从本机 .NET 8 SDK 里定位 System.CodeDom.dll。
        优先 dotnet sdk 根目录（直接存在），再兜底到 NuGet 包缓存。
        """
        # 1. dotnet SDK 根目录：C:\Program Files\dotnet\sdk\<ver>\System.CodeDom.dll
        sdk_roots = [
            Path(r"C:\Program Files\dotnet\sdk"),
            Path(r"C:\Program Files (x86)\dotnet\sdk"),
        ]
        for root in sdk_roots:
            if not root.exists():
                continue
            # 取版本号最高的一个 SDK 目录
            sdk_dirs = sorted(
                [d for d in root.iterdir() if d.is_dir() and d.name[:1].isdigit()],
                key=lambda d: d.name,
                reverse=True,
            )
            for d in sdk_dirs:
                cand = d / "System.CodeDom.dll"
                if cand.exists() and cand.stat().st_size > 100 * 1024:
                    return cand

        # 2. NuGet 包缓存兜底
        nuget_roots = [
            Path.home() / ".nuget" / "packages" / "system.codedom",
            Path(r"C:\Program Files (x86)\Microsoft SDKs\NuGetPackages\system.codedom"),
        ]
        for root in nuget_roots:
            if not root.exists():
                continue
            matches = list(root.glob("*/lib/net*/System.CodeDom.dll"))
            matches.sort(key=lambda p: p.stat().st_size, reverse=True)
            for p in matches:
                if p.stat().st_size > 100 * 1024:
                    return p
        return None

    # ---- UE 辅助：诊断 UBT 生成/编译失败 ----
    @staticmethod
    def _diagnose_ubt_error(output: str) -> str:
        """根据 UBT 输出匹配已知环境问题，返回可执行的修复提示。找不到则返回空串。"""
        if not output:
            return ""
        low = output.lower()
        # .NET 运行时缺少 System.CodeDom 等程序集（典型为未装 .NET SDK 或 UBT\lib\net8.0 目录缺失）
        if "system.codedom" in low or "could not load file or assembly" in low:
            return ("UBT 动态编译缺少 System.CodeDom.dll。AutoTasker 已在 Generate 前自动补齐，"
                    "若仍然失败请手动执行：\n"
                    "  1) `dotnet --list-sdks` 确认已装 .NET 8 SDK (x64)；\n"
                    "  2) 把 SDK 下 System.CodeDom.dll 复制到 "
                    "`<UE>/Engine/Binaries/DotNET/UnrealBuildTool/lib/net8.0/`（目录不存在则先创建）。")
        if "the sdk 'microsoft.net.sdk' specified could not be found" in low or "a compatible .net sdk was not found" in low:
            return "未检测到 .NET SDK，请安装 .NET 8 SDK (x64)。"
        if "vswhere" in low and "not found" in low:
            return "未找到 Visual Studio 安装，请先安装 VS 2022 并勾选 C++ / .NET 桌面工作负载。"
        return ""

    # ---- 执行整个任务（按序执行所有 actions）----
    def execute_task(
        self,
        task: Dict[str, Any],
        on_done: Optional[Callable[[bool, str], None]] = None,
        async_run: bool = True,
        as_admin: bool = False,
    ):
        def _run():
            name = task.get("name", "未命名任务")
            actions: List[Dict] = task.get("actions", [])
            admin_tag = " 🛡[管理员]" if as_admin else ""
            self._log(f"\n{'='*40}")
            self._log(f"▶ 开始执行任务: {name}{admin_tag}")
            self._log(f"{'='*40}")

            if not actions:
                msg = f"任务 [{name}] 没有配置任何操作"
                self._log(msg)
                if on_done:
                    on_done(False, msg)
                return

            all_ok = True
            for i, action in enumerate(actions, 1):
                step_label = action.get('label') or action.get('type')
                self._log(f"\n[步骤 {i}/{len(actions)}] {step_label}")
                # 步骤级启用开关：未启用则跳过
                if not action.get("enabled", True):
                    self._log(f"⏭️  已跳过（步骤未启用）")
                    continue
                result = self.execute_action(action, as_admin=as_admin)
                self._log(str(result))
                if result.output:
                    # 只显示前 30 行输出
                    lines = result.output.splitlines()
                    preview = "\n".join(lines[:30])
                    if len(lines) > 30:
                        preview += f"\n... (共 {len(lines)} 行，已截断)"
                    self._log(preview)
                if not result.success:
                    all_ok = False
                    self._log(f"⚠️ 步骤失败，继续执行后续操作...")

            final_msg = f"✅ 任务 [{name}] 完成" if all_ok else f"⚠️ 任务 [{name}] 完成（有步骤失败）"
            self._log(f"\n{final_msg}")
            if on_done:
                on_done(all_ok, final_msg)

        if async_run:
            t = threading.Thread(target=_run, daemon=True)
            t.start()
        else:
            _run()
