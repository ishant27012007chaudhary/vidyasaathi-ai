# Building VidyaSaathi with IBM Bob

IBM Bob is IBM's AI development partner (bob.ibm.com, 30-day free trial). It plans, writes, tests and
explains code. Use it to run, understand and extend this project — and take screenshots of each step
for your presentation ("Built with IBM Bob").

## 1. Open the project
1. Sign in at **bob.ibm.com** and install/open Bob.
2. Open the `vidyasaathi` folder as your workspace.
3. Ask Bob:
   > Explain this project's architecture. Which file handles the adaptive levels and which calls watsonx.ai?

## 2. Run and test
> Create a virtual environment, install requirements.txt, run the unit tests, then start app.py.

Expected: `Ran 11 tests ... OK`, then the app on http://localhost:5000.

## 3. Connect watsonx.ai
> Help me set WATSONX_APIKEY, WATSONX_PROJECT_ID and WATSONX_URL for this session from .env.example,
> then restart the app and confirm /api/status returns "watsonx".

## 4. Extend it with Bob (pick 1–2 for your demo)
| Prompt to give Bob | What you get |
|---|---|
| "Add a Level 6 'Decimals' to data/questions.json with 4 bilingual questions and hints, same format. Update tests." | Bigger curriculum |
| "Add Marathi (mr) as a third language across questions.json, app.js and ai.py LANG_NAMES." | Regional-language reach |
| "Add a /api/report endpoint that returns a CSV of student progress for teachers, with a test." | Downloadable report |
| "Make ai.py retrieve the matching NCERT textbook paragraph from a data/ncert/ folder and add it to the system prompt (simple keyword RAG)." | Grounded answers |
| "Review app.py for security issues (input validation, SQL injection) and fix anything you find." | Code review checkpoint |

## 5. What to capture for submission
- Screenshot of Bob explaining the architecture
- Screenshot of tests passing in Bob's terminal
- Screenshot of one feature Bob added (diff view)
- The running app in **IBM Granite · watsonx.ai** mode
