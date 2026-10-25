# Submission release — 25 October 2026

- Optional Practice Moves for all six games, with real-input checks and independent two-player progress.
- Camera skeleton/viewfinder overlay and specific head, feet, hands and lane-position guidance.
- Active runs pause when the window loses focus or is minimized.
- Lightning demo keeps a safe hand position when the mouse leaves the playfield.
- Earned action holds survive tracking pauses; Timekeeper samples the returning hand state correctly.
- Model setup verifies the official pinned hashes before trusting or replacing a file.
- First-time setup launcher, portable instructions, integrity checker and clean source/model/artwork ZIP.

The release keeps the six games, four player modes, Time Shield, XP, medals,
reduced motion and existing local results. The upload ZIP starts with default
settings and includes no player database, local environment, Git history or
camera recordings.

Automated movement acceptance uses simulated body landmarks. Physical webcam
capture/inference is verified separately. Check real two-person framing in the
presentation room before demonstrating.
