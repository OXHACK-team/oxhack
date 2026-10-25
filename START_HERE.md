# Start CHRONO ARENA

A webcam-controlled sports arcade for the TIME theme. Six games, solo play,
an offline AI rival, two simultaneous players and 2–4 player turn-taking.

## On this team's laptop

Open **Launch CHRONO ARENA.cmd** for webcam play, or **Launch Demo.cmd** to
try the games with a keyboard and mouse. The existing environment can be used.

## On another Windows computer

1. Extract the ZIP completely. Open the extracted **oxhack** folder.
2. Install **64-bit Python 3.11** with the Python launcher if it is not installed.
   The tested version is [Python 3.11.9](https://www.python.org/downloads/release/python-3119/).
3. Double-click **Setup CHRONO ARENA.cmd**. Internet is needed for the Python
   packages on this first setup. Let it finish before launching.
4. Open **Launch CHRONO ARENA.cmd** or **Launch Demo.cmd**.

Both tracking models and all artwork are included. After setup the game works
offline. A copied `.venv` from someone else's computer is not needed.

## On a Mac (Apple Silicon or Intel)

Requires macOS 13 (Ventura) or later and **Python 3.11** from
[python.org](https://www.python.org/downloads/release/python-3119/).
Extract the latest ZIP. Open Terminal, type `cd `, drag the extracted **oxhack**
folder into Terminal, then press Return. Run:

```bash
bash "Setup Mac.command"
bash "Launch Mac.command"
```

Setup needs internet once. For keyboard play use `bash "Launch Demo Mac.command"`.
After setup you can also double-click the Mac launch files. If Finder blocks
one, run it from Terminal using the commands above.
Allow camera access for Terminal/Python when asked. If you denied it, enable
the launching app under **System Settings > Privacy & Security > Camera**, then
quit and reopen that app. F2 switches to demo without a camera.
Mac launchers start windowed; F11 toggles fullscreen (Fn+F11 on some keyboards).
The separate `.venv-mac` environment prevents a copied Windows environment
from breaking installation. Intel uses MediaPipe 0.10.21; Apple Silicon uses
0.10.35, based on available official wheels. Mac hardware has not been tested
on this Windows development machine.

## Your first minute

- **Webcam:** keep your head, hands and feet in view. Stand still with arms down,
  then raise either hand above your head for 1.2 seconds.
- **Demo:** press **Enter** to join.
- Choose **QUICK PLAY** for Dodge or Die, or **LET'S PLAY** for all six games.
- Use **PRACTICE MOVES** on the briefing to learn without a score or penalty.
- Point at a button and hold for one second. Mouse clicks and arrows/Enter work too.

For two players, choose a game, then **2 PLAYERS**. P1 stays in the left half of
the mirrored preview; P2 stays in the right. Each person calibrates and raises
a hand. On a long tracking loss, stand still and raise a hand to reconnect;
scores are preserved and a ready countdown resumes the run.

## Controls

| Move | Demo P1 | Demo P2 |
| --- | --- | --- |
| Jog | Space | Left Shift |
| Lean | Left / Right arrows | A / D |
| Duck | C | S |
| Raise / lower a hand | H | T |
| Both hands up | U | W |
| Lightning hand | Mouse over the playfield | W / A / S / D |
| Time Shield | Hold R | Hold F |

In webcam play, copy the demonstrated body movement. To activate Time Shield
in endless survival, cross your wrists onto opposite shoulders and hold briefly.
One charge blocks the next mistake for five active seconds.

**Esc / P** pauses. Point at **RESUME** to continue, or **BANK SCORE / RESULTS**
to save a survival run. **F11** changes fullscreen; **F1** shows diagnostics;
**F2** switches to the keyboard demo. Settings includes **Reduced Motion**.

If the camera is unavailable, close other camera apps and check Windows desktop
camera access, or use the demo. Select the correct camera index in `config.json`
if the desired webcam is not camera 0.

## Verification and source

Run `python scripts\validate_release.py` to check the bundled files before
installing dependencies. With setup complete:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -q
.\.venv\Scripts\python.exe main.py --smoke-test
.\.venv\Scripts\python.exe main.py --survival-test
```

See **README.md** for the game rules, architecture, limitations and validation.
**assets/PROMPTS.md** records the generated-art prompts. Results stay on the
computer in `data/`; webcam images are not saved by the game.
