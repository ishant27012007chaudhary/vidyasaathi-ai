const T = {
  en: { welcome: "Namaste! Let's learn maths together.", welcomeSub: "First, 5 quick questions so I know where to start.",
        name: "Your name", class: "Class", lang: "Language", start: "Start", listen: "Listen", next: "Next",
        practice: "Start practising", ask: "Ask VidyaSaathi", send: "Send",
        check: "Quick check", practising: "Practice", q: "Question",
        right: "Correct! Well done.", wrong: "Not quite. The answer is", hintLbl: "Tip:",
        placed: (n) => `Great start, ${n}!`, placedSub: (l, c, t) => `You got ${c} of ${t}. We'll practise: ${l}.`,
        up: "Level up! 🎉 New topic:", down: "Let's revise an easier topic first:",
        chatPh: "Type 'hint' or ask a question", greet: "Stuck? Type 'hint' or ask me anything about this question." },
  hi: { welcome: "नमस्ते! चलो साथ में गणित सीखें।", welcomeSub: "पहले 5 छोटे सवाल, ताकि पता चले कहाँ से शुरू करें।",
        name: "तुम्हारा नाम", class: "कक्षा", lang: "भाषा", start: "शुरू करें", listen: "सुनो", next: "आगे",
        practice: "अभ्यास शुरू करें", ask: "विद्यासाथी से पूछो", send: "भेजो",
        check: "जाँच", practising: "अभ्यास", q: "सवाल",
        right: "सही! बहुत बढ़िया।", wrong: "थोड़ा चूक गए। सही उत्तर है", hintLbl: "सुझाव:",
        placed: (n) => `बढ़िया शुरुआत, ${n}!`, placedSub: (l, c, t) => `${t} में से ${c} सही। अब अभ्यास: ${l}।`,
        up: "अगला स्तर! 🎉 नया विषय:", down: "पहले आसान विषय दोहराते हैं:",
        chatPh: "'hint' लिखो या सवाल पूछो", greet: "अटक गए? 'hint' लिखो या इस सवाल के बारे में कुछ भी पूछो।" },
};

const $ = (id) => document.getElementById(id);
const state = { lang: "en", student: null, diag: [], diagAnswers: [], idx: 0, current: null, chat: [], mode: "practice" };
const t = (k) => T[state.lang][k];

async function api(path, body) {
  const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  if (!res.ok) throw new Error((await res.json()).error || res.statusText);
  return res.json();
}

function show(...ids) {
  ["s-welcome", "s-question", "s-placed", "s-chat"].forEach((s) => $(s).classList.toggle("hidden", !ids.includes(s)));
}

function translate() {
  document.querySelectorAll("[data-t]").forEach((el) => { const v = t(el.dataset.t); if (typeof v === "string") el.textContent = v; });
  $("chatInput").placeholder = t("chatPh");
  document.documentElement.lang = state.lang;
}

// language toggle
document.querySelectorAll(".seg-btn").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".seg-btn").forEach((x) => x.classList.toggle("on", x === b));
  state.lang = b.dataset.lang; translate();
}));

api("/api/status").then((s) => {
  $("mode").textContent = s.ai_mode === "watsonx" ? "IBM Granite · watsonx.ai" : "Demo mode";
  $("mode").classList.toggle("live", s.ai_mode === "watsonx");
});

$("start").addEventListener("click", async () => {
  const name = $("name").value.trim();
  if (!name) { $("name").focus(); return; }
  state.student = await api("/api/students", { name, grade: +$("grade").value, lang: state.lang });
  state.diag = (await api(`/api/diagnostic?lang=${state.lang}`)).questions;
  state.idx = 0; state.diagAnswers = []; state.mode = "diag";
  show("s-question"); renderQuestion(state.diag[0]);
});

function renderQuestion(q) {
  state.current = q;
  $("qtext").textContent = q.q;
  $("feedback").className = "feedback hidden";
  $("next").classList.add("hidden");
  const diag = state.mode === "diag";
  $("stage").textContent = diag ? `${t("check")} · ${t("q")} ${state.idx + 1}/${state.diag.length}` : t("practising");
  $("bar").style.width = diag ? `${(state.idx / state.diag.length) * 100}%` : "100%";
  $("options").innerHTML = "";
  q.options.forEach((o) => {
    const b = document.createElement("button");
    b.className = "opt"; b.textContent = o;
    b.addEventListener("click", () => choose(o, b));
    $("options").appendChild(b);
  });
}

async function choose(option, btn) {
  document.querySelectorAll(".opt").forEach((b) => (b.disabled = true));
  if (state.mode === "diag") {
    btn.classList.add("right"); // no right/wrong shown during the check, to keep it stress-free
    state.diagAnswers.push({ qid: state.current.id, answer: option });
    state.idx++;
    setTimeout(async () => {
      if (state.idx < state.diag.length) return renderQuestion(state.diag[state.idx]);
      const r = await api("/api/diagnostic", { student_id: state.student.id, answers: state.diagAnswers });
      $("placedText").textContent = t("placed")(state.student.name);
      $("placedSub").textContent = t("placedSub")(r.level_name, r.correct, r.total);
      show("s-placed");
    }, 350);
    return;
  }
  const r = await api("/api/answer", { student_id: state.student.id, qid: state.current.id, answer: option });
  btn.classList.add(r.correct ? "right" : "wrong");
  if (!r.correct) document.querySelectorAll(".opt").forEach((b) => b.textContent === r.answer && b.classList.add("right"));
  let msg = r.correct ? t("right") : `${t("wrong")} ${r.answer}. ${t("hintLbl")} ${r.hint}`;
  if (r.level_change === "up") msg += ` ${t("up")} ${r.level_name}`;
  if (r.level_change === "down") msg += ` ${t("down")} ${r.level_name}`;
  const fb = $("feedback"); fb.textContent = msg; fb.className = `feedback ${r.correct ? "ok" : "bad"}`;
  $("levelBadge").textContent = `L${r.level} · ${r.level_name}`;
  $("next").classList.remove("hidden");
}

async function loadPractice() {
  state.mode = "practice";
  const r = await api(`/api/practice?student_id=${state.student.id}`);
  $("levelBadge").textContent = `L${r.level} · ${r.level_name}`;
  renderQuestion(r.question);
}

$("toPractice").addEventListener("click", async () => {
  show("s-question", "s-chat");
  if (!state.chat.length) addMsg("assistant", t("greet"));
  await loadPractice();
});
$("next").addEventListener("click", loadPractice);

// read aloud (works offline on most Android phones)
$("speak").addEventListener("click", () => {
  if (!("speechSynthesis" in window) || !state.current) return;
  const u = new SpeechSynthesisUtterance(state.current.q);
  u.lang = state.lang === "hi" ? "hi-IN" : "en-IN"; u.rate = 0.9;
  speechSynthesis.cancel(); speechSynthesis.speak(u);
});

// voice input where the browser supports it
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SR) $("mic").classList.add("hidden");
$("mic").addEventListener("click", () => {
  const rec = new SR(); rec.lang = state.lang === "hi" ? "hi-IN" : "en-IN";
  rec.onresult = (e) => { $("chatInput").value = e.results[0][0].transcript; };
  rec.start();
});

function addMsg(role, content) {
  const d = document.createElement("div"); d.className = `msg ${role}`; d.textContent = content;
  $("chat").appendChild(d); $("chat").scrollTop = $("chat").scrollHeight;
}

$("chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("chatInput").value.trim(); if (!text) return;
  $("chatInput").value = ""; addMsg("user", text);
  state.chat.push({ role: "user", content: text });
  try {
    const r = await api("/api/tutor", { student_id: state.student.id, qid: state.current?.id, messages: state.chat });
    state.chat.push({ role: "assistant", content: r.reply }); addMsg("assistant", r.reply);
  } catch (err) { addMsg("assistant", "⚠️ " + err.message); }
});

translate();
