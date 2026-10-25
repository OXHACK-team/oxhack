# CHRONO ARENA — Own the next second

CHRONO ARENA turns an ordinary webcam into a controller for six motion games.
Players jog, freeze, dodge, reach, catch a beat and repeat remembered poses.
Time is both the subject and the challenge: timing, anticipation, rhythm,
memory, accelerating survival and an earned Time Shield shape every run.

The Windows application runs locally with Python, OpenCV, MediaPipe Tasks,
Pygame CE and NumPy. No Kinect hardware, cloud inference or paid API is required.
Solo, offline AI, two simultaneous players and 2–4 player parties share the
same seeded game engines and movement vocabulary.

## Suggested demonstration

1. Join by raising a hand and select Quick Play.
2. Use Practice Moves to show the avatar demonstration and real movement feedback.
3. Play Dodge or Die and activate Time Shield with crossed arms.
4. Show Timekeeper for rhythm or Echo Shift for memory and motion.
5. Try Two Players or AI Rival, then show the saved score, medal and XP.

## What we built

- Separate latest-frame camera, pose inference and render loops.
- Body-relative calibration, stable player lanes, hand-menu dwell and rejoining.
- Six complete games with endless and timed variants, bounded difficulty and pauses.
- Distinct clockwork arenas, a joint-driven sprite avatar, synthesized sound and effects.
- Movement lessons, tracking guidance, reduced motion, local records and progression.

## AI and reference use

AI assisted the implementation and original artwork. Artwork prompts and source
asset details are in `assets/PROMPTS.md`. Tracking uses Google's official
MediaPipe model bundles; model URLs and hashes are in `models/manifest.json`.
Kinect Sports' demonstrated-gesture tutorials informed the optional practice
flow; no Xbox artwork, code, audio or video assets were copied.

## Practical limits

This is a 2.5D webcam game, with visible-body tracking rather than Kinect depth
sensing. Two-player tracking depends on camera framing and avoiding occlusion.
Automated body-input tests and actual webcam inference are checked separately;
the physical playing space still needs a two-person playtest before presenting.
