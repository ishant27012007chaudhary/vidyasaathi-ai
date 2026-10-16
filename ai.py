"""Tutor brain: IBM Granite on watsonx.ai, with an offline demo fallback.

Set these environment variables to use watsonx.ai (see README):
  WATSONX_APIKEY      IBM Cloud API key
  WATSONX_PROJECT_ID  watsonx.ai project ID
  WATSONX_URL         region endpoint, e.g. https://us-south.ml.cloud.ibm.com
  WATSONX_MODEL_ID    optional, defaults to an IBM Granite instruct model

Without them the app runs in DEMO mode with rule-based replies, so it can be
shown in class with no internet or cloud account.
"""
import os
import re
import time

DEFAULT_MODEL = "ibm/granite-3-3-8b-instruct"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
API_VERSION = "2024-10-08"

LANG_NAMES = {"en": "simple English", "hi": "simple Hindi (Devanagari script)"}

SYSTEM_PROMPT = """You are VidyaSaathi, a kind and patient maths tutor for children aged 8-15 in rural India.
Rules:
- Reply in {language}. Use short sentences and words a Class 3-8 child knows.
- Use everyday Indian examples (rotis, mangoes, rupees, cricket, marbles).
- Do NOT give the final answer straight away. Give one small hint or step, then ask the child to try.
- If the child is right, praise the effort specifically.
- Keep every reply under 80 words.
- Only talk about studies. If asked anything unsafe or personal, gently bring the child back to learning
  and suggest talking to a teacher or parent.
Current topic: {topic}. Current question (if any): {question}"""

_token = {"value": None, "expires": 0}


def watsonx_ready():
    return bool(os.getenv("WATSONX_APIKEY") and os.getenv("WATSONX_PROJECT_ID"))


def _iam_token():
    import requests
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    r = requests.post(
        IAM_URL,
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": os.environ["WATSONX_APIKEY"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()
    _token.update(value=body["access_token"], expires=time.time() + body.get("expires_in", 3600))
    return _token["value"]


def _ask_watsonx(messages):
    import requests
    base = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/")
    r = requests.post(
        f"{base}/ml/v1/text/chat?version={API_VERSION}",
        headers={"Authorization": f"Bearer {_iam_token()}", "Content-Type": "application/json"},
        json={
            "model_id": os.getenv("WATSONX_MODEL_ID", DEFAULT_MODEL),
            "project_id": os.environ["WATSONX_PROJECT_ID"],
            "messages": messages,
            "max_tokens": 200,
            "temperature": 0.3,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# ---------- demo mode -------------------------------------------------------
DEMO = {
    "en": {
        "greet": "Namaste! I am VidyaSaathi. Ask me about the question on your screen, or type 'hint'.",
        "hint": "Here is a small step: {hint} Now you try - what do you get?",
        "nohint": "Let's go step by step. Tell me what the question is asking, in your own words.",
        "why": "Good question! Maths is like a game with rules. {hint} Try it and tell me your answer.",
        "praise": "Shabaash! You are thinking well. Choose your answer on the screen.",
    },
    "hi": {
        "greet": "नमस्ते! मैं विद्यासाथी हूँ। स्क्रीन वाले सवाल के बारे में पूछो, या 'hint' लिखो।",
        "hint": "एक छोटा कदम: {hint} अब तुम कोशिश करो - क्या उत्तर आया?",
        "nohint": "चलो कदम-दर-कदम चलते हैं। अपने शब्दों में बताओ, सवाल क्या पूछ रहा है?",
        "why": "अच्छा सवाल! गणित नियमों वाला खेल है। {hint} कोशिश करो और उत्तर बताओ।",
        "praise": "शाबाश! तुम अच्छा सोच रहे हो। स्क्रीन पर अपना उत्तर चुनो।",
    },
}


def _demo_reply(text, lang, hint):
    t = DEMO.get(lang, DEMO["en"])
    low = text.lower()
    words = set(re.findall(r"[a-z]+", low))

    def has(english, hindi=()):
        return bool(words & set(english)) or any(h in low for h in hindi)

    if has({"hi", "hello", "namaste"}, ("नमस्ते",)) and len(low) < 15:
        return t["greet"]
    if has({"why", "kyon", "how", "kaise"}, ("क्यों", "कैसे")):
        return t["why"].format(hint=hint or "")
    if has({"hint", "help", "madad", "samajh", "nahi"}, ("मदद", "समझ", "नहीं", "?")):
        return t["hint"].format(hint=hint) if hint else t["nohint"]
    if any(ch.isdigit() for ch in low):
        return t["praise"]
    return t["hint"].format(hint=hint) if hint else t["nohint"]


def tutor_reply(history, lang="en", topic="", question="", hint=""):
    """history: list of {'role': 'user'|'assistant', 'content': str}. Returns (reply, mode)."""
    last = history[-1]["content"] if history else ""
    if watsonx_ready():
        try:
            system = SYSTEM_PROMPT.format(language=LANG_NAMES.get(lang, "simple English"),
                                          topic=topic or "foundational maths", question=question or "none")
            msgs = [{"role": "system", "content": system}] + history[-8:]
            return _ask_watsonx(msgs), "watsonx"
        except Exception as exc:  # network or credential problem: fall back so the class demo never breaks
            print("watsonx.ai call failed, using demo mode:", exc)
    return _demo_reply(last, lang, hint), "demo"
