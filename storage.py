"""Transactional local results; simulated records are kept separate from camera runs."""
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from config import ROOT


class Storage:
    def __init__(self, path=None):
        target = Path(path) if path else ROOT / "data/chrono_arena.sqlite3"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(target))
        self.connection.execute("""CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY, created_utc TEXT NOT NULL, player TEXT NOT NULL,
            mode TEXT NOT NULL, won INTEGER NOT NULL, elapsed REAL NOT NULL,
            remaining REAL NOT NULL, violations INTEGER NOT NULL, events TEXT NOT NULL)""")
        self.connection.commit()
        columns={row[1] for row in self.connection.execute("PRAGMA table_info(results)")}
        for name,definition in {"game_id":"TEXT NOT NULL DEFAULT 'red_green'",
                                "session_mode":"TEXT NOT NULL DEFAULT 'solo'",
                                "score":"INTEGER NOT NULL DEFAULT 0",
                                "metric":"TEXT NOT NULL DEFAULT 'time'",
                                "match_seed":"INTEGER NOT NULL DEFAULT 0"}.items():
            if name not in columns:
                self.connection.execute(f"ALTER TABLE results ADD COLUMN {name} {definition}")
        self.connection.commit()

    def best(self, player, mode="camera",game_id="red_green",session_mode="solo"):
        row = self.connection.execute("SELECT MIN(elapsed) FROM results WHERE player=? AND mode=? AND game_id=? AND session_mode=? AND won=1", (player, mode,game_id,session_mode)).fetchone()
        return row[0]

    def best_score(self,player,mode="camera",game_id="lightning",session_mode="solo"):
        return self.connection.execute("SELECT MAX(score) FROM results WHERE player=? AND mode=? AND game_id=? AND session_mode=?",
                                       (player,mode,game_id,session_mode)).fetchone()[0]

    def save(self, player, mode, game,session_mode="solo",seed=0):
        if not game.finished:
            raise ValueError("Cannot save an unfinished round")
        with self.connection:
            cursor = self.connection.execute("INSERT INTO results(created_utc,player,mode,won,elapsed,remaining,violations,events,game_id,session_mode,score,metric,match_seed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), player, mode, int(game.won), game.elapsed, game.remaining, game.violations, json.dumps(game.events),game.game_id,session_mode,game.score,game.metric,seed))
        return cursor.lastrowid

    def leaderboard(self, mode="camera", limit=5,game_id="red_green",session_mode="solo",metric="time"):
        if metric=="time":
            return self.connection.execute("SELECT player, elapsed, violations FROM results WHERE won=1 AND mode=? AND game_id=? AND session_mode=? ORDER BY elapsed ASC LIMIT ?", (mode,game_id,session_mode,limit)).fetchall()
        return self.connection.execute("SELECT player, score, violations FROM results WHERE mode=? AND game_id=? AND session_mode=? ORDER BY score DESC LIMIT ?", (mode,game_id,session_mode,limit)).fetchall()

    def close(self):
        self.connection.close()
