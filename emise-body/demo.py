#!/usr/bin/env python3
"""Scripted proof that the phext control loop closes.

Reset -> Emise writes a motor command via command.py -> robot.py ticks ->
print the sense scrolls -> repeat: turn/move to the rose, pick it up,
wave, and speak. Watch proprioception and vision change each tick.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robot import DEFAULT_PHEXT, SENSES, fmt, load_body

HERE = os.path.dirname(os.path.abspath(__file__))

def run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr); sys.exit(r.returncode)
    return r.stdout.strip()

def show_senses(step):
    scrolls = load_body(DEFAULT_PHEXT)
    print(f"\n--- senses after: {step} ---")
    for name, c in SENSES.items():
        print(f"  {name}: {scrolls.get(c, '').replace(chr(10), ' | ')}")

def act(channel, command):
    print(f"\n>>> Emise writes [{channel}] {command}")
    print("   " + run(os.path.join(HERE, "command.py"), channel, command))
    print("   " + run(os.path.join(HERE, "robot.py")).splitlines()[0])
    show_senses(f"{channel}: {command}")

def main():
    print(run(os.path.join(HERE, "robot.py"), "--reset"))
    show_senses("reset (start: (2, 3), facing east; rose at (5, 4))")
    act("intent", "intent: go to the rose, pick it up, greet the room")
    act("locomotion", "turn left")      # east -> north
    act("locomotion", "move forward")   # (2,3) -> (2,4)
    act("locomotion", "turn right")     # north -> east
    act("locomotion", "move forward")   # -> (3,4)
    act("locomotion", "move forward")   # -> (4,4)
    act("locomotion", "move forward")   # -> (5,4) — with the rose
    act("paw", "pick up rose")
    act("paw", "wave")
    act("voice", "say: I found the rose")
    print("\nDemo complete: the loop closed — commands written in phext were")
    print("executed by the body, and the senses written back in phext changed.")

if __name__ == "__main__":
    main()
