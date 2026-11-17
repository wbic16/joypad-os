#!/usr/bin/env python3
"""Emise's virtual robot body v0 — phext is the nervous system.

Senses (ch.1): the body writes, Emise reads.
Motors (ch.2): Emise writes, the body executes, then clears (consumed) —
except intent, which is provenance and is never cleared.
All coordinates are 1-based. Phext delimiters/logic follow
~/workspace/phext/parse_phext.py (0x17 scroll, 0x18 section, 0x19 chapter, …).

Usage: robot.py [--reset] [body.phext]    # one tick (or reset with no tick)
State lives *only* in body.phext: position/facing/battery/holding are
recovered each tick by parsing the proprioception scroll.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PHEXT = os.path.join(HERE, "body.phext")

# --- phext core (same logic as ~/workspace/phext/parse_phext.py) ----------
LEVELS = [  # highest -> lowest
    ("library", 0x01), ("shelf", 0x1F), ("series", 0x1E),
    ("collection", 0x1D), ("volume", 0x1C), ("book", 0x1A),
    ("chapter", 0x19), ("section", 0x18), ("scroll", 0x17),
]
DELIM_TO_LEVEL = {byte: i for i, (_, byte) in enumerate(LEVELS)}
LEVEL_BYTE = {name: byte for name, byte in LEVELS}

def fmt(coord):
    return f"{coord[0]}.{coord[1]}.{coord[2]}/{coord[3]}.{coord[4]}.{coord[5]}/{coord[6]}.{coord[7]}.{coord[8]}"

def parse_bytes(data):
    """bytes -> {coord_tuple: text}, exactly as parse_phext.py walks it."""
    coord, buf, out = [1] * 9, bytearray(), {}
    for b in data:
        lvl = DELIM_TO_LEVEL.get(b)
        if lvl is None:
            buf.append(b)
        else:
            out[tuple(coord)] = bytes(buf).decode("utf-8")
            buf = bytearray()
            coord[lvl] += 1
            for j in range(lvl + 1, 9):
                coord[j] = 1
    out[tuple(coord)] = bytes(buf).decode("utf-8")
    return out

def load_body(path):
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        return parse_bytes(f.read())

def serialize(scrolls):
    """{coord_tuple: text} -> phext bytes, targets emitted in sorted order.

    Between scrolls, emit the delimiter for the most-significant differing
    level (repeated if jumping >1); each emission flushes the prior scroll
    in the parser and resets all lower levels to 1 — as the parser defines.
    """
    targets = sorted(c for c, t in scrolls.items() if t != "" or c in ALL_COORDS)
    out, cur, first = bytearray(), [1] * 9, True
    for target in targets:
        if not first:
            while tuple(cur) != target:
                i = next(i for i in range(9) if cur[i] != target[i])
                assert cur[i] < target[i], f"coordinates out of order: {cur} -> {target}"
                out.append(LEVELS[i][1])
                cur[i] += 1
                for j in range(i + 1, 9):
                    cur[j] = 1
        assert tuple(cur) == target, f"cannot reach {fmt(target)} from {fmt(tuple(cur))}"
        out += scrolls.get(target, "").encode("utf-8")
        first = False
    return bytes(out)

def save_body(path, scrolls):
    for c in ALL_COORDS:
        scrolls.setdefault(c, "")
    data = serialize(scrolls)
    # Round-trip self-check: our own bytes must parse back to the same map.
    back = parse_bytes(data)
    for c in ALL_COORDS:
        assert back.get(c, "") == scrolls[c], f"round-trip mismatch at {fmt(c)}"
    with open(path, "wb") as f:
        f.write(data)

def coord(chapter, section, scroll):
    return (1, 1, 1, 1, 1, 1, chapter, section, scroll)

VISION, HEARING, PROPRIO, TOUCH = (coord(1, 1, n) for n in (1, 2, 3, 4))
LOCO, PAW, VOICE, INTENT = (coord(2, 1, n) for n in (1, 2, 3, 4))
ALL_COORDS = [VISION, HEARING, PROPRIO, TOUCH, LOCO, PAW, VOICE, INTENT]
SENSES = {"vision": VISION, "hearing": HEARING, "proprioception": PROPRIO, "touch": TOUCH}
MOTORS = {"locomotion": LOCO, "paw": PAW, "arm": PAW, "voice": VOICE,
          "face": VOICE, "intent": INTENT}

# --- world -----------------------------------------------------------------
WIDTH, HEIGHT = 7, 5                     # x: 1(west)..7(east), y: 1(south)..5(north)
OBJECTS = {"rose": (5, 4), "open book": (3, 2), "door": (7, 3)}
DIRS = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}
CLOCKWISE = ["north", "east", "south", "west"]
WELCOME_INTENT = "intent: first body — learn the room, find the rose, say hello"

def default_state():
    return {"x": 2, "y": 3, "facing": "east", "battery": 100.0, "holding": []}

def state_from_proprio(text):
    st = default_state()
    if m := re.search(r"position:\s*\((\d+),\s*(\d+)\)", text or ""):
        st["x"], st["y"] = int(m.group(1)), int(m.group(2))
    if m := re.search(r"facing:\s*(\w+)", text or ""):
        if m.group(1) in DIRS: st["facing"] = m.group(1)
    if m := re.search(r"battery:\s*([\d.]+)", text or ""):
        st["battery"] = float(m.group(1))
    if m := re.search(r"holding:\s*(.+)", text or ""):
        held = m.group(1).strip()
        st["holding"] = [] if held in ("", "none") else [h.strip() for h in held.split(",") if h.strip() in OBJECTS]
    return st

def direction_to(st, pos):
    dx, dy = pos[0] - st["x"], pos[1] - st["y"]
    if dx == dy == 0: return "here"
    parts = ([f"{abs(dy)} north" if dy > 0 else f"{abs(dy)} south"] if dy else []) + \
            ([f"{abs(dx)} east" if dx > 0 else f"{abs(dx)} west"] if dx else [])
    return ", ".join(parts)

def senses_for(st, touch_events, said):
    fx, fy = DIRS[st["facing"]]
    ahead, d = [], 1
    while 1 <= st["x"] + fx * d <= WIDTH and 1 <= st["y"] + fy * d <= HEIGHT:
        cell = (st["x"] + fx * d, st["y"] + fy * d)
        for name, pos in OBJECTS.items():
            if pos == cell and name not in st["holding"]:
                ahead.append(f"{name}, {d} cell{'s' if d > 1 else ''} ahead")
        d += 1
    ahead_txt = "; ".join(ahead) if ahead else f"clear for {d - 1} cell{'s' if d - 1 != 1 else ''} to the {st['facing']} wall"
    visible = [f"{n}: {direction_to(st, p)}" for n, p in OBJECTS.items() if n not in st["holding"]]
    vision = (f"facing {st['facing']}. ahead: {ahead_txt}.\n"
              f"visible: {'; '.join(visible)}.\n"
              f"a quiet {WIDTH}x{HEIGHT} room; the door is set in the east wall.")
    hearing = (f"you hear your own voice: \"{said}\"" if said
               else "quiet room tone; faint birdsong outside the door")
    touch = "\n".join(touch_events) if touch_events else "clear: no contact"
    proprio = (f"position: ({st['x']}, {st['y']})\n"
               f"facing: {st['facing']}\n"
               f"battery: {st['battery']:.1f}\n"
               f"holding: {', '.join(st['holding']) if st['holding'] else 'none'}")
    return {VISION: vision, HEARING: hearing, TOUCH: touch, PROPRIO: proprio}

def initial_scrolls():
    st = default_state()
    s = senses_for(st, [], None)
    s.update({LOCO: "", PAW: "", VOICE: "", INTENT: WELCOME_INTENT})
    return s

def tick(path):
    scrolls = load_body(path)
    if not scrolls or PROPRIO not in scrolls:
        scrolls = initial_scrolls()
    st = state_from_proprio(scrolls.get(PROPRIO, ""))
    touch, said, acted = [], None, False

    loco = scrolls.get(LOCO, "").strip().lower()
    if loco:
        acted = True; cost = 0.5
        if loco == "move forward":
            fx, fy = DIRS[st["facing"]]
            nx, ny = st["x"] + fx, st["y"] + fy
            if 1 <= nx <= WIDTH and 1 <= ny <= HEIGHT:
                st["x"], st["y"] = nx, ny
            else:
                touch.append(f"bump: blocked by the {st['facing']} wall")
        elif loco in ("turn left", "turn right"):
            i = CLOCKWISE.index(st["facing"]) + (-1 if loco == "turn left" else 1)
            st["facing"] = CLOCKWISE[i % 4]
        elif loco == "wait":
            cost = 0.1
        else:
            touch.append(f"locomotion: did not understand '{loco}'")
        st["battery"] = max(0.0, st["battery"] - cost)

    paw = scrolls.get(PAW, "").strip()
    if paw:
        acted = True; st["battery"] = max(0.0, st["battery"] - 0.3)
        low = paw.lower()
        if low == "wave":
            touch.append("paw: waved")
        elif low.startswith(("pick up ", "point at ")):
            verb, thing = ("pick up", low[8:].strip()) if low.startswith("pick up ") else ("point at", low[9:].strip())
            thing = "open book" if thing == "book" else thing
            if thing not in OBJECTS:
                touch.append(f"paw: no '{thing}' here to {verb}")
            elif verb == "point at":
                touch.append(f"paw: pointing at the {thing} ({direction_to(st, OBJECTS[thing])})")
            elif thing in st["holding"]:
                touch.append(f"paw: already holding the {thing}")
            elif thing == "door":
                touch.append("paw: the door is fixed in the wall — cannot pick it up")
            elif abs(OBJECTS[thing][0] - st["x"]) + abs(OBJECTS[thing][1] - st["y"]) <= 1 or OBJECTS[thing] == (st["x"], st["y"]):
                st["holding"].append(thing)
                touch.append(f"paw: picked up the {thing}")
            else:
                touch.append(f"paw: the {thing} is out of reach ({direction_to(st, OBJECTS[thing])})")
        else:
            touch.append(f"paw: did not understand '{paw}'")

    voice = scrolls.get(VOICE, "").strip()
    if voice:
        acted = True; st["battery"] = max(0.0, st["battery"] - 0.2)
        said = voice[5:].strip() if voice.lower().startswith("say:") else voice

    scrolls.update(senses_for(st, touch, said))
    for c in (LOCO, PAW, VOICE):       # consumed; INTENT is preserved
        scrolls[c] = ""
    save_body(path, scrolls)
    return scrolls, acted

def main(argv):
    args = [a for a in argv[1:] if a != "--reset"]
    path = args[0] if args else DEFAULT_PHEXT
    if "--reset" in argv:
        save_body(path, initial_scrolls())
        print(f"reset: body written to {path}")
        return 0
    scrolls, acted = tick(path)
    print("tick: " + ("executed pending motor command(s)" if acted else "no pending motor commands"))
    for name, c in SENSES.items():
        print(f"[{name} @ {fmt(c)}] {scrolls[c]}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
