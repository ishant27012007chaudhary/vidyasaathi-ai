"""VidyaSaathi AI - adaptive bilingual maths tutor (prototype).

Run:  python app.py   then open http://localhost:5000
"""
import os
import random
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory

import ai
import engine

BASE = Path(__file__).parent
DB_PATH = os.getenv("VIDYA_DB", str(BASE / "vidyasaathi.db"))

app = Flask(__name__, static_folder="static")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  grade INTEGER NOT NULL,
  lang TEXT NOT NULL DEFAULT 'en',
  start_level INTEGER,
  level INTEGER,
  level_mark INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL REFERENCES students(id),
  qid TEXT NOT NULL,
  level INTEGER NOT NULL,
  correct INTEGER NOT NULL,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.executescript(SCHEMA)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def get_student(sid):
    row = db().execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
    if not row:
        raise LookupError("student not found")
    return row


@app.errorhandler(LookupError)
def not_found(exc):
    return jsonify(error=str(exc)), 404


# ---------- pages ----------
@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/teacher")
def teacher_page():
    return send_from_directory(app.static_folder, "teacher.html")


# ---------- student flow ----------
@app.post("/api/students")
def create_student():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()[:40]
    if not name:
        return jsonify(error="name required"), 400
    grade = int(data.get("grade", 5))
    lang = data.get("lang", "en") if data.get("lang") in ("en", "hi") else "en"
    cur = db().execute("INSERT INTO students (name, grade, lang) VALUES (?, ?, ?)", (name, grade, lang))
    db().commit()
    return jsonify(id=cur.lastrowid, name=name, grade=grade, lang=lang)


@app.get("/api/diagnostic")
def diagnostic():
    return jsonify(questions=engine.diagnostic_set(request.args.get("lang", "en")))


@app.post("/api/diagnostic")
def submit_diagnostic():
    data = request.get_json(force=True)
    s = get_student(data["student_id"])
    results = []
    for a in data["answers"]:
        res = engine.check_answer(a["qid"], a["answer"], s["lang"])
        results.append((res["level"], res["correct"]))
        db().execute("INSERT INTO attempts (student_id, qid, level, correct) VALUES (?, ?, ?, ?)",
                     (s["id"], a["qid"], res["level"], int(res["correct"])))
    results.sort()
    level = engine.place_student([ok for _, ok in results])
    mark = db().execute("SELECT COALESCE(MAX(id), 0) FROM attempts").fetchone()[0]
    db().execute("UPDATE students SET start_level = ?, level = ?, level_mark = ? WHERE id = ?",
                 (level, level, mark, s["id"]))
    db().commit()
    return jsonify(level=level, level_name=engine.level_name(level, s["lang"]),
                   correct=sum(ok for _, ok in results), total=len(results))


@app.get("/api/practice")
def practice():
    s = get_student(int(request.args["student_id"]))
    recent = [r["qid"] for r in db().execute(
        "SELECT qid FROM attempts WHERE student_id = ? ORDER BY id DESC LIMIT 2", (s["id"],))]
    q = engine.practice_question(s["level"], s["lang"], exclude=recent)
    return jsonify(question=q, level=s["level"], level_name=engine.level_name(s["level"], s["lang"]))


@app.post("/api/answer")
def answer():
    data = request.get_json(force=True)
    s = get_student(data["student_id"])
    res = engine.check_answer(data["qid"], data["answer"], s["lang"])
    db().execute("INSERT INTO attempts (student_id, qid, level, correct) VALUES (?, ?, ?, ?)",
                 (s["id"], data["qid"], s["level"], int(res["correct"])))
    history = [bool(r["correct"]) for r in db().execute(
        "SELECT correct FROM attempts WHERE student_id = ? AND id > ? AND level = ? ORDER BY id",
        (s["id"], s["level_mark"], s["level"]))]
    new_level, change = engine.next_level(s["level"], history)
    if change:
        mark = db().execute("SELECT MAX(id) FROM attempts").fetchone()[0]
        db().execute("UPDATE students SET level = ?, level_mark = ? WHERE id = ?", (new_level, mark, s["id"]))
    db().commit()
    return jsonify(correct=res["correct"], answer=res["answer"], hint=res["hint"],
                   level=new_level, level_change=change,
                   level_name=engine.level_name(new_level, s["lang"]))


@app.post("/api/tutor")
def tutor():
    data = request.get_json(force=True)
    s = get_student(data["student_id"])
    question, hint = "", ""
    if data.get("qid"):
        q, _ = engine.find_question(data["qid"])
        question = q["q"]["en"]
        hint = q["hint"].get(s["lang"], q["hint"]["en"])
    messages = [m for m in data.get("messages", []) if m.get("role") in ("user", "assistant")][-8:]
    reply, mode = ai.tutor_reply(messages, s["lang"], engine.level_name(s["level"] or 1), question, hint)
    return jsonify(reply=reply, mode=mode)


@app.get("/api/status")
def status():
    return jsonify(ai_mode="watsonx" if ai.watsonx_ready() else "demo")


# ---------- teacher dashboard ----------
@app.get("/api/teacher")
def teacher():
    rows = db().execute("""
        SELECT s.id, s.name, s.grade, s.lang, s.start_level, s.level,
               COUNT(a.id) AS attempts, COALESCE(SUM(a.correct), 0) AS correct
        FROM students s LEFT JOIN attempts a ON a.student_id = s.id
        WHERE s.level IS NOT NULL
        GROUP BY s.id ORDER BY s.level, s.name""").fetchall()
    students = [{
        "id": r["id"], "name": r["name"], "grade": r["grade"], "lang": r["lang"],
        "start_level": r["start_level"], "level": r["level"],
        "gain": r["level"] - r["start_level"],
        "attempts": r["attempts"],
        "accuracy": round(100 * r["correct"] / r["attempts"]) if r["attempts"] else 0,
        "below_grade": r["level"] <= 2 and r["grade"] >= 5,
    } for r in rows]
    groups = {}
    for st in students:
        groups.setdefault(st["level"], []).append(st["name"])
    return jsonify(
        students=students,
        groups=[{"level": l, "level_name": engine.level_name(l), "students": n} for l, n in sorted(groups.items())],
        summary={
            "students": len(students),
            "attempts": sum(s["attempts"] for s in students),
            "avg_accuracy": round(sum(s["accuracy"] for s in students) / len(students)) if students else 0,
            "moved_up": sum(1 for s in students if s["gain"] > 0),
        },
    )


@app.post("/api/seed-demo")
def seed_demo():
    """Fill the dashboard with a sample class so it can be demoed instantly."""
    rng = random.Random(7)
    names = ["Aarav", "Anjali", "Ravi", "Sunita", "Imran", "Kavya", "Deepak", "Meena",
             "Arjun", "Neha", "Salman", "Lakshmi"]
    for i, name in enumerate(names):
        start = rng.choice([1, 1, 2, 2, 2, 3, 3, 4])
        level = min(start + rng.choice([0, 0, 1, 1, 2]), engine.MAX_LEVEL)
        cur = db().execute(
            "INSERT INTO students (name, grade, lang, start_level, level) VALUES (?, ?, ?, ?, ?)",
            (name, rng.choice([4, 5, 6, 7]), "hi" if i % 3 else "en", start, level))
        for _ in range(rng.randint(8, 30)):
            lvl = rng.randint(start, level)
            q = rng.choice(engine.LEVELS[lvl]["questions"])
            db().execute("INSERT INTO attempts (student_id, qid, level, correct) VALUES (?, ?, ?, ?)",
                         (cur.lastrowid, q["id"], lvl, int(rng.random() < 0.7)))
    db().commit()
    return jsonify(ok=True, added=len(names))


if __name__ == "__main__":
    print("VidyaSaathi AI running in", "watsonx.ai" if ai.watsonx_ready() else "DEMO", "mode")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
