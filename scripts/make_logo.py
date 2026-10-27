"""
make_logo.py - draws the "EstateIQ" logo (PNG + SVG) with matplotlib.
Concept: a rounded navy->teal badge, a skyline of buildings whose roofline
rises like a growth chart, topped by a gold up-arrow (investment growth).
Run:  python scripts/make_logo.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon, Circle

ASSETS = Path(__file__).resolve().parents[1] / "assets"
NAVY, TEAL, GOLD, WHITE = "#0B1F3A", "#14B8A6", "#F5B83D", "#FFFFFF"


def draw_mark(ax):
    """Draw the square badge mark in a 0-100 coordinate space."""
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal"); ax.axis("off")
    # gradient background clipped to a rounded square
    grad = np.linspace(0, 1, 256).reshape(-1, 1) * np.ones((1, 256))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("b", [NAVY, "#16325C", "#0F766E"])
    bg = FancyBboxPatch((2, 2), 96, 96, boxstyle="round,pad=0,rounding_size=22",
                        fc="none", ec="none")
    ax.add_patch(bg)
    im = ax.imshow(grad, extent=(2, 98, 2, 98), cmap=cmap, origin="upper", zorder=0)
    im.set_clip_path(bg)
    # skyline: building (x, width, height) - heights rise left to right
    builds = [(23, 12, 26), (37, 12, 38), (51, 12, 50), (65, 12, 62)]
    for i, (x, w, h) in enumerate(builds):
        col = WHITE if i % 2 == 0 else "#BFEFE9"
        ax.add_patch(Rectangle((x, 16), w, h, fc=col, ec="none", zorder=2))
        # windows
        for wy in np.arange(22, 16 + h - 5, 9):
            for wx in (x + 2.5, x + 7):
                ax.add_patch(Rectangle((wx, wy), 2.6, 3.6, fc=NAVY, ec="none", alpha=.55, zorder=3))
    # base line
    ax.add_patch(Rectangle((17, 14), 70, 2.4, fc=TEAL, ec="none", zorder=2))
    # growth arrow above skyline
    ax.plot([21, 39, 51, 71], [58, 68, 76, 90], color=GOLD, lw=5.5, solid_capstyle="round",
            solid_joinstyle="round", zorder=4)
    ax.add_patch(Polygon([[65, 92], [81, 94], [73, 80]], closed=True, fc=GOLD, ec=GOLD,
                         lw=2, joinstyle="round", zorder=4))
    ax.add_patch(Circle((21, 58), 2.8, fc=GOLD, ec="none", zorder=4))


def main():
    ASSETS.mkdir(exist_ok=True)
    # 1) square icon
    fig, ax = plt.subplots(figsize=(4, 4), dpi=300)
    fig.patch.set_alpha(0); draw_mark(ax)
    fig.savefig(ASSETS / "logo_icon.png", transparent=True, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(ASSETS / "logo_icon.svg", transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    # 2) horizontal lockup: icon + wordmark (dark text, for light backgrounds)
    for variant, fg, sub in (("logo", NAVY, "#6B7A90"), ("logo_light", WHITE, "#BFD3EA")):
        fig = plt.figure(figsize=(8.4, 2.4), dpi=300)
        fig.patch.set_alpha(0)
        ax_i = fig.add_axes([0.0, 0.0, 0.285, 1.0]); draw_mark(ax_i)
        t1 = fig.text(0.31, 0.58, "Estate", fontsize=46, fontweight="bold", color=fg, va="center", ha="left")
        fig.canvas.draw()
        end_x = t1.get_window_extent().x1 / fig.bbox.width       # right edge of "Estate"
        fig.text(end_x + 0.008, 0.58, "IQ", fontsize=46, fontweight="bold", color=TEAL, va="center", ha="left")
        fig.text(0.315, 0.27, "REAL ESTATE INVESTMENT ADVISOR", fontsize=12.5, color=sub,
                 va="center", ha="left", fontweight="bold")
        fig.savefig(ASSETS / f"{variant}.png", transparent=True, bbox_inches="tight", pad_inches=0.05)
        fig.savefig(ASSETS / f"{variant}.svg", transparent=True, bbox_inches="tight", pad_inches=0.05)
        plt.close(fig)
    print("logos written to", ASSETS)


if __name__ == "__main__":
    main()
