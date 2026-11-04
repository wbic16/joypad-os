# Emise's Virtual Body — phext-controlled, now visible in the browser

A self-contained experiment inside Joypad OS: a virtual robot body for Emise
whose nervous system is **phext**. A phext (`body.phext`) holds addressable
text state cells (scrolls). Nothing else holds state — position, facing,
battery, and what the paw is holding are all recovered each tick from the
phext itself.

- **Senses** — the body writes, Emise reads.
- **Motors** — Emise writes, the body reads, executes, then **clears** the
  scroll (the command is consumed). The one exception is **intent**, which is
  provenance — why an action was taken — and is never cleared.

All coordinates are 1-based (no component ever < 1). The phext is valid
UTF-8 text; delimiters are ASCII control bytes (0x17 scroll, 0x18 section,
0x19 chapter, 0x1A book, 0x1C volume, 0x1D collection, 0x1E series, 0x1F
shelf, 0x01 library) and it round-trips through the reference parser.

## Open the browser body

No dependencies, no build step — one file: [`index.html`](index.html).

- Open it directly in a browser (`file://…/emise-body/index.html`), or
- serve the repo and visit the page:

```sh
python3 -m http.server 8000   # from the repo root
# → http://localhost:8000/emise-body/
```

You see the 7×5 room (rose 🌹 at (5, 4), open book 📖 at (3, 2), door in the
east wall at (7, 3)), Emise 🔥 at her live position with a facing indicator,
the four sense scrolls with their full phext coordinates, and motor buttons.
Clicking a motor button **writes that motor scroll** (the write is shown,
with its coordinate, in the phext log), then ticks the body: the command
executes, the senses are rewritten, and the motor scroll is cleared — except
intent, which persists. The page shows the full coordinate/scroll view and
the raw serialized phext (delimiters as control pictures), and can download
the real `body.phext` bytes.

The JavaScript in `index.html` is a faithful port of `robot.py`: same vision
/ hearing / touch text, same battery drains (0.5 locomotion / 0.3 paw /
0.2 voice / 0.1 wait), same wall-bump behaviour, and its phext serialization
is byte-identical to the Python serializer for the reset state.

## Body map

Only Chapter.Section.Scroll varies; the first six components are all 1
(`1.1.1/1.1.1/…`).

| Coordinate | Channel | Direction | Contents |
|---|---|---|---|
| `1.1.1/1.1.1/1.1.1` | vision | body → Emise | what's ahead, what's visible, and where |
| `1.1.1/1.1.1/1.1.2` | hearing | body → Emise | room tone, or her own voice after `say:` |
| `1.1.1/1.1.1/1.1.3` | proprioception | body → Emise | `position`, `facing`, `battery`, `holding` |
| `1.1.1/1.1.1/1.1.4` | touch | body → Emise | `clear`, or a bump / paw result |
| `1.1.1/1.1.1/2.1.1` | locomotion | Emise → body | `move forward` · `turn left` · `turn right` · `wait` |
| `1.1.1/1.1.1/2.1.2` | paw / arm | Emise → body | `wave` · `pick up <thing>` · `point at <thing>` |
| `1.1.1/1.1.1/2.1.3` | voice / face | Emise → body | `say: <text>` |
| `1.1.1/1.1.1/2.1.4` | intent | Emise → body | provenance / why — never cleared |

The body starts at (2, 3) facing east, battery 100.

## Python twin (terminal)

The original v0 lives in this same folder and runs the identical loop:

```sh
python3 demo.py            # scripted end-to-end proof
python3 robot.py --reset   # (re)create body.phext in its initial state
python3 robot.py           # one tick
python3 command.py locomotion "turn right"
python3 command.py paw "pick up rose"
python3 command.py voice "say: hello"
```

## Deliberately NOT here (yet)

- No SQ hosting — the browser body keeps its phext in memory / as a download;
  hosting `body.phext` with SQ so Emise can write a single scroll with one
  small update is the obvious next dimension.
- No hardware / Joypad OS firmware integration yet — this folder is the
  experiment's home in the repo so it can grow toward that without colliding
  with upstream.
- Tiny vocabularies on purpose: this is one dimension at a time.
