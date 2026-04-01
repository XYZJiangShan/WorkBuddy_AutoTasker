"""
生成 AutoTasker 专业 LOGO（256x256 PNG）
运行：py tools/gen_logo.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QLinearGradient, QRadialGradient,
    QPainterPath, QPen, QBrush, QFont, QImage
)

app = QApplication(sys.argv)

SIZE = 256

def gen_logo(size=256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    s = size
    r = s * 0.18  # 圆角半径

    # ── 1. 背景：深邃渐变圆角矩形 ──
    bg_grad = QLinearGradient(0, 0, s, s)
    bg_grad.setColorAt(0.0, QColor("#1a1b2e"))
    bg_grad.setColorAt(0.5, QColor("#0d0e1a"))
    bg_grad.setColorAt(1.0, QColor("#0a0b14"))
    bg_path = QPainterPath()
    bg_path.addRoundedRect(QRectF(0, 0, s, s), r, r)
    p.fillPath(bg_path, QBrush(bg_grad))

    # ── 2. 内圈发光光晕 ──
    glow = QRadialGradient(s * 0.5, s * 0.45, s * 0.42)
    glow.setColorAt(0.0, QColor(122, 162, 247, 55))
    glow.setColorAt(0.6, QColor(122, 162, 247, 20))
    glow.setColorAt(1.0, QColor(122, 162, 247, 0))
    p.fillPath(bg_path, QBrush(glow))

    # ── 3. 边框：微光描边 ──
    border_grad = QLinearGradient(0, 0, s, s)
    border_grad.setColorAt(0.0, QColor(122, 162, 247, 180))
    border_grad.setColorAt(0.5, QColor(158, 206, 106, 120))
    border_grad.setColorAt(1.0, QColor(122, 162, 247, 80))
    pen = QPen(QBrush(border_grad), s * 0.016)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(s * 0.008, s * 0.008, s * 0.984, s * 0.984), r, r)

    # ── 4. 闪电符号（主体）──
    # 闪电路径：经典分段向下折角造型
    cx = s * 0.5
    bolt = QPainterPath()

    # 上半段（左倾斜往右下）
    pts_top = [
        QPointF(cx + s * 0.04,  s * 0.15),   # 顶部右
        QPointF(cx - s * 0.14,  s * 0.48),   # 中间左
        QPointF(cx + s * 0.04,  s * 0.48),   # 中间右（折点）
    ]
    # 下半段（继续向左下）
    pts_bot = [
        QPointF(cx - s * 0.04,  s * 0.85),   # 底部左
        QPointF(cx + s * 0.16,  s * 0.52),   # 中间右
        QPointF(cx - s * 0.02,  s * 0.52),   # 中间左（折点）
    ]

    bolt.moveTo(pts_top[0])
    bolt.lineTo(pts_top[1])
    bolt.lineTo(pts_top[2])
    bolt.lineTo(pts_bot[1])
    bolt.lineTo(pts_bot[0])
    bolt.lineTo(pts_bot[2])
    bolt.lineTo(pts_top[0])
    bolt.closeSubpath()

    # 闪电渐变：蓝→绿
    bolt_grad = QLinearGradient(cx - s*0.15, s*0.15, cx + s*0.15, s*0.85)
    bolt_grad.setColorAt(0.0, QColor("#a0c4ff"))
    bolt_grad.setColorAt(0.35, QColor("#7aa2f7"))
    bolt_grad.setColorAt(0.7, QColor("#9ece6a"))
    bolt_grad.setColorAt(1.0, QColor("#73c991"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(bolt_grad))
    p.drawPath(bolt)

    # ── 5. 闪电高光：顶部白色光泽 ──
    hi_path = QPainterPath()
    hi_path.moveTo(pts_top[0])
    hi_path.lineTo(pts_top[1])
    hi_path.lineTo(QPointF(pts_top[1].x() + s*0.04, pts_top[1].y()))
    hi_path.lineTo(QPointF(pts_top[0].x() + s*0.02, pts_top[0].y() + s*0.06))
    hi_path.closeSubpath()
    p.setBrush(QBrush(QColor(255, 255, 255, 60)))
    p.drawPath(hi_path)

    # ── 6. 右下角小圆圈：自动化/齿轮暗示 ──
    dot_cx = s * 0.76
    dot_cy = s * 0.76
    dot_r  = s * 0.095
    dot_grad = QRadialGradient(dot_cx, dot_cy, dot_r)
    dot_grad.setColorAt(0.0, QColor("#9ece6a"))
    dot_grad.setColorAt(0.6, QColor("#73c991"))
    dot_grad.setColorAt(1.0, QColor("#4a9e6a"))
    p.setBrush(QBrush(dot_grad))
    p.setPen(QPen(QColor("#1a2e1a"), s * 0.012))
    p.drawEllipse(QPointF(dot_cx, dot_cy), dot_r, dot_r)

    # 圆圈里画对勾
    check = QPainterPath()
    check.moveTo(dot_cx - dot_r*0.45, dot_cy)
    check.lineTo(dot_cx - dot_r*0.1,  dot_cy + dot_r*0.38)
    check.lineTo(dot_cx + dot_r*0.5,  dot_cy - dot_r*0.35)
    p.setPen(QPen(QColor("#ffffff"), s * 0.022, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(check)

    # ── 7. 整体蒙版：边缘渐暗，增加立体感 ──
    vignette = QRadialGradient(s*0.5, s*0.5, s*0.7)
    vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
    vignette.setColorAt(0.75, QColor(0, 0, 0, 0))
    vignette.setColorAt(1.0,  QColor(0, 0, 0, 60))
    mask_path = QPainterPath()
    mask_path.addRoundedRect(QRectF(0, 0, s, s), r, r)
    p.fillPath(mask_path, QBrush(vignette))

    p.end()
    return pm


# 生成不同尺寸
out_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
os.makedirs(out_dir, exist_ok=True)

for sz in [16, 32, 64, 128, 256]:
    pm = gen_logo(sz)
    path = os.path.join(out_dir, f'logo_{sz}.png')
    pm.save(path, 'PNG')
    print(f'[OK] {path}')

# 主图标（256）
main_path = os.path.join(out_dir, 'logo.png')
gen_logo(256).save(main_path, 'PNG')
print(f'[OK] main: {main_path}')

print('LOGO done!')
app.quit()
