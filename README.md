# CHRONO ARENA — Own the next second

Six motion-controlled sports challenges for **OxHack 2026 / TIME**. A webcam
becomes the controller: raise a hand to join, choose a game, and compete with
your timing, movement, memory and stillness.

![The six-game gallery](artifacts/v2/05-six-games.png)

## Run now

The Python environment, models and original artwork are already installed in
this workspace. **No reinstall is needed to run this upgrade.**

- Double-click **Launch CHRONO ARENA.cmd** for fullscreen webcam play.
- Double-click **Launch Demo.cmd** for a windowed keyboard/mouse simulation.

Or open PowerShell in this folder:

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe main.py --demo --windowed
```

In webcam mode, stand back with your head, hands and feet visible. Keep arms
down for calibration, then hold either hand above your head for 1.2 seconds.
In demo mode, hold **H** to simulate that gesture, or press **Enter** to join
quickly. The complete flow is **LET'S PLAY → game → player mode → three rules →
START**. Move a hand over a button and hold for one second; move away after a
selection to rearm. Mouse clicks and arrows/Enter also work.

**USE HAND / USE MOUSE** is always in the top right. Settings lets you switch
between the webcam and keyboard demo without restarting. The bottom of each
game shows its relevant controls. Escape goes back or pauses a running match.

## Six playable games

| Game | What you do | How TIME matters | Default challenge / record |
| --- | --- | --- | --- |
| **Red Light, Green Light** | Jog on green; freeze on red | Choose when to move and when to stop | Finish within 60s; fastest completion |
| **Lightning Strike** | Reach either hand onto an energy orb | Every target expires; chains reward quick follow-through | Score 1,200+ in 36s; highest score |
| **Dodge or Die** | Lean left/right or duck into the safe gap | Anticipate an approaching obstacle before impact | Survive 36s with five shields; highest score |
| **Chrono Sprint** | Jog in place and build speed | Race your previous time and exploit Time Warp windows | Finish within 40s; fastest completion |
| **Timekeeper** | Raise a hand as two rings meet; lower between beats | Synchronize with a repeating clock cycle | Score 650+ in 36s; highest score |
| **Echo Shift** | Watch, remember and repeat poses | Recreate the past, then beat your completion time | Complete 2-, 3-, and 4-pose sequences within 45s |

All six have a briefing, a distinct animated gameplay presentation, countdown,
feedback, outcome, rematch, records and timestamped events. There are no
disabled game placeholders.

Jogging requires alternating leg activity. Shaking one hand does not advance
the running games. On red, significant sustained body movement after a 0.5s
grace period costs seven percentage points of progress. Hysteresis and a
cooldown make ordinary camera jitter less likely to trigger repeated penalties.

Lightning targets require a brief hand hold. Dodge shows the required action
and impact countdown. Timekeeper produces an audio cue when the rings meet;
holding a hand up continuously cannot collect repeated beats. Echo Shift
demonstrates its sequence, hides it during recall, and replays it if recall
times out. Complete all three sequences to win.

## Four ways to play

Every game supports all four modes:

| Mode | Players | How it works |
| --- | --- | --- |
| **Solo** | 1 human | Beat the challenge and your personal best |
| **AI Rival** | 1 human + NOVA | Simultaneous competition against an offline opponent; Easy, Normal or Hard |
| **2 Players** | 2 humans simultaneously | Share one webcam; Player 1 stays in the left half of the mirrored image, Player 2 in the right |
| **Party / 2–4** | 2–4 humans taking turns | Choose the count on the briefing, calibrate each incoming player, and compare the same seeded challenge |

**NOVA** is a local rule-based AI with response delays, movement strength,
timing variation and mistakes. Difficulty changes those parameters. It uses
the same game engines, scoring, limits and seeded challenge patterns. No API
key, paid model call or internet connection is required for opponents.

In two-player mode, both people calibrate and raise a hand in the lobby. Stay
inside your own camera lane. MediaPipe result ordering cannot exchange the
players' controls. Crossing into ambiguous lanes locks control until rejoin.
Player 1 normally drives shared menus; Player 2 can take over if Player 1 has
stepped out. Each competitor has an independent game and score, with clocks
paused together while an unfinished human is not reliably tracked.

If a competitor finishes first, the other continues until their finish or
timeout. The finished competitor can step out without pausing the remaining
round. Party mode asks the next player to step into view and register afresh;
only the active player should be in view. The challenge seed is retained for
every turn. Party standings update after each turn and announce the winner
after everyone has played.

## Controls

| Action | Webcam | Demo Player 1 | Demo Player 2 |
| --- | --- | --- | --- |
| Join | Hold either hand above head | Hold H; Enter skips calibration | Hold T; Enter joins both in lobby |
| Menu selection | Point a hand; hold 1s | Mouse click, or arrows + Enter | Shared menus / remaining tracked player |
| Jog | Alternate knees in place | Hold Space | Hold Left Shift |
| Freeze | Stop moving | Release movement keys | Release movement keys |
| Lean | Lean left / right | Left / Right arrows | A / D |
| Duck | Crouch | C | S |
| Raise one hand / beat | Raise a hand | H | T |
| Both hands up / Echo | Raise both hands | U | W |
| Lightning hand aiming | Reach with either hand | Move mouse over the playfield | W/A/S/D move a hand cursor |

Global: **Escape** back/pause, **P** pause/resume, **F1** diagnostics,
**F2** restart in demo mode, **F3** hand control, **F11** fullscreen/windowed.
Hold **L** in demo to simulate lost tracking. A short interruption recovers;
long gaps require rejoining. Mouse movement switches to mouse control; choose
USE HAND to resume gestures. Keyboard/mouse selection uses click/Enter rather
than dwell.

## Settings and camera positioning

Settings provides movement sensitivity, sound, mirrored preview visibility,
recalibration and webcam/demo switching. Changes save to `config.json`. The
file also exposes player name, camera index/resolution, FPS target, confidence,
smoothing, dwell, timing ranges, grace, movement hysteresis, penalty cooldown,
target radius/hold, beat period/window, lean/crouch thresholds and pose hold.

Default capture is 640×480 at a requested 30 FPS, with rendering capped at 60
FPS. Close other camera applications and enable Windows desktop-camera access
if needed. Change `camera_index` if the intended device is not camera 0.
For two players, move far enough back that both full bodies fit in separate
halves. Keep only the intended players in view. This is spatial continuity
tracking and requires visible bodies; similar people replacing one another at
the same position cannot be identified reliably.

On tracking loss, the game explains that time is on hold. All competitors'
clocks pause together. Return to your position for a short interruption;
**REJOIN / START FRESH** resets calibration and the match after a long gap.
Use the mouse or Enter if tracking is unavailable. Recalibration ends the
current round. A camera disconnect requires reconnecting/restarting capture or
switching to demo. Missing models and capture errors are shown in the UI.

## Installation on another computer

Verified on Windows with **64-bit Python 3.11.9**, MediaPipe **0.10.35**,
OpenCV **4.12.0**, NumPy **2.2.6**, and Pygame CE **2.5.8**. Pygame CE supplies
the `pygame` import; use a fresh environment rather than mixing distributions.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_models.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py
```

Alternatively run `powershell -ExecutionPolicy Bypass -File .\setup.ps1`.
After setup, gameplay runs offline. Copy **assets/** with the project; its three
PNG files are part of the game. `models/manifest.json` records official model
URLs and checksums. The model bundles total approximately 14 MB.

On Linux/macOS, use `python3.11 -m venv .venv` and `.venv/bin/python` for these
commands. Those operating systems have not been validated here. Fonts fall
back to DejaVu Sans or Arial where Bahnschrift is unavailable.

## Presentation and artwork

The arena has an original clockwork stadium above the clouds, golden-hour
lighting, a six-card illustrated gallery, large prompts, smooth hover/scene
transitions, perspective tracks, animated obstacles, target effects, celebration
particles, original synthesized sound cues and a quiet synthesized music loop.
The music pauses during Timekeeper so its beat cue stays clear.

The avatar uses **3D-shaded textures in a joint-driven 2.5D sprite rig**: head,
torso, upper arms, forearms, gloves, thighs, shins, shoes and shoulder caps.
Live landmarks rotate and stretch independent parts; calibration normalizes
character size, and interpolation reduces jitter. Player 2 and NOVA use a warm
accent; the time echo is purple. A procedural character remains available if
the sprite asset is missing.

Artwork was made with the built-in image generation tool and copied into this
workspace. Full prompts, file names and generation details are in
[assets/PROMPTS.md](assets/PROMPTS.md). Source video assets were not copied.

## Architecture

```text
main.py                         CLI and application lifecycle
camera.py                       Latest-frame OpenCV capture thread
pose_tracker.py                 MediaPipe Tasks VIDEO worker, up to two poses
tracking_types.py               Mirrored landmarks, confidence, all-body output
player_manager.py               Neutral calibration, join, confidence, continuity
player_bank.py                  Fixed camera lanes and independent player inputs
gesture_controller.py           Cursor, distance-normalized hand switch, dwell latch
movement.py                     Alternating-leg activity and normalized motion
motion_input.py                 Shared movement vocabulary for humans and AI
simulated_input.py              Synthetic landmarks using the same tracking path
ai_opponent.py                  NOVA's offline decisions and difficulty
match.py                        Fair seeded games, shared pause and ranking
game_manager.py                 Navigation, input, multiplayer turns, persistence
games/                          Six independent game engines and common clock
avatar.py / sprite_rig.py        Animated poses and shaded texture rig
ui/art.py                       Artwork loading, caching and atlas slicing
ui/components.py                Buttons, game cards, mode cards and cursor
ui/screens.py                   Onboarding, gallery, briefings, lobby, results
ui/worlds.py                    Six animated gameplay presentations
audio.py                        Synthesized sound/music and stereo player cues
storage.py                      SQLite schema migration, records and boards
tests/                          Rules, camera, input, multiplayer and acceptance
scripts/                        Model setup, inference checks and benchmarks
```

MediaPipe uses the Tasks API with the official Pose Landmarker Lite and Hand
Landmarker bundles. OpenCV capture and inference have separate latest-result
threads. Rendering never waits for inference. Captured RGB coordinates are
mirrored once. Fine hand landmarks are associated by wrist proximity; body
wrists provide a fallback when fingers are small or occluded. The hand model is
skipped during games to prioritize body latency.

The game clocks use `time.perf_counter()`. The original running engine splits
intervals at light/grace/finish boundaries; arcade games integrate bounded
steps so impacts and beat windows cannot be skipped by a slower render frame.
Completion time is active play time, excluding the initial countdown and
tracking pauses. Timekeeper timing error is a score relative to the game beat.
These values do not establish precise human reaction times: capture, inference,
display and frame sampling introduce latency.

## Local records

`data/chrono_arena.sqlite3` stores completed human rounds. The upgrade migrates
the original results table in place and preserves existing Red/Green records.
Each entry includes UTC creation time, player, camera/demo source, game, match
mode, challenge seed, outcome, score, elapsed/remaining time, violations and
timestamped event JSON. Events cover phases, targets, misses, scoring, beats,
echo sequences, tracking pauses/resumes and outcomes.

Records and personal bests are separated by game, source and match mode. Time
games rank successful completion time; score games rank points. AI competitors
do not enter human leaderboards. Party turns store one entry per person.
Abandoned games do not create completed records. Write failures are surfaced
in the interface.

## Automated verification

```powershell
.\.venv\Scripts\python.exe -m compileall -q -x .venv .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe main.py --smoke-test
.\.venv\Scripts\python.exe scripts\verify_tracking.py --camera
.\.venv\Scripts\python.exe scripts\benchmark.py --frames 300
.\.venv\Scripts\python.exe scripts\benchmark.py --mode duo --game sprint --frames 300
```

The smoke test uses temporary records/settings, deterministic seeds and actual
synthetic body landmarks. It joins by raising hands, navigates using wrist
positions plus smoothing/dwell, plays **all six games in all four modes**, tests
both 2- and 4-person parties, pauses/resumes, triggers a red penalty, rematches,
loses by timeout and validates personal-best preservation. Player 2 beats an
idle Player 1 in every game, and can navigate after Player 1 steps out. It
expects exactly **41 human result rows**, including the extra rematch. PNGs and
`acceptance-report.json` are under `artifacts/v2/`.

`verify_tracking.py` checks one-body and two-hand official reference images,
negative blank input, and a two-body fixture made from the reference photograph.
With `--camera`, it checks physical webcam capture, worker inference and cleanup.
It does not save webcam images. The two-body fixture verifies multi-pose output;
it is separate from a real two-person playtest.

Verified in this Windows workspace on **24 October 2026**:

| Check | Observed result |
| --- | --- |
| Unit tests | 49 pass |
| Full body-input acceptance | All six games × Solo, AI, 2 Players and Party pass |
| Party handoffs | 2- and 4-player sessions pass |
| Result integrity | One record per human finish; old schema migration passes |
| Physical webcam | 640×480 frames, 91 distinct inference frames in a 3s probe |
| Multi-pose reference fixture | Two bodies detected |
| Native solo render + synthetic input | ~6.5ms median, ~146 uncapped FPS |
| Native two-player render + synthetic input | ~7.9ms median, ~118 uncapped FPS |
| Resource cleanup | Camera and inference workers stop cleanly |

These are local measurements; the rendering benchmarks measure simulated input
separately from camera inference. **Physical standing-player and two-person
gameplay still need a playtest** for room framing, occlusion, hand reach,
ordinary stillness, sensitivity and sound audibility. The webcam pipeline has
been exercised, while the complete movement/gameplay acceptance is synthetic.

## Demo route for judges

1. Launch the webcam game and join with a raised hand.
2. Open the gallery to show six distinct TIME mechanics and four player modes.
3. Play Red/Green for jogging/freezing, then Timekeeper for synchronization.
4. Try AI Rival in Chrono Sprint or Lightning Strike.
5. Use 2 Players for a side-by-side race, or Party for a shared-room tournament.
6. End on results: completion/score, personal best and the local standings.

## References

The vision implementation follows Google's official
[Pose Landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python)
and [Hand Landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python).
Reference fixtures come from Google's
[pose sample](https://storage.googleapis.com/mediapipe-assets/pose.jpg) and
[Hand Landmarker notebook](https://github.com/google-ai-edge/mediapipe-samples/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb).
The user-provided [Kinect Sports video](https://www.youtube.com/watch?v=-AuBrN5up8k&t=68s)
set the presentation direction. Its metadata was retrieved; playback at the
requested timestamp was unavailable in this environment.
