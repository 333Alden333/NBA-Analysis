#!/usr/bin/env python3
"""
NBA ANALYST — Hermes Agent-style CLI for NBA Analysis & Prediction
Hackathon submission for Nous Research using Hermes Agent framework.

Launch with: nba
"""

import os
import sys
import json
import shutil
import datetime
import time
import urllib.request
from pathlib import Path
from collections import defaultdict

# Set working directory to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Rich imports ────────────────────────────────────────────────────────────
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.table import Table
from rich import box
from rich.align import Align
from rich.style import Style

# ─── prompt_toolkit imports ──────────────────────────────────────────────────
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.styles import Style as PTStyle

# ─── pyfiglet ────────────────────────────────────────────────────────────────
import pyfiglet

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "NBA ANALYST"
APP_VERSION = "0.1.0"
APP_TAGLINE = "AI-Powered NBA Analysis & Prediction Platform"

# Resolve GIF path — check several locations
GIF_SEARCH_PATHS = [
    Path(__file__).parent / "nba_banner_v4.gif",
    Path(__file__).parent.parent / "data" / "nba_banner_v4.gif",
    Path(__file__).parent.parent / "assets" / "nba_banner_v4.gif",
    Path(__file__).parent.parent / "nba_banner_v4.gif",
    Path.home() / "HermesAnalysis" / "data" / "nba_banner_v4.gif",
    Path.home() / "HermesAnalysis" / "nba_banner_v4.gif",
]

# ANSI escape helpers
CSI = "\033["
CURSOR_UP = lambda n: f"{CSI}{n}A"
CURSOR_DOWN = lambda n: f"{CSI}{n}B"
CURSOR_COL = lambda n: f"{CSI}{n}G"
CLEAR_LINE = f"{CSI}2K"
HIDE_CURSOR = f"{CSI}?25l"
SHOW_CURSOR = f"{CSI}?25h"
RESET = f"{CSI}0m"

# Color palette (orange/amber/cyan — Hermes Agent style)
class Colors:
    ORANGE = "#FF8C00"
    AMBER = "#FFD700"
    CYAN = "#00CED1"
    BRIGHT_ORANGE = "#FF6600"
    DIM_ORANGE = "#CC7000"
    WHITE = "#FFFFFF"
    GRAY = "#888888"
    DIM = "#666666"
    BORDER = "#FF8C00"
    ACCENT = "#00CED1"
    MUTED = "#B8860B"

# Tools & Skills displayed in banner
TOOLS = [
    ("ELO Rankings", "Team strength ratings & rankings"),
    ("ML Predictions", "GBM model · 73.5% accuracy"),
    ("Pattern Engine", "Matchup classification system"),
    ("Player Stats", "Per-game & season averages"),
    ("Momentum", "Hot/cold streak detection"),
    ("Injury Intel", "Injury report integration"),
]

SKILLS = [
    ("nba_api", "Live NBA data pipeline"),
    ("scikit-learn", "Gradient Boosted Models"),
    ("SQLite", "Local game database"),
    ("pandas", "Statistical analysis"),
]

# Slash commands (all 18 tools + utilities)
COMMANDS = {
    "/elo": "ELO rankings with chart [--png]",
    "/games": "Recent game scores",
    "/predict": "Matchup prediction — /predict Celtics Lakers",
    "/odds": "Polymarket championship odds",
    "/teams": "List all NBA teams",
    "/player": "Player stats — /player Curry [--png]",
    "/team": "Team stats — /team Lakers [--png]",
    "/compare": "Compare players — /compare Curry vs LeBron [--png]",
    "/trend": "PPG trend — /trend Luka [--png]",
    "/top": "League leaders — /top pts|reb|ast|stl|blk|3pm [--png]",
    "/heatmap": "Stats correlation [--png]",
    "/shot": "Shot chart — /shot Curry [--png]",
    "/pattern": "Player vs team — /pattern Curry vs Lakers",
    "/matchup": "Matchup classification — /matchup LeBron vs Celtics",
    "/edge": "Betting edges (model vs market)",
    "/momentum": "Who's hot / who's cold",
    "/update": "Refresh ELO ratings",
    "/clear": "Clear screen and re-dashboard",
    "/help": "Show all commands & usage",
    "/quit": "Exit NBA Analyst",
}

HELP = """
=== NBA ANALYST v1.0.0 ===

Tools (prefix with /):
  elo         ELO rankings with chart (--png to save)
  games       Recent game scores
  predict     Matchup prediction: /predict Celtics Lakers
  odds        Polymarket championship odds
  teams       List all teams
  player      Player stats: /player Curry [--png]
  team        Team stats: /team Lakers [--png]
  compare     Compare players: /compare Curry vs LeBron [--png]
  trend       PPG trend: /trend Luka [--png]
  top         League leaders: /top pts|reb|ast|stl|blk|3pm [--png]
  heatmap     Stats correlation [--png]
  shot        Shot chart: /shot Curry [--png]
  pattern     Player vs team: /pattern Curry vs Lakers
  matchup     Matchup classification: /matchup LeBron vs Celtics
  edge        Betting edges (model vs market)
  momentum    Who's hot/cold
  update      Refresh ELO ratings

Utilities:
  help        Show this message
  clear       Clear screen and redashboard
  quit        Exit

Natural language:
  Just type a question without / to use AI:
  "who wins tonight?"
  "compare the top 3 teams"
"""

# ═══════════════════════════════════════════════════════════════════════════════
# GIF → HALF-BLOCK RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

# Content crop box for nba_banner_v4.gif (player silhouette region)
GIF_CROP = (40, 300, 290, 880)  # left, top, right, bottom
GIF_ART_WIDTH = 22  # characters wide
GIF_ART_LINES = 18  # lines tall (each line = 2 vertical pixels)


def find_gif_path() -> Path | None:
    """Search for the GIF file in known locations."""
    for p in GIF_SEARCH_PATHS:
        if p.exists():
            return p
    return None


def load_gif_frames(gif_path: Path, step: int = 2) -> list[list[str]]:
    """
    Load and pre-render GIF frames to half-block terminal art.

    Args:
        gif_path: Path to the GIF file
        step: Frame step (2 = every other frame, for speed)

    Returns:
        List of frames, each frame is a list of ANSI-colored strings
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return []

    gif = Image.open(gif_path)
    n_frames = getattr(gif, "n_frames", 1)
    duration_ms = gif.info.get("duration", 60)

    frames = []
    for i in range(0, n_frames, step):
        gif.seek(i)
        frame_rgb = gif.copy().convert("RGB")
        arr = np.array(frame_rgb)

        art = _render_halfblock(arr, GIF_CROP, GIF_ART_WIDTH, GIF_ART_LINES)
        frames.append(art)

    return frames


def _render_halfblock(
    arr, crop: tuple, width: int, height_lines: int
) -> list[str]:
    """Convert numpy RGB array to half-block ANSI art lines."""
    from PIL import Image as PILImage
    import numpy as np

    l, t, r, b = crop
    cropped = PILImage.fromarray(arr[t:b, l:r])
    px_h = height_lines * 2
    resized = cropped.resize((width, px_h), PILImage.LANCZOS)
    data = np.array(resized)

    lines = []
    for row in range(0, px_h, 2):
        chars = []
        for col in range(width):
            tr = int(data[row, col, 0])
            tg, tb = int(data[row, col, 1]), int(data[row, col, 2])
            if row + 1 < px_h:
                br = int(data[row + 1, col, 0])
                bg, bb = int(data[row + 1, col, 1]), int(data[row + 1, col, 2])
            else:
                br, bg, bb = 0, 0, 0

            top_on = tr > 35
            bot_on = br > 35

            if top_on and bot_on:
                r, g, b = (tr + br) // 2, (tg + bg) // 2, (tb + bb) // 2
                chars.append(f"\033[38;2;{r};{g};{b}m█")
            elif top_on:
                chars.append(f"\033[38;2;{tr};{tg};{tb}m▀")
            elif bot_on:
                chars.append(f"\033[38;2;{br};{bg};{bb}m▄")
            else:
                chars.append(" ")

        lines.append("".join(chars) + RESET)
    return lines


def render_static_frame(gif_path: Path) -> list[str]:
    """Render frame 0 as static art for the banner."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return _fallback_art()

    gif = Image.open(gif_path)
    gif.seek(0)
    arr = np.array(gif.copy().convert("RGB"))
    return _render_halfblock(arr, GIF_CROP, GIF_ART_WIDTH, GIF_ART_LINES)


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATED STARTUP SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════════


def play_startup_animation(frames: list[list[str]], duration_secs: float = 3.0):
    """
    Play the GIF animation centered in the terminal for a few seconds.
    Uses ANSI cursor repositioning to overwrite frames in-place.
    """
    if not frames:
        return

    n_lines = len(frames[0])
    frame_delay = duration_secs / len(frames)
    # Clamp to reasonable range
    frame_delay = max(0.04, min(0.12, frame_delay))

    term_w = shutil.get_terminal_size((80, 24)).columns

    # Print header first
    header_raw = pyfiglet.figlet_format("NBA ANALYSIS", font="pagga")
    header_lines = header_raw.rstrip("\n").split("\n")
    gradient = [
        "\033[38;2;255;110;30m",  # Bright orange
        "\033[38;2;255;70;25m",  # Medium orange
        "\033[38;2;160;40;12m",  # Dark orange
    ]

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.write("\n")

    # Print pagga header centered with gradient
    for i, line in enumerate(header_lines):
        color = gradient[min(i, len(gradient) - 1)]
        pad = max(0, (term_w - len(line)) // 2)
        sys.stdout.write(f" " * pad + color + line + RESET + "\n")

    sys.stdout.write("\n")
    sys.stdout.flush()

    # Print first frame to establish the art region
    art_pad = max(0, (term_w - GIF_ART_WIDTH) // 2)
    for line in frames[0]:
        sys.stdout.write(" " * art_pad + line + "\n")
    sys.stdout.flush()

    # Animate: overwrite the art region with each subsequent frame
    for frame in frames[1:]:
        time.sleep(frame_delay)
        # Move cursor up to start of art region
        sys.stdout.write(CURSOR_UP(n_lines))
        for line in frame:
            sys.stdout.write("\r" + " " * art_pad + line + "\n")
        sys.stdout.flush()

    # Small pause on last frame
    time.sleep(0.3)

    # Clear the animation area
    total_clear = len(header_lines) + 2 + n_lines
    sys.stdout.write(CURSOR_UP(total_clear))
    for _ in range(total_clear + 1):
        sys.stdout.write(CLEAR_LINE + "\n")
    sys.stdout.write(CURSOR_UP(total_clear + 1))
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK ASCII ART (when GIF not found)
# ═══════════════════════════════════════════════════════════════════════════════

FALLBACK_ART_LINES = [
    r"      ,,,,,       ",
    r"    ,@@@@@@,      ",
    r"   @@'---'@@      ",
    r"  @@|     |@@     ",
    r"  @@|  *  |@@     ",
    r"  @@|     |@@     ",
    r"   @@,---,@@      ",
    r"    '@@@@@@'      ",
    r"      '''''       ",
    r"    /       \     ",
    r"   / N B A   \    ",
    r"  /  ANALYST  \   ",
    r" '─────────────'  ",
]


def _fallback_art() -> list[str]:
    """Return fallback ASCII art lines with orange ANSI coloring."""
    return [f"\033[38;2;255;110;30m{line}{RESET}" for line in FALLBACK_ART_LINES]


# ═══════════════════════════════════════════════════════════════════════════════
# BANNER BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


def get_terminal_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def build_header_text() -> Text:
    """Build the pagga-font header with orange gradient."""
    raw = pyfiglet.figlet_format("NBA ANALYSIS", font="pagga")
    lines = raw.rstrip("\n").split("\n")
    header = Text()
    gradient = [Colors.BRIGHT_ORANGE, Colors.ORANGE, Colors.AMBER]
    for i, line in enumerate(lines):
        color = gradient[min(i, len(gradient) - 1)]
        header.append(line + "\n", style=Style(color=color, bold=True))
    return header


def build_tools_lines() -> list[tuple[str, str, str]]:
    """Build tools/skills as structured lines: (icon, label, desc)."""
    # Count how many tool commands aren't shown in the banner
    utility_cmds = {"/clear", "/help", "/quit"}
    total_tool_cmds = len([c for c in COMMANDS if c not in utility_cmds])
    shown = len(TOOLS)
    hidden = total_tool_cmds - shown

    lines = []
    lines.append(("", "TOOLS", ""))
    for name, desc in TOOLS:
        lines.append(("▸", name, desc))
    if hidden > 0:
        lines.append(("", f"  +{hidden} more — /help", ""))
    lines.append(("", "", ""))
    lines.append(("", "SKILLS", ""))
    for name, desc in SKILLS:
        lines.append(("◆", name, desc))
    return lines


def build_two_column_body(art_lines: list[str]) -> Text:
    """
    Build side-by-side layout: GIF art (left) │ tools+skills (right).
    Manually line-by-line for precise alignment.
    """
    tool_lines = build_tools_lines()
    max_lines = max(len(art_lines), len(tool_lines))

    # Strip ANSI to measure visual width of art
    import re
    ansi_re = re.compile(r"\033\[[0-9;]*m")

    art_visual_widths = []
    for l in art_lines:
        stripped = ansi_re.sub("", l)
        art_visual_widths.append(len(stripped))
    art_width = max(art_visual_widths) if art_visual_widths else GIF_ART_WIDTH

    result = Text()
    for i in range(max_lines):
        # Left column: art (raw ANSI — append as-is via markup escape)
        if i < len(art_lines):
            stripped = ansi_re.sub("", art_lines[i])
            pad_needed = art_width - len(stripped)
            # We need to output raw ANSI, so use Text.append_text or direct
            result.append(stripped.ljust(art_width), style=Style(color=Colors.ORANGE))
        else:
            result.append(" " * art_width)

        # Divider
        result.append("  │  ", style=Style(color=Colors.DIM))

        # Right column: tools/skills
        if i < len(tool_lines):
            icon, label, desc = tool_lines[i]
            if icon:
                result.append(f"{icon} ", style=Style(color=Colors.ORANGE))
            else:
                result.append("  ")

            if label and not desc:
                result.append(label, style=Style(color=Colors.CYAN, bold=True))
            elif label:
                result.append(f"{label:<16}", style=Style(color=Colors.AMBER, bold=True))
                result.append(desc, style=Style(color=Colors.GRAY))

        result.append("\n")

    return result


def build_two_column_ansi(art_lines: list[str]) -> str:
    """
    Build two-column layout as raw ANSI string.
    This preserves the true-color GIF art rendering.
    """
    import re
    ansi_re = re.compile(r"\033\[[0-9;]*m")

    tool_lines = build_tools_lines()
    max_lines = max(len(art_lines), len(tool_lines))

    # Measure visual art width
    art_visual_widths = []
    for l in art_lines:
        stripped = ansi_re.sub("", l)
        art_visual_widths.append(len(stripped))
    art_width = max(art_visual_widths) if art_visual_widths else GIF_ART_WIDTH

    # ANSI color codes for right column
    C_ORANGE = "\033[38;2;255;140;0m"
    C_AMBER = "\033[38;2;255;215;0m"
    C_CYAN = "\033[38;2;0;206;209m"
    C_GRAY = "\033[38;2;136;136;136m"
    C_DIM = "\033[38;2;102;102;102m"
    C_BOLD = "\033[1m"
    RST = RESET

    output_lines = []
    for i in range(max_lines):
        line = ""

        # Left: art with true colors
        if i < len(art_lines):
            raw = art_lines[i]
            stripped = ansi_re.sub("", raw)
            pad = art_width - len(stripped)
            line += raw + (" " * pad)
        else:
            line += " " * art_width

        # Divider
        line += f"  {C_DIM}│{RST}  "

        # Right: tools/skills
        if i < len(tool_lines):
            icon, label, desc = tool_lines[i]
            if icon:
                line += f"{C_ORANGE}{icon}{RST} "
            else:
                line += "  "

            if label and not desc:
                # "+N more" line renders dim, section headers render bold cyan
                if label.strip().startswith("+"):
                    line += f"{C_DIM}{label}{RST}"
                else:
                    line += f"{C_CYAN}{C_BOLD}{label}{RST}"
            elif label:
                line += f"{C_AMBER}{C_BOLD}{label:<16}{RST}"
                line += f"{C_GRAY}{desc}{RST}"

        output_lines.append(line)

    return "\n".join(output_lines)


def build_info_line() -> Text:
    """Build the model/path/session info line below the box."""
    info = Text()
    info.append("  Model ", style=Style(color=Colors.DIM))
    info.append("GBM v2 · scikit-learn", style=Style(color=Colors.AMBER))
    info.append("  │  ", style=Style(color=Colors.DIM))
    info.append("Accuracy ", style=Style(color=Colors.DIM))
    info.append("73.5%", style=Style(color=Colors.CYAN, bold=True))
    info.append("  │  ", style=Style(color=Colors.DIM))
    info.append("DB ", style=Style(color=Colors.DIM))
    info.append("SQLite", style=Style(color=Colors.AMBER))
    info.append("  │  ", style=Style(color=Colors.DIM))
    info.append("Session ", style=Style(color=Colors.DIM))
    info.append(
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        style=Style(color=Colors.GRAY),
    )
    return info


def build_welcome_banner(console: Console, gif_path: Path | None = None) -> None:
    """Build and print the full Hermes-style welcome banner."""
    term_width = get_terminal_width()

    # ── Get art lines (GIF or fallback) ──
    if gif_path and gif_path.exists():
        art_lines = render_static_frame(gif_path)
    else:
        art_lines = _fallback_art()

    # ── Header (pagga font) ──
    header = build_header_text()

    # ── Build the two-column body as raw ANSI ──
    body_ansi = build_two_column_ansi(art_lines)

    # ── Assemble into Rich panel ──
    # We use a Table to stack header + tagline + body
    combined = Table(
        show_header=False, show_edge=False, box=None, padding=0, expand=True
    )
    combined.add_column(ratio=1)
    combined.add_row(Align.center(header))
    combined.add_row(
        Text(
            f"  {APP_TAGLINE}",
            style=Style(color=Colors.CYAN, italic=True),
        )
    )
    combined.add_row(Text(""))  # spacer

    # For the body, print the ANSI content directly via Text.from_ansi
    body_text = Text.from_ansi(body_ansi)
    combined.add_row(body_text)

    panel = Panel(
        combined,
        border_style=Style(color=Colors.ORANGE),
        box=box.HEAVY,
        padding=(1, 2),
        expand=True,
    )

    console.print()
    console.print(panel)
    console.print(build_info_line())
    console.print()

    # ── Welcome message ──
    welcome = Text()
    welcome.append("  Welcome to ", style=Style(color=Colors.GRAY))
    welcome.append("NBA Analyst", style=Style(color=Colors.ORANGE, bold=True))
    welcome.append(". Type ", style=Style(color=Colors.GRAY))
    welcome.append("/help", style=Style(color=Colors.CYAN, bold=True))
    welcome.append(
        " for commands or ask anything about the NBA.",
        style=Style(color=Colors.GRAY),
    )
    console.print(welcome)
    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FUNCTIONS & COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════


def _find_player(cur, name_query, limit=5):
    """
    Smart player search: handles 'Curry', 'steph curry', 'Stephen Curry', etc.
    Searches first_name, last_name, AND the concatenated full name.
    Also splits multi-word queries to match first + last independently.
    Returns list of (player_id, first_name, last_name) tuples.
    """
    q = name_query.strip()
    if not q:
        return []

    # Strategy 1: exact full-name match (first || ' ' || last)
    results = cur.execute("""
        SELECT player_id, first_name, last_name FROM players
        WHERE (first_name || ' ' || last_name) LIKE ?
        LIMIT ?
    """, (f"%{q}%", limit)).fetchall()
    if results:
        return results

    # Strategy 2: split into words and match first_name + last_name
    words = q.split()
    if len(words) >= 2:
        results = cur.execute("""
            SELECT player_id, first_name, last_name FROM players
            WHERE first_name LIKE ? AND last_name LIKE ?
            LIMIT ?
        """, (f"%{words[0]}%", f"%{words[-1]}%", limit)).fetchall()
        if results:
            return results

    # Strategy 3: single word — search either column
    results = cur.execute("""
        SELECT player_id, first_name, last_name FROM players
        WHERE first_name LIKE ? OR last_name LIKE ?
        LIMIT ?
    """, (f"%{q}%", f"%{q}%", limit)).fetchall()
    return results


def compute_elo_from_db():
    """Compute live ELO ratings from box_scores in database."""
    import sqlite3
    from collections import defaultdict
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Get team names
    cur.execute("SELECT team_id, full_name FROM teams")
    team_names = {row[0]: row[1] for row in cur.fetchall()}
    
    # Get game scores for current season (00225 = 2025-26)
    # Deduplicate: take MAX points per player per game, THEN sum per team
    cur.execute("""
        SELECT game_id, team_id, SUM(player_pts) as total_points
        FROM (
            SELECT game_id, team_id, player_id, MAX(points) as player_pts
            FROM box_scores
            WHERE game_id LIKE '00225%'
            GROUP BY game_id, team_id, player_id
        )
        GROUP BY game_id, team_id
    """)
    game_scores = defaultdict(dict)
    for gid, tid, pts in cur.fetchall():
        game_scores[gid][tid] = pts
    
    conn.close()
    
    # Initialize ELO, wins, losses at 1500
    elo = {tid: 1500 for tid in team_names.keys()}
    wins = {tid: 0 for tid in team_names.keys()}
    losses = {tid: 0 for tid in team_names.keys()}
    K_FACTOR = 32
    
    # Process each game in order
    for gid in sorted(game_scores.keys()):
        teams = game_scores[gid]
        if len(teams) != 2:
            continue
        
        tids = list(teams.keys())
        t1, t2 = tids[0], tids[1]
        s1, s2 = teams[t1], teams[t2]
        
        e1 = 1 / (1 + 10 ** ((elo.get(t2, 1500) - elo.get(t1, 1500)) / 400))
        e2 = 1 / (1 + 10 ** ((elo.get(t1, 1500) - elo.get(t2, 1500)) / 400))
        
        if s1 > s2:
            S1, S2 = 1, 0
            wins[t1] += 1
            losses[t2] += 1
        elif s2 > s1:
            S1, S2 = 0, 1
            wins[t2] += 1
            losses[t1] += 1
        else:
            S1, S2 = 0.5, 0.5
            wins[t1] += 0.5
            wins[t2] += 0.5
        
        elo[t1] = elo.get(t1, 1500) + K_FACTOR * (S1 - e1)
        elo[t2] = elo.get(t2, 1500) + K_FACTOR * (S2 - e2)
    
    # Format for show_elo compatibility
    result = {}
    for tid in team_names.keys():
        w = int(wins[tid])
        l = int(losses[tid])
        gp = w + l
        wpct = (w / gp * 100) if gp > 0 else 0
        result[str(tid)] = {
            "elo": elo[tid],
            "wins": w,
            "losses": l,
            "win_pct": f"{wpct:.1f}"
        }
    
    return result

def load_elo():
    """Load ELO ratings - computes fresh from DB if available."""
    # Try to compute live ELO from box_scores first
    try:
        return compute_elo_from_db()
    except Exception as e:
        pass
    
    # Fallback to JSON file
    try:
        with open("data/elo_ratings.json") as f:
            return json.load(f)
    except:
        return {}

def load_teams():
    sys.path.insert(0, 'src')
    from sportsprediction.data.models import Team
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        return {t.team_id: t.full_name for t in session.query(Team).all()}

def get_recent_games(teams):
    sys.path.insert(0, 'src')
    from sportsprediction.data.models import BoxScore, Game
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sqlalchemy import func
    from collections import defaultdict
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        # Deduplicate: MAX per player per game, then SUM per team
        from sqlalchemy import text as sa_text
        game_teams = session.execute(sa_text("""
            SELECT game_id, team_id, SUM(player_pts) as pts
            FROM (
                SELECT game_id, team_id, player_id, MAX(points) as player_pts
                FROM box_scores
                GROUP BY game_id, team_id, player_id
            )
            GROUP BY game_id, team_id
        """)).fetchall()
    
    games_data = defaultdict(dict)
    for game_id, team_id, pts in game_teams:
        games_data[game_id][team_id] = float(pts)
    
    valid = {k: v for k, v in games_data.items() if len(v) == 2}
    
    with get_session(engine) as session:
        all_dates = {g.game_id: g.game_date for g in session.query(Game).all()}
    
    sorted_games = sorted(
        [g for g in valid.keys() if g in all_dates],
        key=lambda g: all_dates[g], reverse=True
    )[:10]
    
    results = []
    for gid in sorted_games:
        tids = list(valid[gid].keys())
        results.append({
            "date": all_dates[gid],
            "t1": teams.get(tids[0], f"Team {tids[0]}"),
            "t2": teams.get(tids[1], f"Team {tids[1]}"),
            "s1": valid[gid][tids[0]],
            "s2": valid[gid][tids[1]],
        })
    return results

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def show_elo(teams, elo, save_png=False):
    import matplotlib.pyplot as plt
    import os
    
    sorted_elo = sorted(elo.items(), key=lambda x: x[1]["elo"], reverse=True)
    print("\n=== ELO RANKINGS ===\n")
    print(f"{'Rank':<5} {'Team':<25} {'ELO':<8} {'Record':<12} {'Win%'}")
    print("-" * 60)
    for i, (tid, data) in enumerate(sorted_elo[:15], 1):
        name = teams.get(int(tid), f"Team {tid}")[:24]
        print(f"{i:<5} {name:<25} {data['elo']:<8.0f} {data['wins']}-{data['losses']:<6} {data['win_pct']}%")
    
    # Generate PNG if requested
    if save_png:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        top_teams = sorted_elo[:15]
        names = [teams.get(int(tid), f"Team {tid}")[:20] for tid, _ in top_teams]
        ratings = [data["elo"] for _, data in top_teams]
        
        colors = ['#1d428a' if i < 5 else '#552583' if i < 10 else '#888888' for i in range(len(names))]
        
        bars = ax.barh(names[::-1], ratings[::-1], color=colors[::-1])
        ax.set_xlabel('ELO Rating', fontsize=12, fontweight='bold')
        ax.set_title('NBA Team ELO Ratings', fontsize=14, fontweight='bold')
        
        for bar, rating in zip(bars, ratings[::-1]):
            ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                   f'{rating:.0f}', va='center', fontsize=9)
        
        plt.tight_layout()
        
        filepath = os.path.join("data", "elo_rankings.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")

def show_games(teams):
    games = get_recent_games(teams)
    print("\n=== RECENT GAMES ===\n")
    for g in games:
        print(f"{g['date']}: {g['t1']} {g['s1']:.0f} - {g['s2']:.0f} {g['t2']}")

def show_predict(teams, elo, arg):
    if not arg:
        print("Usage: /predict <team1> <team2>")
        print("Example: /predict Celtics Lakers")
        return
    
    # Split arg into parts and match each to a team
    parts = arg.lower().split()
    matches = []
    for tid, name in teams.items():
        name_lower = name.lower()
        # Check if any part of the arg matches the team name (full or last word)
        for part in parts:
            if part in name_lower or part == name_lower.split()[-1]:
                matches.append((tid, name))
                break
    
    if len(matches) < 2:
        print("Teams not found. Available:")
        for name in sorted(set(teams.values())):
            print(f"  - {name}")
        return
    
    t1_id, t1_name = matches[0]
    t2_id, t2_name = matches[1]
    t1_elo = elo.get(str(t1_id), elo.get(str(t1_id), {"elo": 1500, "wins": 0, "losses": 0, "win_pct": "0.0"}))
    t2_elo = elo.get(str(t2_id), elo.get(str(t2_id), {"elo": 1500, "wins": 0, "losses": 0, "win_pct": "0.0"}))
    
    if not t1_elo or not t2_elo:
        print("Error: No ELO data")
        return
    
    prob = expected_score(t1_elo.get("elo", 1500), t2_elo.get("elo", 1500))
    
    print(f"\n=== PREDICTION ===")
    print(f"{t1_name} vs {t2_name}")
    print(f"\nELO Ratings:")
    print(f"  {t1_name}: {t1_elo.get('elo', 1500):.0f} ({t1_elo.get('wins', 0)}-{t1_elo.get('losses', 0)}, {t1_elo.get('win_pct', '0.0')}%)")
    print(f"  {t2_name}: {t2_elo.get('elo', 1500):.0f} ({t2_elo.get('wins', 0)}-{t2_elo.get('losses', 0)}, {t2_elo.get('win_pct', '0.0')}%)")
    print(f"\nWin Probability:")
    print(f"  {t1_name}: {prob:.1%}")
    print(f"  {t2_name}: {1-prob:.1%}")
    print(f"\nMarket Odds (Polymarket):")
    print("  [NBA daily markets not available - showing futures]")
    print(f"  Championship: Thunder 35.5%, Next: varies")

def show_odds():
    """Show tonight's NBA game odds via Playwright."""
    print("\n=== TONIGHT'S NBA GAMES - POLYMARKET ===\n")
    
    try:
        from playwright.sync_api import sync_playwright
        import re
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://polymarket.com/sports/nba/games', timeout=20000)
            page.wait_for_timeout(3000)
            text = page.inner_text('body')
            browser.close()
        
        team_map = {
            'ind': 'Pacers', 'mil': 'Bucks', 'dal': 'Mavericks', 'cle': 'Cavaliers',
            'det': 'Pistons', 'tor': 'Raptors', 'por': 'Trail Blazers', 'phi': '76ers',
            'gsw': 'Warriors', 'nyk': 'Knicks', 'min': 'Timberwolves', 'okc': 'Thunder',
            'uta': 'Jazz', 'sac': 'Kings', 'lal': 'Lakers', 'lac': 'Clippers',
            'pho': 'Suns', 'den': 'Nuggets', 'mem': 'Grizzlies', 'nop': 'Pelicans',
            'bos': 'Celtics', 'mia': 'Heat', 'atl': 'Hawks', 'orl': 'Magic',
            'chi': 'Bulls', 'cha': 'Hornets', 'was': 'Wizards', 'hou': 'Rockets',
            'sas': 'Spurs', 'bkn': 'Nets'
        }
        
        matches = re.findall(r'([A-Za-z]{3})(\d+)¢', text)
        games = []
        seen = set()
        for i in range(0, len(matches)-1, 2):
            if i+1 < len(matches):
                t1, o1 = matches[i]
                t2, o2 = matches[i+1]
                t1l, t2l = t1.lower(), t2.lower()
                if t1l != t2l and t1l in team_map and t2l in team_map:
                    key = tuple(sorted([t1l, t2l]))
                    if key not in seen:
                        seen.add(key)
                        games.append((team_map[t1l], int(o1), team_map[t2l], int(o2)))
        
        if games:
            for g in games[:6]:
                print(f"  {g[0]:<16} {g[1]:>3}%  vs  {g[2]:<16} {g[3]:>3}%")
            print("\n  (Source: polymarket.com)")
            return
        
    except Exception as e:
        print(f"  Browser error: {e}")
    
    # Fallback
    print("  Could not load games")
    print("  Championship futures:")
    show_championship_odds()

def show_championship_odds():
    """Show 2026 NBA Championship odds from Polymarket API."""
    print("\n=== 2026 NBA CHAMPIONSHIP ===\n")
    
    try:
        import urllib.request
        import json
        
        url = "https://gamma-api.polymarket.com/public-search?q=2026%20nba%20champion"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        
        events = data.get('events', [])
        
        team_names = {
            'oklahoma city thunder': 'Thunder', 'houston rockets': 'Rockets', 
            'cleveland cavaliers': 'Cavaliers', 'denver nuggets': 'Nuggets',
            'boston celtics': 'Celtics', 'san antonio spurs': 'Spurs',
            'golden state warriors': 'Warriors', 'miami heat': 'Heat',
            'milwaukee bucks': 'Bucks', 'phoenix suns': 'Suns',
            'dallas mavericks': 'Mavericks', 'minnesota timberwolves': 'Timberwolves',
            'new york knicks': 'Knicks', 'memphis grizzlies': 'Grizzlies',
            'detroit pistons': 'Pistons', 'los angeles lakers': 'Lakers',
            'la clippers': 'Clippers',
        }
        
        markets_data = []
        for e in events:
            title = e.get('title', '')
            # Only get main championship, not Rising Stars
            if '2026' in title and 'champion' in title.lower() and 'rising stars' not in title.lower():
                for m in e.get('markets', []):
                    mvol = float(m.get('volume', 0))
                    if mvol > 0:
                        prices = json.loads(m['outcomePrices'])
                        outcomes = json.loads(m['outcomes'])
                        # Only process Yes/No markets (championship winner)
                        if outcomes[0] != 'Yes':
                            continue
                        yes_price = float(prices[0])
                        
                        q_lower = m['question'].lower()
                        team = "Team"
                        for k, v in team_names.items():
                            if k in q_lower:
                                team = v
                                break
                        
                        markets_data.append((team, yes_price * 100, mvol))
        
        markets_data.sort(key=lambda x: -x[1])
        
        for team, prob, mvol in markets_data[:5]:
            bar = "█" * int(prob / 5)
            print(f"  {team:<20} {prob:5.1f}% {bar}  ${mvol/1e6:.1f}M")
        
        print("\n  (Source: Polymarket)")
        
    except Exception as e:
        print(f"  Error: {e}")
        print("  Thunder 35.5% | Spurs 13.9% | Celtics 13.2%")

def update_elo():
    print("Updating ELO...")
    import importlib.util
    spec = importlib.util.spec_from_file_location("compute_elo", "scripts/compute_elo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        module.compute_elo_ratings(session)
    print("✓ ELO updated")

def show_teams(teams):
    print("\n=== AVAILABLE TEAMS ===\n")
    for name in sorted(set(teams.values())):
        print(f"  {name}")


def show_player(name_query, save_png=False):
    """Show player career stats by season (like ESPN table)."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not name_query:
        print("Usage: /player <name> [--png]")
        print("Example: /player Curry")
        print("         /player Curry --png")
        return
    
    # Check for --png flag
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find player
    player = _find_player(cur, name_query, limit=5)
    
    if not player:
        print(f"No players found matching '{name_query}'")
        conn.close()
        return
    
    if len(player) > 1:
        print(f"Multiple players found - be more specific:")
        for p in player:
            print(f"  {p[1]} {p[2]} (ID: {p[0]})")
        conn.close()
        return
    
    player_id, first_name, last_name = player[0]
    
    # Get career stats by season (all available from 2022 onwards)
    stats = cur.execute("""
        SELECT 
            SUBSTR(g.season, 1, 4) as year,
            COUNT(*) as GP,
            ROUND(AVG(bs.minutes), 1) as MIN,
            ROUND(AVG(bs.points), 1) as PTS,
            ROUND(AVG(bs.rebounds), 1) as REB,
            ROUND(AVG(bs.assists), 1) as AST,
            ROUND(AVG(bs.steals), 1) as STL,
            ROUND(AVG(bs.blocks), 1) as BLK,
            ROUND(AVG(bs.turnovers), 1) as "TO",
            ROUND(AVG(bs.fg3m), 1) as "3PM",
            ROUND(AVG(1.0 * bs.fgm / NULLIF(bs.fga, 0)) * 100, 1) as "FG_PCT",
            ROUND(AVG(1.0 * bs.fg3m / NULLIF(bs.fg3a, 0)) * 100, 1) as "3P_PCT",
            ROUND(AVG(1.0 * bs.ftm / NULLIF(bs.fta, 0)) * 100, 1) as "FT_PCT"
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.player_id = ? AND bs.minutes > 0 AND g.season >= '2022-23'
        GROUP BY g.season
        ORDER BY year DESC
    """, (player_id,)).fetchall()
    
    if not stats:
        print(f"No stats found for {first_name} {last_name}")
        conn.close()
        return
    
    # Calculate career averages (2022-23 onwards)
    career = cur.execute("""
        SELECT 
            ROUND(AVG(bs.minutes), 1) as MIN,
            ROUND(AVG(bs.points), 1) as PTS,
            ROUND(AVG(bs.rebounds), 1) as REB,
            ROUND(AVG(bs.assists), 1) as AST,
            ROUND(AVG(bs.steals), 1) as STL,
            ROUND(AVG(bs.blocks), 1) as BLK,
            ROUND(AVG(bs.turnovers), 1) as "TO",
            ROUND(AVG(bs.fg3m), 1) as "3PM",
            ROUND(AVG(1.0 * bs.fgm / NULLIF(bs.fga, 0)) * 100, 1) as "FG_PCT",
            ROUND(AVG(1.0 * bs.fg3m / NULLIF(bs.fg3a, 0)) * 100, 1) as "3P_PCT",
            ROUND(AVG(1.0 * bs.ftm / NULLIF(bs.fta, 0)) * 100, 1) as "FT_PCT",
            COUNT(*) as GP
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.player_id = ? AND bs.minutes > 0 AND g.season >= '2022-23'
    """, (player_id,)).fetchone()
    
    # Print header
    print(f"\n=== {first_name} {last_name} Career Stats ===\n")
    print(f"{'SEASON':<8} {'GP':>4} {'MIN':>5} {'PTS':>5} {'REB':>5} {'AST':>5} {'STL':>4} {'BLK':>4} {'TO':>4} {'3PM':>4} {'FG%':>5} {'3P%':>5} {'FT%':>5}")
    print("-" * 75)
    
    # Print each season
    for row in stats:
        year, gp, min_, pts, reb, ast, stl, blk, to, tpm, fg, tp, ft = row
        print(f"{year}-{str(int(year)+1)[-2:]:<5} {gp:>4} {min_:>5.1f} {pts:>5.1f} {reb:>5.1f} {ast:>5.1f} {stl:>4.1f} {blk:>4.1f} {to:>4.1f} {tpm:>4.1f} {fg:>4.1f}% {tp:>4.1f}% {ft:>4.1f}%")
    
    # Print career totals
    print("-" * 75)
    min_, pts, reb, ast, stl, blk, to, tpm, fg, tp, ft, gp = career
    print(f"{'Career':<8} {gp:>4} {min_:>5.1f} {pts:>5.1f} {reb:>5.1f} {ast:>5.1f} {stl:>4.1f} {blk:>4.1f} {to:>4.1f} {tpm:>4.1f} {fg:>4.1f}% {tp:>4.1f}% {ft:>4.1f}%")
    
    # Generate PNG if requested
    if save_png:
        # Create visualization
        fig, ax = plt.subplots(figsize=(12, 6))
        
        seasons = [f"{row[0]}-{str(int(row[0])+1)[-2:]}" for row in stats]
        ppg = [float(row[3]) for row in stats]  # PTS
        
        bars = ax.bar(seasons, ppg, color='#1d428a')  # NBA blue
        ax.set_xlabel('Season', fontsize=12, fontweight='bold')
        ax.set_ylabel('Points Per Game', fontsize=12, fontweight='bold')
        ax.set_title(f'{first_name} {last_name} - PPG by Season', fontsize=14, fontweight='bold')
        
        # Add value labels
        for bar, pts_val in zip(bars, ppg):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                   f'{pts_val:.1f}', ha='center', va='bottom', fontsize=9)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save
        filename = f"{first_name}_{last_name}_ppg.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== TEAM STATS ==============

def show_team(name_query, save_png=False):
    """Show team stats by season."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not name_query:
        print("Usage: /team <name> [--png]")
        print("Example: /team Lakers")
        return
    
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find team
    team = cur.execute("""
        SELECT team_id, abbreviation, full_name 
        FROM teams 
        WHERE full_name LIKE ? OR abbreviation LIKE ?
        LIMIT 5
    """, (f"%{name_query}%", f"%{name_query}%")).fetchall()
    
    if not team:
        print(f"No teams found matching '{name_query}'")
        conn.close()
        return
    
    if len(team) > 1:
        print(f"Multiple teams found - be more specific:")
        for t in team:
            print(f"  {t[2]} ({t[1]})")
        conn.close()
        return
    
    team_id, abbrev, full_name = team[0]
    abbrev = abbrev or full_name[:3].upper()
    
    # Get team stats by season - simpler approach using box_scores + games
    stats = cur.execute("""
        SELECT 
            SUBSTR(g.season, 1, 4) as year,
            COUNT(DISTINCT g.game_id) as GP,
            SUM(CASE WHEN team_pts > opp_pts THEN 1 ELSE 0 END) as W,
            SUM(CASE WHEN team_pts < opp_pts THEN 1 ELSE 0 END) as L
        FROM games g
        JOIN (
            SELECT game_id, team_id, SUM(points) as team_pts
            FROM box_scores WHERE team_id = ?
            GROUP BY game_id
        ) my_team ON g.game_id = my_team.game_id
        JOIN (
            SELECT game_id, SUM(points) as opp_pts
            FROM box_scores
            WHERE team_id != ? AND game_id IN (
                SELECT game_id FROM box_scores WHERE team_id = ?
            )
            GROUP BY game_id
        ) opp ON g.game_id = opp.game_id
        WHERE g.season >= '2022-23'
        GROUP BY g.season
        ORDER BY year DESC
    """, (team_id, team_id, team_id)).fetchall()
    
    if not stats:
        print(f"No stats found for {full_name}")
        conn.close()
        return
    
    # Print table
    print(f"\n=== {full_name} ({abbrev}) Season Stats ===\n")
    print(f"{'SEASON':<8} {'GP':>4} {'W':>4} {'L':>4} {'WIN%':>6}")
    print("-" * 35)
    
    wins_total = 0
    losses_total = 0
    games_total = 0
    
    for row in stats:
        year, gp, w, l = row
        win_pct = w / gp * 100 if gp > 0 else 0
        print(f"{year}-{str(int(year)+1)[-2:]:<5} {gp:>4} {w:>4} {l:>4} {win_pct:>5.1f}%")
        wins_total += w
        losses_total += l
        games_total += gp
    
    print("-" * 35)
    win_pct_total = wins_total / games_total * 100 if games_total > 0 else 0
    print(f"{'Total':<8} {games_total:>4} {wins_total:>4} {losses_total:>4} {win_pct_total:>5.1f}%")
    
    # PNG
    if save_png:
        fig, ax = plt.subplots(figsize=(10, 6))
        seasons = [f"{row[0]}-{str(int(row[0])+1)[-2:]}" for row in stats]
        wins = [row[2] for row in stats]
        
        ax.bar(seasons, wins, color='#17408B')
        ax.set_xlabel('Season', fontsize=12, fontweight='bold')
        ax.set_ylabel('Wins', fontsize=12, fontweight='bold')
        ax.set_title(f'{abbrev} - Wins by Season', fontsize=14, fontweight='bold')
        
        for i, w in enumerate(wins):
            ax.text(i, w + 1, str(w), ha='center', fontsize=10)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        filepath = os.path.join("data", f"{abbrev}_wins.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== PLAYER COMPARE ==============

def show_compare(query, save_png=False):
    """Compare two players."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not query or 'vs' not in query.lower():
        print("Usage: /compare <player1> vs <player2> [--png]")
        print("Example: /compare Curry vs LeBron")
        return
    
    if '--png' in query:
        query = query.replace('--png', '').strip()
        save_png = True
    
    parts = query.lower().split('vs')
    if len(parts) != 2:
        print("Usage: /compare <player1> vs <player2> [--png]")
        return
    
    p1_query = parts[0].strip()
    p2_query = parts[1].strip()
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find players
    p1 = _find_player(cur, p1_query, limit=1)
    p1 = p1[0] if p1 else None
    p2 = _find_player(cur, p2_query, limit=1)
    p2 = p2[0] if p2 else None
    
    if not p1 or not p2:
        print("Could not find both players. Be more specific.")
        conn.close()
        return
    
    # Get career averages
    p1_stats = cur.execute("""
        SELECT ROUND(AVG(points), 1), ROUND(AVG(rebounds), 1), ROUND(AVG(assists), 1), COUNT(*)
        FROM box_scores WHERE player_id = ? AND minutes > 0
    """, (p1[0],)).fetchone()
    
    p2_stats = cur.execute("""
        SELECT ROUND(AVG(points), 1), ROUND(AVG(rebounds), 1), ROUND(AVG(assists), 1), COUNT(*)
        FROM box_scores WHERE player_id = ? AND minutes > 0
    """, (p2[0],)).fetchone()
    
    print(f"\n=== {p1[1]} {p1[2]} vs {p2[1]} {p2[2]} ===")
    print(f"\nCareer Averages (2022-23 onwards):")
    print(f"{'Player':<20} {'PPG':>6} {'RPG':>6} {'APG':>6} {'GP':>6}")
    print("-" * 50)
    print(f"{p1[1]} {p1[2]:<10} {p1_stats[0]:>6.1f} {p1_stats[1]:>6.1f} {p1_stats[2]:>6.1f} {p1_stats[3]:>6}")
    print(f"{p2[1]} {p2[2]:<10} {p2_stats[0]:>6.1f} {p2_stats[1]:>6.1f} {p2_stats[2]:>6.1f} {p2_stats[3]:>6}")
    
    if save_png:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        stats = ['PPG', 'RPG', 'APG']
        p1_vals = [float(p1_stats[0]), float(p1_stats[1]), float(p1_stats[2])]
        p2_vals = [float(p2_stats[0]), float(p2_stats[1]), float(p2_stats[2])]
        
        x = range(len(stats))
        width = 0.35
        
        ax.bar([i - width/2 for i in x], p1_vals, width, label=p1[1], color='#17408B')
        ax.bar([i + width/2 for i in x], p2_vals, width, label=p2[1], color='#C9082A')
        
        ax.set_ylabel('Average', fontsize=12, fontweight='bold')
        ax.set_title(f'{p1[2]} vs {p2[2]} - Career Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(stats)
        ax.legend()
        
        plt.tight_layout()
        
        filename = f"{p1[2]}_vs_{p2[2]}_compare.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== PLAYER TREND ==============

def show_trend(name_query, save_png=False):
    """Show player PPG trend over time."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    if not name_query:
        print("Usage: /trend <player> [--png]")
        print("Example: /trend Curry")
        return
    
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    player = _find_player(cur, name_query, limit=1)
    player = player[0] if player else None
    
    if not player:
        print(f"No player found matching '{name_query}'")
        conn.close()
        return
    
    # Get game-by-game PPG trend
    trend = cur.execute("""
        SELECT g.game_date, bs.points, g.season
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.player_id = ? AND bs.minutes > 0
        ORDER BY g.game_date ASC
    """, (player[0],)).fetchall()
    
    if not trend:
        print(f"No stats found for {player[1]} {player[2]}")
        conn.close()
        return
    
    print(f"\n=== {player[1]} {player[2]} PPG Trend ===")
    print(f"Last 20 games:\n")
    
    dates = [t[0] for t in trend[-20:]]
    points = [t[1] for t in trend[-20:]]
    
    for i, t in enumerate(trend[-10:]):
        print(f"  {t[0]}: {t[1]} pts ({t[2]})")
    
    if len(trend) > 10:
        print(f"  ... ({len(trend) - 10} more games)")
    
    avg = sum(p for _, p, _ in trend) / len(trend)
    print(f"\nSeason Avg: {avg:.1f} PPG over {len(trend)} games")
    
    if save_png:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Last 30 games
        recent = trend[-30:]
        dates = [t[0][-5:] for t in recent]  # Just month-day
        points = [t[1] for t in recent]
        
        ax.plot(dates, points, marker='o', linewidth=2, color='#17408B', label='PPG')
        
        # Rolling average
        window = 5
        rolling = []
        for i in range(len(points)):
            if i < window - 1:
                rolling.append(sum(points[:i+1])/(i+1))
            else:
                rolling.append(sum(points[i-window+1:i+1])/window)
        
        ax.plot(dates, rolling, linewidth=2, color='#C9082A', linestyle='--', label=f'{window}-game avg')
        
        ax.set_xlabel('Game Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Points', fontsize=12, fontweight='bold')
        ax.set_title(f'{player[1]} {player[2]} - PPG Trend', fontsize=14, fontweight='bold')
        ax.legend()
        
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        filename = f"{player[1]}_{player[2]}_trend.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== LEAGUE LEADERS ==============

def show_top(category, save_png=False):
    """Show league leaders for a category."""
    import sqlite3
    import matplotlib.pyplot as plt
    import os
    
    valid_cats = {'pts': 'points', 'reb': 'rebounds', 'ast': 'assists', 
                  'stl': 'steals', 'blk': 'blocks', '3pm': 'fg3m'}
    
    if not category or category.lower() not in valid_cats:
        print("Usage: /top <category> [--png]")
        print("Categories: pts, reb, ast, stl, blk, 3pm")
        return
    
    if '--png' in category:
        category = category.replace('--png', '').strip()
        save_png = True
    
    stat_col = valid_cats[category.lower()]
    title_map = {'pts': 'Points', 'reb': 'Rebounds', 'ast': 'Assists',
                 'stl': 'Steals', 'blk': 'Blocks', '3pm': '3-Pointers Made'}
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Get top 10 players by total in current season
    leaders = cur.execute(f"""
        SELECT p.first_name, p.last_name, SUM(bs.{stat_col}) as total, COUNT(*) as GP,
               ROUND(AVG(bs.{stat_col}), 1) as avg
        FROM box_scores bs
        JOIN players p ON bs.player_id = p.player_id
        JOIN games g ON bs.game_id = g.game_id
        WHERE bs.minutes > 0 AND g.season = '2025-26'
        GROUP BY p.player_id
        ORDER BY total DESC
        LIMIT 10
    """).fetchall()
    
    print(f"\n=== 2025-26 {title_map[category]} Leaders ===\n")
    print(f"{'Rank':<6} {'Player':<25} {'Total':>8} {'GP':>5} {'Avg':>6}")
    print("-" * 55)
    
    for i, row in enumerate(leaders, 1):
        print(f"{i:<6} {row[0]} {row[1]:<18} {row[2]:>8.0f} {row[3]:>5} {row[4]:>6.1f}")
    
    if save_png:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        names = [f"{r[0][0]}. {r[1]}" for r in leaders][:10]
        totals = [r[2] for r in leaders][:10]
        
        colors = ['#17408B' if i < 3 else '#552583' if i < 6 else '#888888' for i in range(len(names))]
        
        bars = ax.barh(names[::-1], totals[::-1], color=colors[::-1])
        ax.set_xlabel(f'Total {title_map[category]}', fontsize=12, fontweight='bold')
        ax.set_title(f'2025-26 {title_map[category]} Leaders', fontsize=14, fontweight='bold')
        
        for bar, val in zip(bars, totals[::-1]):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                   f'{val:.0f}', va='center', fontsize=10)
        
        plt.tight_layout()
        
        filepath = os.path.join("data", f"leaders_{category}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== HEATMAP ==============

def show_heatmap(save_png=False):
    """Show team stats correlation heatmap."""
    import sqlite3
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import os
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Get team stats from box_scores
    stats = cur.execute("""
        SELECT 
            t.full_name as Team,
            COUNT(DISTINCT g.game_id) as GP,
            SUM(bs.points) as PTS,
            SUM(bs.rebounds) as REB,
            SUM(bs.assists) as AST,
            SUM(bs.steals) as STL,
            SUM(bs.blocks) as BLK,
            SUM(bs.turnovers) as TOV,
            SUM(bs.fg3m) as TPM
        FROM box_scores bs
        JOIN games g ON bs.game_id = g.game_id
        JOIN teams t ON bs.team_id = t.team_id
        WHERE g.season = '2024-25'
        GROUP BY t.team_id
    """).fetchall()
    
    if not stats:
        print("No team stats found for 2024-25 season")
        conn.close()
        return
    
    import pandas as pd
    df = pd.DataFrame(stats, columns=['Team', 'GP', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'TPM'])
    
    # Calculate per-game stats
    df['PPG'] = df['PTS'] / df['GP']
    df['RPG'] = df['REB'] / df['GP']
    df['APG'] = df['AST'] / df['GP']
    df['SPG'] = df['STL'] / df['GP']
    df['BPG'] = df['BLK'] / df['GP']
    df['TPG'] = df['TOV'] / df['GP']
    df['TPMpg'] = df['TPM'] / df['GP']
    
    # Get correlation matrix
    stats_cols = ['PPG', 'RPG', 'APG', 'SPG', 'BPG', 'TPG', 'TPMpg']
    corr_matrix = df[stats_cols].corr()
    
    print("\n=== Team Stats Correlation Matrix (2024-25) ===\n")
    print(corr_matrix.round(2).to_string())
    
    if save_png:
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                   center=0, square=True, linewidths=1, ax=ax)
        ax.set_title('NBA Team Stats Correlation Matrix (2024-25)', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        filepath = os.path.join("data", "heatmap.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


# ============== SHOT CHART ==============

def show_shot(name_query, save_png=False):
    """Show player shot chart."""
    import sqlite3
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle, Arc
    import os
    
    if not name_query:
        print("Usage: /shot <player> [--png]")
        print("Example: /shot Curry")
        return
    
    if '--png' in name_query:
        name_query = name_query.replace('--png', '').strip()
        save_png = True
    
    conn = sqlite3.connect("data/hermes.db")
    cur = conn.cursor()
    
    # Find player
    player = _find_player(cur, name_query, limit=1)
    player = player[0] if player else None
    
    if not player:
        print(f"No player found matching '{name_query}'")
        conn.close()
        return
    
    # Get shot data
    shots = cur.execute("""
        SELECT loc_x, loc_y, shot_made, shot_distance, action_type, shot_type
        FROM shot_charts
        WHERE player_id = ?
    """, (player[0],)).fetchall()
    
    if not shots:
        print(f"No shot chart data for {player[1]} {player[2]}")
        conn.close()
        return
    
    # Get season range
    season_range = cur.execute("""
        SELECT MIN(g.season) as min_season, MAX(g.season) as max_season
        FROM shot_charts s
        JOIN games g ON s.game_id = g.game_id
        WHERE s.player_id = ?
    """, (player[0],)).fetchone()
    
    season_str = ""
    if season_range and season_range[0]:
        season_str = f" | {season_range[0]} - {season_range[1]}"
    
    print(f"\n=== {player[1]} {player[2]} Shot Chart{season_str} ===")
    print(f"Total shots: {len(shots)}")
    
    made = sum(1 for s in shots if s[2] == 1)
    print(f"Made: {made} ({made/len(shots)*100:.1f}%)")
    
    # Season breakdown - use games.season column directly
    season_data = cur.execute("""
        SELECT 
            g.season,
            COUNT(DISTINCT s.game_id) as games,
            COUNT(*) as shots,
            SUM(s.shot_made) as made
        FROM shot_charts s
        JOIN games g ON s.game_id = g.game_id
        WHERE s.player_id = ?
        GROUP BY g.season
        ORDER BY g.season DESC
    """, (player[0],)).fetchall()
    
    if len(season_data) > 1:
        print("\nBy season:")
        for row in season_data:
            pct = row[3]/row[2]*100 if row[2] > 0 else 0
            print(f"  {row[0]}: {row[1]} games, {row[2]} shots, {row[3]} made ({pct:.1f}%)")
    
    if save_png:
        # ── Draw court ──
        def draw_court(ax=None, color='#333333', lw=1.5):
            if ax is None:
                ax = plt.gca()

            court_elements = [
                Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False),          # Hoop
                Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color),                   # Backboard
                Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color, fill=False),     # Outer box
                Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color, fill=False),     # Inner box
                Arc((0, 142.5), 120, 120, theta1=0, theta2=180, linewidth=lw, color=color),   # FT circle top
                Arc((0, 142.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color, linestyle='dashed'),
                Rectangle((-220, -47.5), 0, 140, linewidth=lw, color=color),                  # Corner 3 left
                Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color),                   # Corner 3 right
                Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color),      # 3pt arc
                Arc((0, 422.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color),   # Center court
            ]

            for element in court_elements:
                ax.add_patch(element)
            return ax

        # ── Plot ──
        fig, ax = plt.subplots(figsize=(12, 11), facecolor='#FAFAFA')
        ax.set_facecolor('#FAFAFA')
        draw_court(ax)
        ax.set_xlim(-250, 250)
        ax.set_ylim(-50, 450)
        ax.set_aspect('equal')

        # ── Colors ──
        # Using green/red instead of blue/red — much more distinguishable
        COLOR_MADE = '#2E8B57'     # Sea green
        COLOR_MISSED = '#DC143C'   # Crimson
        EDGE_MADE = '#1B5E20'      # Dark green edge
        EDGE_MISSED = '#8B0000'    # Dark red edge

        # Handle shot_made being int, bool, or string
        def is_made(val):
            if isinstance(val, (int, float)):
                return val == 1
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ('1', 'true', 'yes')
            return False

        made_count = sum(1 for s in shots if is_made(s[2]))
        missed_count = len(shots) - made_count

        # Separate made/missed for proper layering
        made_x = [s[0] for s in shots if is_made(s[2])]
        made_y = [s[1] for s in shots if is_made(s[2])]
        miss_x = [s[0] for s in shots if not is_made(s[2])]
        miss_y = [s[1] for s in shots if not is_made(s[2])]

        # Plot missed first (underneath), then made on top
        ax.scatter(miss_x, miss_y,
                   c=COLOR_MISSED, s=120, alpha=0.7,
                   edgecolors=EDGE_MISSED, linewidths=0.8,
                   zorder=2, label='_nolegend_')
        ax.scatter(made_x, made_y,
                   c=COLOR_MADE, s=120, alpha=0.7,
                   edgecolors=EDGE_MADE, linewidths=0.8,
                   zorder=3, label='_nolegend_')

        # ── Legend (using SAME alpha as the dots so colors match) ──
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='none',
                   markerfacecolor=COLOR_MADE, markeredgecolor=EDGE_MADE,
                   markersize=12, markeredgewidth=0.8, alpha=0.7,
                   label=f'Made ({made_count})'),
            Line2D([0], [0], marker='o', color='none',
                   markerfacecolor=COLOR_MISSED, markeredgecolor=EDGE_MISSED,
                   markersize=12, markeredgewidth=0.8, alpha=0.7,
                   label=f'Missed ({missed_count})'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=12,
                  framealpha=0.9, edgecolor='#CCCCCC')

        # ── Labels ──
        ax.set_title(f'{player[1]} {player[2]} — Shot Chart{season_str}',
                     fontsize=16, fontweight='bold', pad=15)
        ax.set_xlabel('Court Width (units)', fontsize=11)
        ax.set_ylabel('Court Length (units)', fontsize=11)

        # ── Stats annotation ──
        pct = made_count / len(shots) * 100 if shots else 0
        ax.text(0.02, 0.98,
                f'{len(shots)} shots  ·  {pct:.1f}% FG',
                transform=ax.transAxes, fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#CCCCCC', alpha=0.9))

        plt.tight_layout()

        filename = f"{player[1]}_{player[2]}_shot_chart.png".replace(" ", "_")
        filepath = os.path.join("data", filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#FAFAFA')
        plt.close()
        print(f"\n✓ Chart saved to: {filepath}")
    
    conn.close()


def show_pattern(query, save_png=False):
    """Analyze player matchup patterns."""
    sys.path.insert(0, 'src')
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sportsprediction.data.features.pattern.detector import PatternDetector, MatchupPattern
    from sportsprediction.data.models import Player, Team
    
    # Parse query: "player vs team"
    if ' vs ' not in query:
        print("Usage: /pattern <player> vs <team>")
        return
    
    player_name, team_name = query.split(' vs ', 1)
    player_name = player_name.strip()
    team_name = team_name.strip()
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        # Find player
        player = session.query(Player).filter(
            (Player.first_name + ' ' + Player.last_name).ilike(f"%{player_name}%")
        ).first()
        
        if not player:
            print(f"Player not found: {player_name}")
            return
        
        # Find team
        team = session.query(Team).filter(
            Team.full_name.ilike(f"%{team_name}%")
        ).first()
        
        if not team:
            team = session.query(Team).filter(
                Team.abbreviation.ilike(f"%{team_name}%")
            ).first()
        
        if not team:
            print(f"Team not found: {team_name}")
            return
        
        # Detect patterns
        detector = PatternDetector(session)
        patterns = detector.detect_for_player_team(player.player_id, team.team_id)
        
        print(f"\n{'='*60}")
        print(f"PATTERN ANALYSIS: {player.first_name} {player.last_name} vs {team.full_name}")
        print(f"{'='*60}")
        
        if not patterns:
            print("\nNo significant patterns detected (need more matchup history)")
        else:
            for p in patterns:
                strength_bar = "█" * int(p.strength * 10) + "░" * (10 - int(p.strength * 10))
                print(f"\n[{p.pattern.value.upper()}] {p.description}")
                print(f"  Strength: {strength_bar} ({p.strength:.0%})")
                for e in p.evidence:
                    print(f"    • {e}")
        
        print()


def show_matchup(query, save_png=False):
    """Classify player vs team matchup."""
    sys.path.insert(0, 'src')
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sportsprediction.data.features.pattern.classifier import MatchupClassifier, MatchupType
    from sportsprediction.data.models import Player, Team
    
    # Parse query: "player vs team"
    if ' vs ' not in query:
        print("Usage: /matchup <player> vs <team>")
        return
    
    player_name, team_name = query.split(' vs ', 1)
    player_name = player_name.strip()
    team_name = team_name.strip()
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        # Find player
        player = session.query(Player).filter(
            (Player.first_name + ' ' + Player.last_name).ilike(f"%{player_name}%")
        ).first()
        
        if not player:
            print(f"Player not found: {player_name}")
            return
        
        # Find team
        team = session.query(Team).filter(
            Team.full_name.ilike(f"%{team_name}%")
        ).first()
        
        if not team:
            team = session.query(Team).filter(
                Team.abbreviation.ilike(f"%{team_name}%")
            ).first()
        
        if not team:
            print(f"Team not found: {team_name}")
            return
        
        # Classify matchup
        classifier = MatchupClassifier(session)
        result = classifier.classify(player.player_id, team.team_id)
        
        print(f"\n{'='*60}")
        print(f"MATCHUP CLASSIFICATION: {player.first_name} {player.last_name} vs {team.full_name}")
        print(f"{'='*60}")
        
        emoji = {
            MatchupType.EXPLOITABLE: "🟢",
            MatchupType.TOUGH: "🔴",
            MatchupType.NEUTRAL: "⚪",
            MatchupType.UNKNOWN: "❓"
        }
        
        print(f"\n{emoji[result.matchup_type]} TYPE: {result.matchup_type.value.upper()}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        if result.diff_points is not None:
            sign = "+" if result.diff_points > 0 else ""
            print(f"  Points diff: {sign}{result.diff_points:.1f} vs season avg")
        if result.diff_rebounds is not None:
            sign = "+" if result.diff_rebounds > 0 else ""
            print(f"  Rebounds diff: {sign}{result.diff_rebounds:.1f}")
        if result.diff_assists is not None:
            sign = "+" if result.diff_assists > 0 else ""
            print(f"  Assists diff: {sign}{result.diff_assists:.1f}")
        
        if result.matchup_type == MatchupType.EXPLOITABLE:
            print("\n💡 This matchup is FAVORABLE - player performs well vs this team")
        elif result.matchup_type == MatchupType.TOUGH:
            print("\n⚠️  This matchup is TOUGH - this team defends player well")
        elif result.matchup_type == MatchupType.NEUTRAL:
            print("\n➖ No clear advantage either way")
        
        print()

def show_edge(save_png=False):
    """Find edges: our model probability vs Polymarket odds."""
    print("\n=== MODEL vs MARKET EDGES ===\n")
    
    # Get today's games from Polymarket
    try:
        from playwright.sync_api import sync_playwright
        import re
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://polymarket.com/sports/nba/games', timeout=20000)
            page.wait_for_timeout(3000)
            text = page.inner_text('body')
            browser.close()
        
        team_map = {
            'ind': 'Pacers', 'mil': 'Bucks', 'dal': 'Mavericks', 'cle': 'Cavaliers',
            'det': 'Pistons', 'tor': 'Raptors', 'por': 'Trail Blazers', 'phi': '76ers',
            'gsw': 'Warriors', 'nyk': 'Knicks', 'min': 'Timberwolves', 'okc': 'Thunder',
            'uta': 'Jazz', 'sac': 'Kings', 'lal': 'Lakers', 'lac': 'Clippers',
            'pho': 'Suns', 'den': 'Nuggets', 'mem': 'Grizzlies', 'nop': 'Pelicans',
            'bos': 'Celtics', 'mia': 'Heat', 'atl': 'Hawks', 'orl': 'Magic',
            'chi': 'Bulls', 'cha': 'Hornets', 'was': 'Wizards', 'hou': 'Rockets',
            'sas': 'Spurs', 'bkn': 'Nets'
        }
        
        # Full name to ELO ID mapping
        team_to_elo = {
            'Pacers': '1610612754', 'Bucks': '1610612749', 'Mavericks': '1610612742', 
            'Cavaliers': '1610612739', 'Pistons': '1610612741', 'Raptors': '1610612761',
            'Trail Blazers': '1610612757', '76ers': '1610612755', 'Warriors': '1610612744',
            'Knicks': '1610612752', 'Timberwolves': '1610612750', 'Thunder': '1610612760',
            'Jazz': '1610612762', 'Kings': '1610612758', 'Lakers': '1610612747',
            'Clippers': '1610612746', 'Suns': '1610612756', 'Nuggets': '1610612743',
            'Grizzlies': '1610612763', 'Pelicans': '1610612740', 'Celtics': '1610612738',
            'Heat': '1610612748', 'Hawks': '1610612737', 'Magic': '1610612753',
            'Bulls': '1610612741', 'Hornets': '1610612766', 'Wizards': '1610612764',
            'Rockets': '1610612745', 'Spurs': '1610612759', 'Nets': '1610612751'
        }
        
        matches = re.findall(r'([A-Za-z]{3})(\d+)¢', text)
        games = []
        seen = set()
        for i in range(0, len(matches)-1, 2):
            if i+1 < len(matches):
                t1, o1 = matches[i]
                t2, o2 = matches[i+1]
                t1l, t2l = t1.lower(), t2.lower()
                if t1l != t2l and t1l in team_map and t2l in team_map:
                    key = tuple(sorted([t1l, t2l]))
                    if key not in seen:
                        seen.add(key)
                        games.append((team_map[t1l], int(o1), team_map[t2l], int(o2)))
        
        if not games:
            print("  No games found")
            return
            
        elo = load_elo()
        
        def elo_prob(rating_a, rating_b):
            return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        
        print("  Comparing ELO model vs Polymarket odds:\n")
        
        edges = []
        for t1, o1, t2, o2 in games[:5]:
            t1_elo = team_to_elo.get(t1)
            t2_elo = team_to_elo.get(t2)
            
            if t1_elo and t2_elo and t1_elo in elo and t2_elo in elo:
                # ELO is nested dict with 'elo' key
                r1 = elo[t1_elo].get('elo', 1500)
                r2 = elo[t2_elo].get('elo', 1500)
                our_prob = elo_prob(r1, r2) * 100
                
                # Compare our team1 win prob to market's team1 odds
                market_prob = o1
                edge = our_prob - market_prob
                edges.append((t1, t2, our_prob, market_prob, edge))
        
        edges.sort(key=lambda x: abs(x[4]), reverse=True)
        
        for t1, t2, our, market, edge in edges:
            direction = "⬆️" if edge > 0 else "⬇️"
            print(f"  {t1} vs {t2}")
            print(f"    ELO model: {our:5.1f}%")
            print(f"    Market:    {market:5.1f}%")
            print(f"    Edge:      {edge:+5.1f}% {direction}")
            if abs(edge) > 5:
                print(f"    ⚠️  STRONG EDGE!" if edge > 0 else f"    ⚠️  VALUE ON OTHER SIDE")
            print()
        
        print("  (Polymarket + ELO)")
        
    except Exception as e:
        print(f"  Error: {e}")


def show_momentum(save_png=False):
    """Show who's hot and who's cold."""
    sys.path.insert(0, 'src')
    from sportsprediction.data.models.base import create_db_engine
    from sportsprediction.data.db import get_session
    from sportsprediction.data.models import BoxScore, Game, Player
    from sqlalchemy import func
    import matplotlib.pyplot as plt
    
    engine = create_db_engine("data/hermes.db")
    with get_session(engine) as session:
        # Get last 5 games for all players, aggregate points
        recent = (
            session.query(
                Player.player_id,
                Player.first_name,
                Player.last_name,
                func.avg(BoxScore.points).label('avg_pts'),
                func.count(BoxScore.game_id).label('games')
            )
            .join(BoxScore, Player.player_id == BoxScore.player_id)
            .join(Game, BoxScore.game_id == Game.game_id)
            .filter(Game.game_date > '2025-12-01')
            .group_by(Player.player_id, Player.first_name, Player.last_name)
            .having(func.count(BoxScore.game_id) >= 5)
            .order_by(func.avg(BoxScore.points).desc())
            .limit(20)
            .all()
        )
        
        print(f"\n{'='*60}")
        print("MOMENTUM TRACKER - Who's Hot/Cold (Last 2+ Months)")
        print(f"{'='*60}")
        
        print("\n🔥 TOP SCORERS (Last 5+ games):")
        print(f"{'Player':<25} {'Avg PPG':>10} {'Games':>6}")
        print("-" * 43)
        for r in recent[:10]:
            print(f"{r.first_name} {r.last_name:<18} {r.avg_pts:>10.1f} {r.games:>6}")
        
        # Cold players
        cold = recent[-10:] if len(recent) >= 10 else recent
        print("\n❄️  COLD (Lower scoring):")
        print(f"{'Player':<25} {'Avg PPG':>10} {'Games':>6}")
        print("-" * 43)
        for r in cold:
            print(f"{r.first_name} {r.last_name:<18} {r.avg_pts:>10.1f} {r.games:>6}")
        
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# LLM INTEGRATION (OpenRouter)
# ═══════════════════════════════════════════════════════════════════════════════


def _get_api_key():
    """Get OpenRouter API key from ~/.hermes/.env."""
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("OPENROUTER_API_KEY")


NBA_TOOLS_CONTEXT = """You are NBA Analyst, an AI assistant embedded in a terminal CLI with a live SQLite database of NBA stats.

CRITICAL RULES:
1. You do NOT have direct access to the database. You CANNOT look up stats yourself.
2. NEVER invent or guess specific numbers (points, percentages, records, etc). You don't know current stats.
3. To answer data questions, output the correct /command — the CLI will auto-execute it and show real data.
4. Put each command on its own line starting with exactly / so the CLI can detect and run it.
5. Keep prose brief — 1-3 sentences of context, then the commands. No long paragraphs.

Available commands:
  /elo                          - Team ELO power rankings
  /games                        - Recent game scores
  /predict <team1> <team2>      - Win probability (e.g. /predict Celtics Lakers)
  /odds                         - Polymarket championship odds
  /teams                        - List all NBA teams
  /player <name>                - Player season stats (use last name: /player Curry)
  /team <name>                  - Team season record (e.g. /team Lakers)
  /compare <p1> vs <p2>         - Compare two players (e.g. /compare Curry vs LeBron)
  /trend <name>                 - Player PPG trend (e.g. /trend Luka)
  /top <stat>                   - League leaders: pts, reb, ast, stl, blk, 3pm
  /shot <name>                  - Player shot chart
  /pattern <player> vs <team>   - Player matchup patterns
  /matchup <player> vs <team>   - Matchup classification (EXPLOITABLE/TOUGH/NEUTRAL)
  /edge                         - Model vs market betting edges
  /momentum                     - Hot/cold streaks

Example responses:

User: "who is the best team right now?"
Assistant: Here are the current power rankings:
/elo

User: "how is curry doing this season?"
Assistant: Let me pull up Curry\'s stats:
/player Curry

User: "who wins tonight between celtics and lakers?"
Assistant: Let me run the prediction model:
/predict Celtics Lakers

User: "who has steph curry performed best against?"
Assistant: I\'ll check his matchup patterns. Pick a specific team to analyze, or start with his overall stats:
/player Curry
/momentum
"""


def llm_ask(prompt):
    """Send natural language query to LLM via OpenRouter."""
    import requests

    api_key = _get_api_key()
    if not api_key:
        return "No API key found. Set OPENROUTER_API_KEY in ~/.hermes/.env"

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/NousResearch/HermesAgent",
                "X-Title": "NBA Analyst",
            },
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": [
                    {"role": "system", "content": NBA_TOOLS_CONTEXT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 512,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM error: {e}"


def _extract_commands(text: str) -> tuple[str, list[str]]:
    """
    Parse LLM response into (prose, commands_to_execute).
    Detects lines starting with /command and separates them from prose.
    """
    import re
    valid_cmds = {
        "elo", "games", "predict", "odds", "teams", "player", "team",
        "compare", "trend", "top", "heatmap", "shot", "pattern",
        "matchup", "edge", "momentum", "update",
    }

    prose_lines = []
    commands = []

    for line in text.split("\n"):
        stripped = line.strip()
        match = re.match(r"^/(\w+)", stripped)
        if match and match.group(1).lower() in valid_cmds:
            commands.append(stripped)
        else:
            prose_lines.append(line)

    prose = "\n".join(prose_lines).strip()
    return prose, commands



# ═══════════════════════════════════════════════════════════════════════════════
# MAIN INPUT LOOP
# ═══════════════════════════════════════════════════════════════════════════════


def build_prompt_message() -> str:
    return f"\033[38;2;255;140;0m›\033[0m "


def run_cli() -> None:
    """Main CLI entry point."""
    console = Console()
    gif_path = find_gif_path()

    # ── Phase 1: Animated startup (if GIF available) ──
    if gif_path:
        try:
            frames = load_gif_frames(gif_path, step=2)
            if frames:
                play_startup_animation(frames, duration_secs=3.5)
        except Exception:
            pass

    # ── Phase 2: Static banner ──
    build_welcome_banner(console, gif_path)

    # ── Phase 3: Load data ──
    console.print(
        Text("  Loading data...", style=Style(color=Colors.DIM))
    )
    elo_data = load_elo()
    teams_data = load_teams()
    console.print(
        Text(
            f"  ✓ Loaded {len(teams_data)} teams, {len(elo_data)} ELO ratings\n",
            style=Style(color=Colors.AMBER),
        )
    )

    # ── Command dispatcher (reused for direct input AND LLM auto-execute) ──
    def dispatch(cmd_str: str) -> str | None:
        """
        Execute a slash command string like '/player Curry' or '/elo'.
        Returns 'quit' to signal exit, None otherwise.
        """
        nonlocal elo_data

        if not cmd_str.startswith("/"):
            return None
        raw = cmd_str[1:]
        parts = raw.split(" ", 1)
        cmd_name = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd_name in ("quit", "exit", "q"):
            return "quit"

        elif cmd_name == "help":
            print(HELP)
        elif cmd_name == "clear":
            os.system("clear" if os.name != "nt" else "cls")
            build_welcome_banner(console, gif_path)
        elif cmd_name == "elo":
            save_png = "--png" in arg
            arg = arg.replace("--png", "").strip()
            show_elo(teams_data, elo_data, save_png)
        elif cmd_name == "games":
            show_games(teams_data)
        elif cmd_name == "predict":
            show_predict(teams_data, elo_data, arg)
        elif cmd_name == "odds":
            show_odds()
        elif cmd_name == "teams":
            show_teams(teams_data)
        elif cmd_name == "player":
            save_png = "--png" in arg
            show_player(arg, save_png)
        elif cmd_name == "team":
            save_png = "--png" in arg
            show_team(arg, save_png)
        elif cmd_name == "compare":
            save_png = "--png" in arg
            show_compare(arg, save_png)
        elif cmd_name == "trend":
            save_png = "--png" in arg
            show_trend(arg, save_png)
        elif cmd_name == "top":
            save_png = "--png" in arg
            show_top(arg, save_png)
        elif cmd_name == "heatmap":
            save_png = "--png" in arg
            show_heatmap(save_png)
        elif cmd_name == "shot":
            save_png = "--png" in arg
            show_shot(arg, save_png)
        elif cmd_name == "pattern":
            save_png = "--png" in arg
            show_pattern(arg, save_png)
        elif cmd_name == "matchup":
            save_png = "--png" in arg
            show_matchup(arg, save_png)
        elif cmd_name == "edge":
            save_png = "--png" in arg
            show_edge(save_png)
        elif cmd_name == "momentum":
            save_png = "--png" in arg
            show_momentum(save_png)
        elif cmd_name == "update":
            update_elo()
            elo_data = load_elo()
        else:
            console.print(
                Text(
                    f"  Unknown: /{cmd_name} — Type /help for commands",
                    style=Style(color="#FF4444"),
                )
            )
        return None

    # ── Set up prompt_toolkit ──
    command_list = list(COMMANDS.keys())
    completer = WordCompleter(command_list, sentence=True)
    pt_style = PTStyle.from_dict({"prompt": "#FF8C00 bold"})
    session: PromptSession = PromptSession(
        completer=completer,
        style=pt_style,
        complete_while_typing=True,
    )

    # ── Input loop ──
    while True:
        try:
            user_input = session.prompt(
                ANSI(build_prompt_message()),
            ).strip()

            if not user_input:
                continue

            # ── Natural language (no / prefix) → LLM + auto-execute ──
            if not user_input.startswith("/"):
                console.print(
                    Text("  Thinking...\n", style=Style(color=Colors.AMBER))
                )
                try:
                    answer = llm_ask(user_input)
                    prose, commands = _extract_commands(answer)

                    # Print the LLM's prose explanation
                    if prose:
                        console.print(f"  {prose}\n")

                    # Auto-execute any commands the LLM suggested
                    if commands:
                        console.print(
                            Text(
                                f"  ▸ Running {len(commands)} command{'s' if len(commands) > 1 else ''}...\n",
                                style=Style(color=Colors.CYAN),
                            )
                        )
                        for cmd in commands:
                            console.print(
                                Text(f"  {cmd}", style=Style(color=Colors.ORANGE, bold=True))
                            )
                            try:
                                result = dispatch(cmd)
                                if result == "quit":
                                    return
                            except Exception as e:
                                console.print(
                                    Text(f"  Error running {cmd}: {e}", style=Style(color="#FF4444"))
                                )
                            print()  # spacing between commands
                    elif not prose:
                        console.print(
                            Text("  No response from LLM.", style=Style(color=Colors.DIM))
                        )

                except Exception as e:
                    console.print(
                        Text(f"  Error: {e}", style=Style(color="#FF4444"))
                    )
                continue

            # ── Direct slash command ──
            result = dispatch(user_input)
            if result == "quit":
                console.print(
                    Text(
                        "\n  👋 Game over. See you next tip-off.\n",
                        style=Style(color=Colors.ORANGE),
                    )
                )
                break

        except KeyboardInterrupt:
            console.print(
                Text(
                    "\n  ⏸  Press Ctrl+C again or type /quit to exit.",
                    style=Style(color=Colors.DIM),
                )
            )
        except EOFError:
            break


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Entry point for the `nba` command."""
    try:
        run_cli()
    except Exception as e:
        sys.stdout.write("\033[?25h")  # Show cursor
        console = Console()
        console.print(f"\n[bold red]Fatal error:[/] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
