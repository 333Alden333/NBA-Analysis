#!/usr/bin/env python3
"""NBA ANALYSIS banner - pagga font with orange gradient."""

import os
import sys

# ANSI colors
CSI = '\033['
ORANGE_BRIGHT = CSI + '38;2;255;110;30m'   # Bright orange (top)
ORANGE_MID = CSI + '38;2;255;70;25m'        # Medium orange (middle)
ORANGE_DARK = CSI + '38;2;160;40;12m'       # Dark orange (bottom)
RESET = CSI + '0m'

def generate_banner():
    """Generate NBA ANALYSIS banner with pagga font and gradient."""
    try:
        from pyfiglet import Figlet
        f = Figlet(font='pagga')
        text = f.renderText('NBA ANALYSIS')
    except:
        return "NBA ANALYSIS"
    
    lines = text.split('\n')
    non_empty = [l for l in lines if l.strip()]
    total = len(non_empty)
    
    colored = []
    count = 0
    for line in lines:
        if not line.strip():
            colored.append(line)
            continue
        
        # Gradient: top lines bright, bottom lines dark
        if count < total * 0.4:
            color = ORANGE_BRIGHT
        elif count < total * 0.7:
            color = ORANGE_MID
        else:
            color = ORANGE_DARK
        
        colored.append(color + line + RESET)
        count += 1
    
    return '\n'.join(colored)

def generate_banner_plain():
    """Generate plain text banner without colors."""
    try:
        from pyfiglet import Figlet
        f = Figlet(font='pagga')
        return f.renderText('NBA ANALYSIS')
    except:
        return "NBA ANALYSIS"

def create_banner(text):
    """Create banner for arbitrary text with gradient."""
    try:
        from pyfiglet import Figlet
        f = Figlet(font='pagga')
        text = f.renderText(text)
    except:
        return text
    
    lines = text.split('\n')
    non_empty = [l for l in lines if l.strip()]
    total = len(non_empty)
    
    colored = []
    count = 0
    for line in lines:
        if not line.strip():
            colored.append(line)
            continue
        
        if count < total * 0.4:
            color = ORANGE_BRIGHT
        elif count < total * 0.7:
            color = ORANGE_MID
        else:
            color = ORANGE_DARK
        
        colored.append(color + line + RESET)
        count += 1
    
    return '\n'.join(colored)

def create_banner_plain(text):
    """Plain text version."""
    try:
        from pyfiglet import Figlet
        f = Figlet(font='pagga')
        return f.renderText(text)
    except:
        return text

if __name__ == '__main__':
    term = os.environ.get('TERM', '')
    if term != 'dumb' and term:
        print(generate_banner())
    else:
        print(generate_banner_plain())
