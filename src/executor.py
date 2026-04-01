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

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                return ActionResult(True, f"[{label}] P4 Sync 成功: {depot_path}", output)
            else:
                return ActionResult(False, f"[{label}] P4 Sync 失败 (code {result.returncode})", output)
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
                return ActionResult(False, f"[{label}] P4 登录失败（密码错误？）: {output}")
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
                    return ActionResult(False, f"[{label}] Generate VS Files 失败 (code {result.returncode})", output)
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
                self._log(f"\n[步骤 {i}/{len(actions)}] {action.get('label') or action.get('type')}")
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
