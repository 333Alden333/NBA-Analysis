"""NBA half-court drawing and shot chart visualization."""

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
import matplotlib.figure


def draw_court(ax=None, color="black", lw=2):
    """Draw an NBA half-court on a matplotlib Axes.

    Coordinates: hoop at (0, 0), court extends from
    x=(-250, 250), y=(-47.5, 422.5).

    Args:
        ax: Matplotlib Axes. If None, creates one.
        color: Line color for court markings.
        lw: Line width.

    Returns:
        The Axes with court drawn.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5.5))

    # Hoop
    hoop = Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False)
    ax.add_patch(hoop)

    # Backboard
    ax.plot([-30, 30], [-7.5, -7.5], linewidth=lw, color=color)

    # Paint (outer box)
    outer_box = Rectangle((-80, -47.5), 160, 190, linewidth=lw,
                          color=color, fill=False)
    ax.add_patch(outer_box)

    # Paint (inner box)
    inner_box = Rectangle((-60, -47.5), 120, 190, linewidth=lw,
                          color=color, fill=False)
    ax.add_patch(inner_box)

    # Free throw top arc
    top_free_throw = Arc((0, 142.5), 120, 120, theta1=0, theta2=180,
                         linewidth=lw, color=color, fill=False)
    ax.add_patch(top_free_throw)

    # Free throw bottom arc (dashed)
    bottom_free_throw = Arc((0, 142.5), 120, 120, theta1=180, theta2=360,
                            linewidth=lw, color=color, linestyle="dashed",
                            fill=False)
    ax.add_patch(bottom_free_throw)

    # Restricted area arc
    restricted = Arc((0, 0), 80, 80, theta1=0, theta2=180,
                     linewidth=lw, color=color)
    ax.add_patch(restricted)

    # Three-point line (arc)
    three_arc = Arc((0, 0), 475, 475, theta1=22, theta2=158,
                    linewidth=lw, color=color)
    ax.add_patch(three_arc)

    # Three-point corners
    ax.plot([-220, -220], [-47.5, 92.5], linewidth=lw, color=color)
    ax.plot([220, 220], [-47.5, 92.5], linewidth=lw, color=color)

    # Center court outer arc
    center_outer = Arc((0, 422.5), 120, 120, theta1=180, theta2=360,
                       linewidth=lw, color=color)
    ax.add_patch(center_outer)

    # Center court inner arc
    center_inner = Arc((0, 422.5), 40, 40, theta1=180, theta2=360,
                       linewidth=lw, color=color)
    ax.add_patch(center_inner)

    # Outer lines (half court boundary)
    ax.plot([-250, 250], [-47.5, -47.5], linewidth=lw, color=color)
    ax.plot([-250, 250], [422.5, 422.5], linewidth=lw, color=color)
    ax.plot([-250, -250], [-47.5, 422.5], linewidth=lw, color=color)
    ax.plot([250, 250], [-47.5, 422.5], linewidth=lw, color=color)

    ax.set_xlim(-250, 250)
    ax.set_ylim(422.5, -47.5)
    ax.set_aspect("equal")
    ax.axis("off")

    return ax


def shot_chart_figure(
    shots: list,
    title: str = "Shot Chart",
) -> matplotlib.figure.Figure:
    """Create a shot chart figure with court overlay and shot markers.

    Args:
        shots: List of dicts with loc_x, loc_y, shot_made keys.
            shot_made: True = made, False = missed.
        title: Chart title.

    Returns:
        Matplotlib Figure for use with st.pyplot(fig).
    """
    fig, ax = plt.subplots(figsize=(6, 5.5))
    draw_court(ax=ax)

    if not shots:
        ax.text(
            0, 200, "No shot data available",
            ha="center", va="center", fontsize=14, color="gray",
        )
        ax.set_title(title, fontsize=14, pad=10)
        return fig

    # Separate makes and misses
    made_x = [s["loc_x"] for s in shots if s.get("shot_made")]
    made_y = [s["loc_y"] for s in shots if s.get("shot_made")]
    miss_x = [s["loc_x"] for s in shots if not s.get("shot_made")]
    miss_y = [s["loc_y"] for s in shots if not s.get("shot_made")]

    if miss_x:
        ax.scatter(miss_x, miss_y, c="red", marker="x", s=30,
                   alpha=0.6, label="Miss", zorder=5)
    if made_x:
        ax.scatter(made_x, made_y, c="green", marker="o", s=30,
                   alpha=0.6, label="Make", zorder=5)

    ax.set_title(title, fontsize=14, pad=10)
    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    return fig
