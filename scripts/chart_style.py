"""Shared look for every chart in the project: colors, type, layout and bars."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

SURFACE = "#ffffff"
ACCENT = "#2a78d6"
MUTED_MARK = "#898781"
QUIET_MARK = "#c3c2b7"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#6f6e69"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

BAR_THICKNESS = 10
WIDTH_IN = 10
LEFT_IN = 0.45
HEADER_IN = 1.15
FOOTER_IN = 0.3
ROW_IN = 0.37

installed_fonts = {font.name for font in font_manager.fontManager.ttflist}

plt.rcParams.update({
    "font.family": next((name for name in ("Segoe UI", "Helvetica Neue", "Arial") if name in installed_fonts), "sans-serif"),
    "font.size": 11,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": BASELINE,
    "axes.linewidth": 0.8,
    "text.color": INK,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_SECONDARY,
})


def format_speedup(value):
    return f"{value:.0f}x" if value >= 10 else f"{value:.1f}x"


def format_ms(value):
    if value >= 1000:
        return f"{value / 1000:g} s"
    return f"{value:g} ms"


def chart_figure(rows, title, subtitle, footnote=None, label_in=2.6, right_in=0.9):
    """A figure with a left-aligned headline and one plot, sized to its rows."""
    footer = FOOTER_IN + (0.3 if footnote else 0)
    height = HEADER_IN + rows * ROW_IN + footer
    fig, ax = plt.subplots(figsize=(WIDTH_IN, height))
    fig.subplots_adjust(
        left=(LEFT_IN + label_in) / WIDTH_IN,
        right=1 - right_in / WIDTH_IN,
        top=1 - HEADER_IN / height,
        bottom=footer / height,
    )
    add_header(fig, height, title, subtitle)
    if footnote:
        fig.text(LEFT_IN / WIDTH_IN, 0.2 / height, footnote, fontsize=9.5, color=INK_MUTED)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=11, pad=8)
    return fig, ax


def add_header(fig, height, title, subtitle):
    fig.text(LEFT_IN / WIDTH_IN, 1 - 0.47 / height, title, fontsize=18, fontweight="semibold", color=INK)
    fig.text(LEFT_IN / WIDTH_IN, 1 - 0.76 / height, subtitle, fontsize=11.5, color=INK_SECONDARY)


def rounded_hbars(ax, labels, values, colors=ACCENT, value_labels=None, scale="linear",
                  baseline=0, x_max=None):
    """Horizontal bars, first row on top, with a rounded tip and a value beside it.

    The tip is pulled in by the cap radius so the rounded end stops exactly at
    the value, and the axes clip the cap at the baseline to leave it square.
    A value too small to fit a cap still draws one, so no bar disappears.
    """
    rows = len(values)
    positions = list(range(rows - 1, -1, -1))
    colors = [colors] * rows if isinstance(colors, str) else colors
    value_labels = value_labels or [f"{v:,}" for v in values]

    ax.set_xscale(scale)
    ax.set_xlim(baseline, x_max or max(values))
    ax.set_ylim(-0.6, rows - 0.4)
    ax.set_yticks(positions, labels)
    ax.xaxis.set_visible(False)

    radius_px = BAR_THICKNESS / 2 * ax.figure.dpi / 72
    for y, value, color, text in zip(positions, values, colors, value_labels):
        tip_px = ax.transData.transform((value, y))[0] - radius_px
        tip = max(ax.transData.inverted().transform((tip_px, 0))[0], value / 2 if baseline == 0 else baseline)
        ax.plot([baseline, tip], [y, y], color=color, linewidth=BAR_THICKNESS,
                solid_capstyle="round", zorder=3)
        ax.annotate(text, (value, y), xytext=(8, 0), textcoords="offset points",
                    va="center_baseline", fontsize=10.5, fontweight="semibold", color=INK,
                    annotation_clip=False)


def save_chart(fig, path):
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
