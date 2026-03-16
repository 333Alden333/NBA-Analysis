#!/usr/bin/env python3
"""NBA Analyst TUI - Hermes Agent style layout."""

import os
import sys
import shutil
import datetime

VERSION = "v1.0.0"

# ANSI colors (for non-Rich fallback)
CSI = '\033['
RESET = CSI + '0m'
ORANGE = CSI + '38;2;255;140;0m'
GOLD = CSI + '38;2;255;215;0m'
CYAN = CSI + '38;2;30;144;255m'
GREY = CSI + '38;2;128;128;128m'
WHITE = CSI + '38;2;255;255;255m'
AMBER = CSI + '38;2;255;180;0m'

# Try Rich, fallback to plain
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

def get_banner():
    """Get the pagga banner for NBA ANALYST with orange gradient."""
    try:
        from pyfiglet import Figlet
        f = Figlet(font='pagga')
        text = f.renderText('NBA ANALYST')
    except:
        return "NBA ANALYST"
    
    # Add orange gradient colors line by line
    lines = text.split('\n')
    non_empty = [l for l in lines if l.strip()]
    total = len(non_empty)
    
    colored = []
    count = 0
    for line in lines:
        if not line.strip():
            colored.append(line)
            continue
        # Gradient: top bright, bottom dark
        if count < total * 0.4:
            color = ORANGE
        elif count < total * 0.7:
            color = AMBER
        else:
            color = CSI + '38;2;180;90;0m'  # Darker orange
        colored.append(color + line + RESET)
        count += 1
    
    return '\n'.join(colored)

def get_tools():
    return ["elo", "games", "predict", "odds", "teams", "player", "team", "compare", 
            "trend", "top", "heatmap", "shot", "pattern", "matchup", "edge", "momentum", "update"]

def get_skills():
    return ["nba-analysis"]

def get_tools_list():
    return get_tools()

def get_skills_list():
    return get_skills()

def render_dunk_ascii():
    """Render the dunk GIF as ASCII - no border, orange player on black."""
    gif_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'data', 'nba_banner_v4.gif'
    )
    
    if not os.path.exists(gif_path):
        return []
    
    try:
        from PIL import Image
        img = Image.open(gif_path)
        
        # Resize for terminal
        width = 40
        aspect = img.height / img.width
        height = int(width * aspect * 0.3)
        img_small = img.resize((width, height))
        
        # Convert to RGB to check actual colors (not palette indices)
        img_rgb = img_small.convert('RGB')
        
        lines = []
        for y in range(img_rgb.height):
            line = ""
            for x in range(img_rgb.width):
                r, g, b = img_rgb.getpixel((x, y))
                
                # Orange player on black background
                # Check if it's orange (high red, some green, low blue)
                if r > 100 and g > 20 and b < 100:
                    if r > 200:
                        line += "█"  # Bright orange
                    elif r > 150:
                        line += "▓"
                    else:
                        line += "▒"
                else:
                    line += " "  # Black = empty
                    
            if line.strip():
                lines.append(line)
        
        return lines
    except Exception as e:
        print(f"Dunk render error: {e}", file=sys.stderr)
        return []

def render_dashboard():
    """Render the main dashboard - Hermes Agent style."""
    banner = get_banner()
    tools = get_tools()
    skills = get_skills()
    cwd = os.getcwd()
    dunk = render_dunk_ascii()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Print banner at top
    print(banner)
    print()
    
    # Plain text two-column layout (works on any Rich version)
    right_lines = []
    right_lines.append(f"{GOLD}Available Tools{RESET}")
    right_lines.append("")
    
    # Tools - one per line
    for tool in tools:
        right_lines.append(f"  {CYAN}{tool}{RESET}")
    
    right_lines.append("")
    right_lines.append(f"{GOLD}Skills{RESET}")
    right_lines.append("")
    
    for skill in skills:
        right_lines.append(f"  {WHITE}{skill}{RESET}")
    
    right_lines.append("")
    right_lines.append(f"{GREY}{len(tools)} tools · {len(skills)} skills · /help for commands{RESET}")
    
    # Side by side
    max_lines = max(len(dunk), len(right_lines))
    while len(dunk) < max_lines:
        dunk.append("")
    while len(right_lines) < max_lines:
        right_lines.append("")
    
    for i in range(max_lines):
        left = dunk[i] if i < len(dunk) else ""
        right = right_lines[i] if i < len(right_lines) else ""
        # Pad left column to fixed width
        left_padded = left.ljust(45)
        print(f"{left_padded}  {right}")
    
    # Model info, path, session
    print()
    print(f"{GREY}Model: NBA Prediction Model v1.0{RESET}")
    print(f"{GREY}Path: {cwd}{RESET}")
    print(f"{GREY}Session: {now}{RESET}")
    print()
    print(f"{AMBER}Welcome to NBA Analyst!{RESET} Type {ORANGE}/help{RESET} for commands.")
    print()

if __name__ == '__main__':
    render_dashboard()
