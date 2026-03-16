#!/usr/bin/env python3
"""NBA ANALYSIS banner — 3D block style with orange gradient.

Creates a banner similar to the ALEX SHALLER style:
- Block characters (Unicode block elements)
- 3D depth/shadow effect extending down and right
- Orange gradient from bright (top) to dark (bottom)

Can run directly: python3 banner.py
"""

import os
import sys

# ANSI colors for orange gradient
CSI = "\033["
ORANGE_BRIGHT = CSI + "38;2;255;140;40m"   # Bright orange (top)
ORANGE_MID = CSI + "38;2;255;90;30m"       # Medium orange (middle)  
ORANGE_DARK = CSI + "38;2;200;60;20m"      # Dark orange (bottom)
SHADOW_COLOR = CSI + "38;2;120;40;15m"    # Deep shadow
RESET = CSI + "0m"

# Block letter patterns - hand-crafted for 3D look
LETTERS = {
    'A': [' ████ ', '█    █', '█████ ', '█    █', '█    █'],
    'B': ['█████ ', '█    █', '█████ ', '█    █', '█████ '],
    'C': [' ████ ', '█    █', '█    █', '█    █', ' ████ '],
    'D': ['█████ ', '█    █', '█    █', '█    █', '█████ '],
    'E': ['██████', '█    █', '█████ ', '█    █', '██████'],
    'F': ['██████', '█    █', '█████ ', '█    █', '█    █'],
    'G': [' ████ ', '█    █', '█  ███', '█    █', ' ████ '],
    'H': ['█    █', '█    █', '██████', '█    █', '█    █'],
    'I': ['██████', '  ██  ', '  ██  ', '  ██  ', '██████'],
    'J': ['    ██', '    ██', '    ██', '█   ██', ' ████ '],
    'K': ['█    █', '█  ██ ', '████  ', '█  ██ ', '█    █'],
    'L': ['█    █', '█    █', '█    █', '█    █', '██████'],
    'M': ['█    █', '██  ██', '█ ██ █', '█    █', '█    █'],
    'N': ['█    █', '██   █', '█ █  █', '█  ██ ', '█    █'],
    'O': [' ████ ', '█    █', '█    █', '█    █', ' ████ '],
    'P': ['█████ ', '█    █', '█████ ', '█    █', '█    █'],
    'Q': [' ████ ', '█    █', '█ ██ █', '█  ██ ', ' ██ █ '],
    'R': ['█████ ', '█    █', '█████ ', '█  ██ ', '█    █'],
    'S': [' ████ ', '█    █', ' ████ ', '    ██', '██████'],
    'T': ['██████', '  ██  ', '  ██  ', '  ██  ', '  ██  '],
    'U': ['█    █', '█    █', '█    █', '█    █', ' ████ '],
    'V': ['█    █', '█    █', '█    █', ' ██  █', '  ██  '],
    'W': ['█    █', '█    █', '█ ██ █', '██  ██', '█    █'],
    'X': ['█    █', ' ██  █', '  ██  ', ' ██  █', '█    █'],
    'Y': ['█    █', ' ██  █', '  ██  ', '  ██  ', '  ██  '],
    'Z': ['██████', '   ██ ', ' ██   ', '██    ', '██████'],
    ' ': ['      ', '      ', '      ', '      ', '      '],
    '-': ['      ', '      ', '██████', '      ', '      '],
}

def get_color(row: int, total: int) -> str:
    """Get gradient color based on row position."""
    if total <= 0:
        return ORANGE_BRIGHT
    ratio = row / total
    if ratio < 0.35:
        return ORANGE_BRIGHT
    elif ratio < 0.65:
        return ORANGE_MID
    return ORANGE_DARK

def build_banner(text: str) -> tuple:
    """Build front and shadow layers from text."""
    chars = [c.upper() for c in text]
    
    # Get max height
    max_h = 0
    char_patterns = []
    for c in chars:
        pat = LETTERS.get(c, LETTERS[' '])
        char_patterns.append(pat)
        max_h = max(max_h, len(pat))
    
    # Build front and shadow layers
    front = []
    shadow = []
    
    for row in range(max_h):
        f_line = ""
        s_line = ""
        for i, (c, pat) in enumerate(zip(chars, char_patterns)):
            if row < len(pat):
                line = pat[row]
                f_line += line
                # Shadow: shift right, dimmer chars
                s_line += " " + line.replace("█", "▓").replace("▀", "░")
            else:
                f_line += " " * len(pat[0]) if pat else " "
                s_line += " " * (len(pat[0]) + 1) if pat else " "
        
        front.append(f_line.rstrip())
        shadow.append(s_line.rstrip())
    
    return front, shadow

def generate_banner(text: str = "NBA ANALYSIS") -> str:
    """Generate 3D block banner with gradient and shadow."""
    front, shadow = build_banner(text)
    lines = []
    
    # Shadow layer (darker, offset)
    for s_row in shadow:
        if s_row.strip():
            lines.append(SHADOW_COLOR + s_row + " " + RESET)
    
    # Front layer with gradient
    for i, f_row in enumerate(front):
        if f_row.strip():
            color = get_color(i, len(front))
            lines.append(color + f_row + RESET)
    
    return "\n".join(lines)

def generate_banner_plain(text: str = "NBA ANALYSIS") -> str:
    """Generate without colors."""
    front, shadow = build_banner(text)
    lines = []
    for s_row in shadow:
        if s_row.strip():
            lines.append(s_row + " ")
    for f_row in front:
        if f_row.strip():
            lines.append(f_row)
    return "\n".join(lines)

if __name__ == "__main__":
    term = os.environ.get("TERM", "")
    if term and term != "dumb":
        print(generate_banner())
    else:
        print(generate_banner_plain())