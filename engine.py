"""Adaptive learning engine for VidyaSaathi AI.

Pure functions only (no web, no database) so the logic is easy to test.
Levels follow the ASER idea of "teaching at the right level": a child
practises at the level just above what they have already mastered.
"""
import json
import random
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "data" / "questions.json").read_text(encoding="utf-8"))
LEVELS = {lvl["level"]: lvl for lvl in DATA["levels"]}
MIN_LEVEL, MAX_LEVEL = min(LEVELS), max(LEVELS)

LEVEL_UP_CORRECT = 3      # 3 of the last 4 answers right -> move up
WINDOW = 4
LEVEL_DOWN_WRONG = 2      # 2 wrong in a row -> move down


def public_question(q, lang):
    """Question as sent to the browser (no answer key)."""
    return {"id": q["id"], "q": q["q"].get(lang, q["q"]["en"]), "options": q["options"]}


def find_question(qid):
    for lvl in LEVELS.values():
        for q in lvl["questions"]:
            if q["id"] == qid:
                return q, lvl["level"]
    raise KeyError(qid)


def diagnostic_set(lang="en", rng=random):
    """One question per level, easiest first."""
    return [public_question(rng.choice(LEVELS[l]["questions"]), lang) for l in sorted(LEVELS)]


def place_student(results):
    """results: list of booleans in level order (level 1 first).

    The child is placed at the first level they could not do,
    i.e. 1 + number of consecutive correct answers from level 1.
    """
    streak = 0
    for ok in results:
        if not ok:
            break
        streak += 1
    return min(MIN_LEVEL + streak, MAX_LEVEL)


def next_level(level, history):
    """Decide the next practice level.

    history: booleans for answers at the *current* level, oldest first.
    Returns (new_level, changed: 'up' | 'down' | None).
    """
    recent = history[-WINDOW:]
    if len(recent) >= WINDOW and sum(recent) >= LEVEL_UP_CORRECT and level < MAX_LEVEL:
        return level + 1, "up"
    if len(history) >= LEVEL_DOWN_WRONG and not any(history[-LEVEL_DOWN_WRONG:]) and level > MIN_LEVEL:
        return level - 1, "down"
    return level, None


def practice_question(level, lang="en", exclude=(), rng=random):
    pool = [q for q in LEVELS[level]["questions"] if q["id"] not in exclude] or LEVELS[level]["questions"]
    return public_question(rng.choice(pool), lang)


def check_answer(qid, answer, lang="en"):
    q, level = find_question(qid)
    ok = str(answer).strip() == q["answer"]
    return {
        "correct": ok,
        "answer": q["answer"],
        "hint": q["hint"].get(lang, q["hint"]["en"]),
        "level": level,
        "question": q["q"].get(lang, q["q"]["en"]),
    }


def level_name(level, lang="en"):
    return LEVELS[level]["name"].get(lang, LEVELS[level]["name"]["en"])
