# AutoTasker

日常操作自动化配置系统 - 基于 Python + PyQt6

## 功能特性

- ✅ **P4 同步** - 一键同步指定 Depot 路径资产
- ✅ **启动程序** - 打开任意软件/应用
- ✅ **打开路径** - 快速打开文件夹或文件
- ✅ **执行命令** - 运行任意 Shell 命令/脚本
- ✅ **任务组合** - 多个操作串联为一个任务
- ✅ **定时执行** - 设置定时自动运行
- ✅ **系统托盘** - 最小化到托盘，随时调用
- ✅ **执行日志** - 实时查看执行过程和结果

## 快速开始

### 直接运行
```
双击 启动AutoTasker.bat
```

### 打包成 EXE
```powershell
# 先安装打包工具
py -m pip install pyinstaller

# 执行打包
.\build.ps1
```

## 依赖

```
PyQt6
apscheduler
```

安装：`py -m pip install PyQt6 apscheduler`

## 配置文件位置

`%APPDATA%\AutoTasker\tasks.json`

## P4 配置说明

P4 操作需要系统已安装 Perforce 命令行客户端（p4.exe 在 PATH 中）。
可以在每个 P4 操作里单独配置连接信息，也可以通过系统环境变量设置：
- `P4PORT` - 服务器地址
- `P4USER` - 用户名  
- `P4CLIENT` - 工作区名称
