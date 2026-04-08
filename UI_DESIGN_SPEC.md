# AutoTasker UI 设计规范文档

> 本文档描述 AutoTasker（任务自动化桌面工具）的完整 UI 设计规范，  
> 供 AI 或开发者参考，用于优化或复刻同风格工具。

---

## 一、整体设计哲学

### 设计原则
- **Less is More**：用背景层次和空间代替边框，减少视觉噪音
- **层次即信息**：通过背景色深浅（bg → panel → card → card_hover）区分内容层级，而非用线条
- **唯一聚焦**：全局只保留一处有边框的元素（搜索框），其余元素无边框
- **无系统 UI**：窗口、对话框全部无边框（FramelessWindowHint），自定义标题栏，保持品牌一致性

### 设计参考
- 暗色系：Linear App、VS Code、Raycast、Arc Browser
- 浅色系：Figma、Linear Light
- 极简灰：Vercel Dashboard、Arc
- 暖色系：Obsidian Minimal、Bear Notes

---

## 二、窗口与布局

### 主窗口
```
最小尺寸：860 × 580 px
默认尺寸：1080 × 700 px
窗口类型：FramelessWindowHint（无系统标题栏）
```

### 整体结构（从上到下）
```
┌──────────────────────────────────────────────┐
│  Header（56px 高）                            │
│  [LOGO 28px] [AutoTasker]  [搜索框]  [🎨][—][✕] │
├──────────────────────────────────────────────┤
│  Body（padding: 20px 水平, 16px 垂直）         │
│  ┌─────── 任务区（可滚动）─────────────────┐  │
│  │  ⭐ 常用任务  2个                        │  │
│  │  [卡片][卡片][卡片]...                   │  │
│  │  ────────── 分隔线（半透明 55%）─────── │  │
│  │  🎨 美术工具  4个                        │  │
│  │  [卡片][卡片]...                         │  │
│  └─────────────────────────────────────────┘  │
│  ┌──── 底部操作栏（54px 高，圆角 10px）────┐  │
│  │ [任务名]  描述文字  │  [▶执行][✏编辑][删除][📋日志] │
│  └─────────────────────────────────────────┘  │
│  （可折叠日志区，默认隐藏）                     │
└──────────────────────────────────────────────┘
```

### Header 布局
```
高度：56px
内边距：左16px，右8px，上下居中
内容：
  - LOGO 图标：28×28px（圆角方形）
  - 标题文字："AutoTasker"  font-size:16px, font-weight:bold
  - 弹性间距
  - 搜索框：宽220px，高32px，圆角18px（胶囊型）
  - 弹性间距
  - 状态文字："就绪"  color:text2, font-size:12px
  - 主题切换按钮🎨：32×32px，透明背景
  - 间距 4px
  - 最小化按钮 —：32×32px，透明背景
  - 关闭按钮 ✕：32×32px，悬停变危险红色
```

### 拖动支持
```
- 拖动区域：整个 Header 区域
- 实现：mousePressEvent 记录偏移，mouseMoveEvent 移动窗口
```

---

## 三、任务卡片（TaskCard）

### 尺寸
```
卡片大小：90 × 104 px
图标大小：52 × 52 px
内边距：6px 左右，8px 上，6px 下
间距：4px（图标与文字）
网格间距：10px
```

### 图标规则（核心设计）
```
优先级：
  1. 任务自定义图标（builtin:key 或本地文件路径）
  2. 从 action 配置的 exe/lnk/path 提取系统图标
  3. 回退：文字首字母图标（渐变底色 + 白色大字）

有真实图标时：
  - 直接显示系统图标，裁成圆角矩形（圆角比例 20%）
  - 卡片背景透明，不画底色
  - 悬停时淡显背景（rgba(255,255,255,14)）
  - 选中时淡显背景（rgba(255,255,255,28)）+ 底部白色细线

无真实图标时（文字图标）：
  - 绘制渐变底色（主色 → lighter(140%)，左上到右下）
  - 圆角比例：22%
  - 白色大字，字号 size//3，Bold
  - 卡片始终显示背景色（card → card_hover）
```

### 选中态
```
颜色：中性浅灰白（rgba 而非 accent 色）
有真实图标：rgba(255,255,255,28) 背景 + rgba(255,255,255,60) 1px 边框
纯文字图标：card.lighter(135%) 背景 + rgba(255,255,255,80) 1px 边框
底部光条：rgba(255,255,255,50)，宽 w-24，高 2px，圆角 1px
```

### 右键菜单功能
```
📂 移动到分类  →  子菜单列出所有分类
🖼 设置图标    →  子菜单（12个内置图标 + 本地文件 + 清除）
──────────────
▶ 立即执行
🛡 以管理员身份运行
✏ 编辑
──────────────
🗑 删除
```

### 分类分区标题
```
emoji + 分类名（font-size:12px, font-weight:bold）
颜色：第一个分区用 accent 色，其余用 text2 色
分区分隔线：border 色 55% 透明，1px，上下间距各 4px
空分类时显示虚线占位框（height:72px, border: 2px dashed border色）
```

---

## 四、底部操作栏

```
高度：54px，圆角：10px
背景色：panel
内边距：左16px，右12px，上下居中

内容（从左到右）：
  任务名（font-size:14px, bold, color:text）
  步骤描述（font-size:11px, color:text2，flex:1）
  间距 8px
  [▶ 执行]   accent 色实心，圆角7px，7×18px padding，白色文字
  [✏ 编辑]   透明背景，color:text2，悬停 card_hover
  [删除]     透明背景，color:danger，悬停 danger/18 背景
  [📋 日志]  透明背景，color:text2，可切换（展开/收起日志）
```

### 日志区
```
默认：隐藏
展开触发：点击「日志」按钮，或任务开始执行时自动展开
高度：固定 160px
背景：log_bg（比 bg 更深）
字体：Consolas / JetBrains Mono，12px
行颜色规则：
  - ✅ 成功/完成 → #22c55e
  - ❌ 失败/错误 → #ef4444
  - ⚠️ 警告     → #f59e0b
  - ▶ 开始执行  → #7c6aff
  - ℹ️ 步骤/信息 → #38bdf8
  - 分隔线符号  → #383860
  - 其他        → #8888aa
```

---

## 五、字体系统

```
主字体（UI）：
  首选："Microsoft YaHei UI"（微软雅黑 UI）
  回退："Segoe UI", sans-serif

代码/日志字体：
  首选："Consolas"
  回退："JetBrains Mono", monospace

Emoji 字体：
  "Segoe UI Emoji"（Windows 系统内置）

字号规范：
  标题（窗口/对话框）：16px, bold
  分区标题：12px, bold
  主要内容：13px, weight:500
  任务名（底部栏）：14px, bold
  卡片文字：10px
  步骤描述/副文本：11px
  日志：12px
  时间戳/提示：11px

行高：默认系统行高，日志区适当加宽
字间距：标题 letter-spacing: 0.5px
```

---

## 六、颜色系统（主题）

所有颜色通过主题字典动态注入，结构如下：

```python
theme = {
    "bg":         "",  # 窗口最底层背景
    "panel":      "",  # header、detail 面板背景（略亮于 bg）
    "card":       "",  # 按钮、输入框、卡片背景（略亮于 panel）
    "card_hover": "",  # hover/active 状态（略亮于 card）
    "border":     "",  # 分隔线颜色（极低饱和度）
    "accent":     "",  # 主强调色（执行按钮、选中状态、分区标题）
    "accent2":    "",  # 次强调色（新建按钮）
    "danger":     "",  # 危险/删除颜色
    "warn":       "",  # 警告颜色
    "text":       "",  # 主要文字颜色
    "text2":      "",  # 次要/占位符文字（低对比度）
    "log_bg":     "",  # 日志区背景
    "log_text":   "",  # 日志文字颜色
    "is_light":   bool # 是否为浅色主题（影响按钮文字色）
}
```

### 五套内置主题

#### 🌌 暗夜（默认，参考 Linear / VS Code Dark+）
```
bg:         #111318  近黑，略带蓝调
panel:      #1c1e26
card:       #22252f
card_hover: #2a2e3a
border:     #32374a
accent:     #6d8ff5  柔和蓝紫
accent2:    #56c9a0  薄荷绿
danger:     #e05c6e
text:       #d4d8f0
text2:      #5c6485
log_bg:     #0c0e13
log_text:   #9098c0
```

#### 🌊 深海（参考 Notion Dark / Raycast）
```
bg:         #0e1420  深蓝墨水
panel:      #141d30
card:       #1a2540
card_hover: #1f2d4d
border:     #273558
accent:     #4b9cf5  清澈蓝
accent2:    #38c9b8  青绿
danger:     #e05a6b
text:       #c8d8f5
text2:      #445a85
log_bg:     #090e1a
log_text:   #7090c8
```

#### 🪨 石墨（参考 Arc / Vercel Dashboard）
```
bg:         #141414  中性纯黑灰
panel:      #1c1c1c
card:       #242424
card_hover: #2c2c2c
border:     #363636
accent:     #a78bfa  淡紫
accent2:    #34d399  绿
danger:     #f87171
text:       #e2e2e2
text2:      #6b6b6b
log_bg:     #0e0e0e
log_text:   #888888
```

#### ☀️ 曙光（浅色，参考 Figma / Linear Light）
```
is_light:   True
bg:         #f4f5f7  浅灰白
panel:      #ffffff
card:       #ffffff
card_hover: #f0f1f5
border:     #e2e4ec
accent:     #4f6ef7  饱和蓝
accent2:    #10b981  翠绿
danger:     #e53e3e
text:       #1a1d2e  深墨蓝字
text2:      #64748b  灰蓝副文本
log_bg:     #f8f9fb
log_text:   #374151
```

#### 🌸 玫瑰（参考 Obsidian Minimal / Bear Notes）
```
bg:         #13100f  暖棕暗底
panel:      #1d1614
card:       #261e1c
card_hover: #2e2420
border:     #3d2f2b
accent:     #f472b6  粉红
accent2:    #fb923c  橙
danger:     #ef4444
text:       #f5e8e4
text2:      #8a6a65
log_bg:     #0e0b0a
log_text:   #c4a09a
```

---

## 七、按钮设计规范

### 层级体系（从强到弱）
```
1. 主操作按钮（▶ 执行）
   背景：accent 实心
   文字：#ffffff
   圆角：7px
   padding：7px 18px
   weight：600

2. 正向操作按钮（＋ 新建、保存任务）
   背景：accent2/22（22% 不透明度背景）
   文字：accent2
   圆角：7px
   weight：600

3. 通用操作按钮（编辑、分类、日志）
   背景：transparent（完全透明）
   文字：text2
   悬停：card_hover 背景，text 文字
   圆角：7px

4. 危险操作按钮（删除）
   背景：transparent
   文字：danger 色
   悬停：danger/18 背景
   无边框

5. 窗口控制按钮（— 最小化、✕ 关闭）
   背景：transparent
   文字：text2
   关闭悬停：danger 背景 + #ffffff 文字
   尺寸：32×32px
```

### 统一规则
```
- 所有按钮：border: none（无边框）
- 圆角：7px（统一）
- 禁用状态：color text2/55 透明度，背景透明
- 状态变化：仅背景色变化，无边框变化
```

---

## 八、输入框与表单

```
通用输入框：
  背景：card
  聚焦：card_hover（背景变化，无边框描边）
  圆角：6px
  padding：5px 10px
  border：none

搜索框（例外）：
  border：1.5px solid border色
  聚焦：border-color → accent/99
  圆角：18px（胶囊型）
  padding：6px 14px 6px 34px（左留空给图标）

ComboBox（下拉框）：
  同通用输入框
  下拉面板背景：panel
  选中项：card_hover

CheckBox：
  indicator 尺寸：15×15px
  未选中：border 1.5px，背景 card
  选中：accent 实心填充，accent 边框
  圆角：4px
```

---

## 九、菜单与弹窗

### 右键菜单
```
背景：panel
边框：border/66（40% 透明，极轻）
圆角：10px
padding：5px 3px
item padding：7px 20px 7px 14px
item 圆角：6px
item margin：1px 3px
悬停：card_hover 背景，text 文字
分隔线：border/66，1px，margin 3px 10px
```

### 对话框（编辑任务、管理分类等）
```
窗口类型：FramelessWindowHint
自定义标题栏：44px 高，panel 背景，可拖动
关闭按钮：右上角 30×30px，同主窗口关闭按钮样式

对话框内容区：
  背景：bg
  padding：16px 水平，12px 垂直
  内容间距：10px

任务编辑器尺寸：800 × 600px（最小 700 × 520px）
分类管理器尺寸：440 × 420px（最小）
```

---

## 十、滚动条

```
宽度：3px（极细）
背景：transparent（不显示轨道）
handle 背景：border 色
handle 悬停：text2 色
最小长度：20px
两端箭头：隐藏（height:0）
```

---

## 十一、Logo 设计规范

### 生成方法（代码绘制，无外部图片依赖）

#### 整体结构
```
尺寸：256 × 256px（生成多尺寸：16/32/64/128/256）
形状：圆角正方形，圆角半径 18%（约 46px）
```

#### 背景层
```
渐变方向：左上 → 右下（QLinearGradient）
渐变色：
  stop:0.0  #1a1b2e（深蓝紫）
  stop:0.5  #0d0e1a（近黑）
  stop:1.0  #0a0b14（极深蓝）
```

#### 内发光层（叠加）
```
类型：径向渐变（QRadialGradient），圆心 (50%, 45%)，半径 42%
颜色：
  stop:0.0  rgba(122,162,247, 55)（蓝色光晕）
  stop:0.6  rgba(122,162,247, 20)
  stop:1.0  rgba(122,162,247, 0)
```

#### 边框描边
```
类型：线性渐变描边
宽度：1.6%（约 4px）
渐变：
  stop:0.0  rgba(122,162,247, 180)（亮蓝）
  stop:0.5  rgba(158,206,106, 120)（亮绿）
  stop:1.0  rgba(122,162,247, 80)（淡蓝）
```

#### 闪电主体（核心图形）
```
颜色渐变（顶→底）：
  stop:0.0  #a0c4ff（淡蓝白）
  stop:0.35 #7aa2f7（蓝紫）
  stop:0.7  #9ece6a（黄绿）
  stop:1.0  #73c991（薄荷绿）

形状（相对于尺寸 S 的坐标比例）：
  上半段：
    顶部右点  (cx+0.04S, 0.15S)
    中间左点  (cx-0.14S, 0.48S)
    中间右点  (cx+0.04S, 0.48S)   ← 折点
  下半段：
    底部左点  (cx-0.04S, 0.85S)
    中间右点  (cx+0.16S, 0.52S)
    中间左点  (cx-0.02S, 0.52S)   ← 折点
  （cx = S × 0.5 为水平中心）

高光：
  闪电顶部区域叠加 rgba(255,255,255,60) 白色三角形光泽
```

#### 右下角完成标记
```
形状：实心圆
位置：(0.76S, 0.76S)，半径 0.095S
颜色：径向渐变
  stop:0.0  #9ece6a（黄绿）
  stop:0.6  #73c991（绿）
  stop:1.0  #4a9e6a（深绿）
圆内：白色对勾（✓），线宽 0.022S，RoundCap，粗线

对勾坐标（相对圆心）：
  起点：(-0.45r, 0)
  中点：(-0.1r, +0.38r)
  终点：(+0.5r, -0.35r)
```

#### 暗角层（最终叠加）
```
类型：径向渐变，从中心向外
  stop:0.0  rgba(0,0,0, 0)
  stop:0.75 rgba(0,0,0, 0)
  stop:1.0  rgba(0,0,0, 60)（边角压暗）
```

---

## 十二、分类系统

### 数据结构
```json
{
  "id": "uuid-string",
  "name": "美术工具",
  "emoji": "🎨",
  "order": 1
}
```

### 视觉规则
```
- 每个分类有独立区域，标题 + 任务卡片网格
- 分类顺序可拖拽调整（在管理面板）
- 空分类显示虚线占位框（提示可拖入）
- 卡片跨分类拖拽：拖到目标分区落点即转移
```

### 内置 Emoji 图标池（20个）
```
⭐ 📋 🎨 🛠 🎮 📁 🚀 🔧 💡 📦
🌐 🎬 📷 🖥 🔥 ⚡ 🎯 💻 🗂 📌
```

---

## 十三、动效与交互

```
悬停响应：仅背景色变化，无位移/缩放/渐变动画（保持克制）
选中卡片：背景淡显，底部短横线
主题切换：即时刷新（调用 setStyleSheet 重新注入样式表）
日志展开：显示/隐藏切换，无动画（直接 setVisible）
窗口拖动：跟手移动，无弹性/摩擦
```

---

## 十四、技术栈

```
语言：Python 3.12
UI 框架：PyQt6
主要组件：QMainWindow, QDialog, QWidget, QListWidget
绘图：QPainter（纯代码绘制图标、Logo、卡片效果）
打包：PyInstaller --onefile --windowed
图标提取：QFileIconProvider（获取 .exe/.lnk 系统图标）
配置存储：JSON，路径 %APPDATA%\AutoTasker\
```

---

## 十五、文件结构

```
AutoTasker/
├── src/
│   ├── app.py              # 入口
│   ├── main_window.py      # 主窗口（主题、卡片、网格）
│   ├── task_editor.py      # 编辑对话框
│   ├── executor.py         # 执行引擎
│   ├── scheduler.py        # 定时调度
│   └── config_manager.py   # 配置持久化
├── assets/
│   ├── logo.png            # 256px LOGO
│   ├── logo_32.png         # 32px
│   ├── logo_64.png         # 64px
│   ├── logo_128.png        # 128px
│   └── logo.ico            # EXE 图标
└── dist/
    └── AutoTasker.exe      # 打包输出（~38MB）
```

---

*文档版本：2026-04-08 | 基于 AutoTasker v1.x*
