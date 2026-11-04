#!/usr/bin/env python3
"""Emise writes one motor command into body.phext (all other scrolls preserved).

Usage:
  python3 command.py locomotion "turn right"
  python3 command.py paw "pick up rose"
  python3 command.py voice "say: hello"
  python3 command.py intent "intent: find the rose"

Channels: locomotion | paw (arm) | voice (face) | intent
The command sits in its motor scroll until robot.py ticks and consumes it.
"""
import os, sys
from robot import DEFAULT_PHEXT, MOTORS, fmt, initial_scrolls, load_body, save_body

def main(argv):
    if len(argv) < 3 or argv[1] not in MOTORS:
        print(__doc__.strip())
        return 2
    channel, text = argv[1], " ".join(argv[2:])
    scrolls = load_body(DEFAULT_PHEXT) or initial_scrolls()
    coord = MOTORS[channel]
    scrolls[coord] = text
    save_body(DEFAULT_PHEXT, scrolls)
    print(f"wrote [{channel} @ {fmt(coord)}] {text}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
