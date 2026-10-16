# VidyaSaathi AI — adaptive bilingual maths tutor (prototype)

**SDG 4: Quality Education** · IBM SkillsBuild Masterclass project

Students in rural areas lack access to quality, personalised education. VidyaSaathi is an AI tutor that
finds each child's real level with a 5-question check, then gives practice at exactly that level, in
English or Hindi, with an AI tutor (IBM Granite on watsonx.ai) that gives hints instead of answers.
Teachers get a dashboard that groups children by level for multigrade classrooms.

## Features
| For | Feature |
|---|---|
| Student | 5-question diagnostic → placed at the right level (ASER "teaching at the right level" idea) |
| Student | Adaptive practice: 3 of last 4 right → level up; 2 wrong in a row → step back and revise |
| Student | English / हिन्दी interface, questions and hints |
| Student | "Listen" button reads the question aloud; 🎤 voice input in supported browsers |
| Student | Chat tutor powered by **IBM Granite on watsonx.ai** — hint-first, child-safe system prompt |
| Teacher | Class dashboard: start vs current level, accuracy, children needing attention, suggested level groups |
| Demo | Works fully offline in **demo mode** (rule-based tutor) when no watsonx.ai keys are set |

## Run it (5 minutes)
```bash
pip install -r requirements.txt
python app.py
```
Open http://localhost:5000 (student) and http://localhost:5000/teacher (click **Load sample class**).

### Switch on IBM watsonx.ai (Granite)
1. Create a free IBM Cloud account and a watsonx.ai project (IBM SkillsBuild / IBM Cloud trial).
2. Create an IBM Cloud API key and copy your project ID.
3. Set the variables from `.env.example`, e.g. on Windows PowerShell:
   ```powershell
   $env:WATSONX_APIKEY="..."; $env:WATSONX_PROJECT_ID="..."; $env:WATSONX_URL="https://us-south.ml.cloud.ibm.com"
   python app.py
   ```
   The header badge changes from **Demo mode** to **IBM Granite · watsonx.ai**.
   If the model ID in `.env.example` is not available in your region, pick any Granite chat model listed in
   your watsonx.ai Prompt Lab and set `WATSONX_MODEL_ID`.

## Tests
```bash
python -m unittest discover tests -v
```
11 tests cover placement, level-up/level-down rules, answer checking, Hindi content, the demo tutor and the
full student → teacher API journey.

## Project structure
```
app.py              Flask web server + SQLite storage + REST API
engine.py           Adaptive learning logic (pure functions, fully tested)
ai.py               IBM watsonx.ai Granite chat client + offline demo tutor
data/questions.json Bilingual question bank: 5 levels × 4 questions with hints
static/             Student app (index.html, app.js) and teacher dashboard
tests/              unittest suite
BOB_GUIDE.md        How to open, run and extend this project with IBM Bob
```

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/students` | Register `{name, grade, lang}` |
| GET/POST | `/api/diagnostic` | Get check questions / submit answers → placement level |
| GET | `/api/practice?student_id=` | Next question at the student's level |
| POST | `/api/answer` | Check answer, update level |
| POST | `/api/tutor` | Chat with the tutor (watsonx.ai or demo) |
| GET | `/api/teacher` | Dashboard data |
| POST | `/api/seed-demo` | Load a sample class |

## Limits of this prototype
Maths only, 20 questions, Hindi + English. Next steps: NCERT-grounded retrieval (RAG), more languages
(Granite 4.0 was trained with Indian-language data), WhatsApp channel, offline Android build.

Data sources: ASER 2024 (Pratham), UDISE+ 2024-25 (Ministry of Education).
