"""Run with:  python -m unittest discover tests"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("WATSONX_APIKEY", None)  # always test in demo mode
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["VIDYA_DB"] = _tmp.name

import ai  # noqa: E402
import engine  # noqa: E402
from app import app  # noqa: E402


class EngineTests(unittest.TestCase):
    def test_placement(self):
        self.assertEqual(engine.place_student([False, True, True, True, True]), 1)
        self.assertEqual(engine.place_student([True, True, False, True, False]), 3)
        self.assertEqual(engine.place_student([True] * 5), 5)  # capped at top level

    def test_level_up_after_3_of_4(self):
        self.assertEqual(engine.next_level(2, [True, False, True, True]), (3, "up"))
        self.assertEqual(engine.next_level(2, [True, True, True]), (2, None))  # needs 4 answers

    def test_level_down_after_2_wrong(self):
        self.assertEqual(engine.next_level(3, [True, False, False]), (2, "down"))
        self.assertEqual(engine.next_level(1, [False, False]), (1, None))  # floor

    def test_answer_check_and_language(self):
        r = engine.check_answer("L2-1", "63", "hi")
        self.assertTrue(r["correct"])
        self.assertIn("हासिल", r["hint"])
        self.assertFalse(engine.check_answer("L2-1", "53")["correct"])

    def test_questions_have_valid_answers(self):
        for lvl in engine.LEVELS.values():
            for q in lvl["questions"]:
                self.assertIn(q["answer"], q["options"], q["id"])
                self.assertIn("hi", q["q"]); self.assertIn("hi", q["hint"])

    def test_answer_not_leaked(self):
        for q in engine.diagnostic_set():
            self.assertNotIn("answer", q)


class DemoTutorTests(unittest.TestCase):
    def test_hint_reply(self):
        reply, mode = ai.tutor_reply([{"role": "user", "content": "hint"}], "en", hint="Add the ones first.")
        self.assertEqual(mode, "demo")
        self.assertIn("Add the ones first.", reply)

    def test_hindi_reply(self):
        reply, _ = ai.tutor_reply([{"role": "user", "content": "समझ नहीं आया"}], "hi", hint="पहले इकाई जोड़ो।")
        self.assertIn("पहले इकाई जोड़ो।", reply)


class ApiFlowTests(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def test_full_student_journey(self):
        sid = self.c.post("/api/students", json={"name": "Priya", "grade": 5, "lang": "en"}).get_json()["id"]
        qs = self.c.get("/api/diagnostic").get_json()["questions"]
        # answer level 1 and 2 right, level 3 wrong -> placed at level 3
        answers = []
        for q in qs:
            full, lvl = engine.find_question(q["id"])
            answers.append({"qid": q["id"], "answer": full["answer"] if lvl <= 2 else "wrong"})
        placed = self.c.post("/api/diagnostic", json={"student_id": sid, "answers": answers}).get_json()
        self.assertEqual(placed["level"], 3)

        # 4 correct answers in a row -> level up to 4
        change = None
        for _ in range(4):
            q = self.c.get(f"/api/practice?student_id={sid}").get_json()["question"]
            full, _ = engine.find_question(q["id"])
            res = self.c.post("/api/answer", json={"student_id": sid, "qid": q["id"], "answer": full["answer"]}).get_json()
            change = res["level_change"] or change
        self.assertEqual(change, "up")
        self.assertEqual(res["level"], 4)

        tut = self.c.post("/api/tutor", json={"student_id": sid, "qid": q["id"],
                                              "messages": [{"role": "user", "content": "hint please"}]}).get_json()
        self.assertEqual(tut["mode"], "demo")

        dash = self.c.get("/api/teacher").get_json()
        me = [s for s in dash["students"] if s["id"] == sid][0]
        self.assertEqual(me["gain"], 1)

    def test_seed_demo(self):
        self.assertTrue(self.c.post("/api/seed-demo").get_json()["ok"])
        self.assertGreaterEqual(self.c.get("/api/teacher").get_json()["summary"]["students"], 12)

    def test_missing_student(self):
        self.assertEqual(self.c.get("/api/practice?student_id=99999").status_code, 404)


if __name__ == "__main__":
    unittest.main()
