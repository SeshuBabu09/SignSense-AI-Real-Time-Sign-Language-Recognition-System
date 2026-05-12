(() => {
  "use strict";

  const SIGN_LIBRARY = {
    hello: { label: "HELLO", preview: "👋", file: "hello.mp4" },
    help: { label: "HELP", preview: "🆘", file: "help.mp4" },
    emergency: { label: "EMERGENCY", preview: "🚨", file: "emergency.mp4" },
    water: { label: "WATER", preview: "💧", file: "water.mp4" },
    food: { label: "FOOD", preview: "🍛", file: "food.mp4" },
    bathroom: { label: "BATHROOM", preview: "🚻", file: "bathroom.mp4" },
    yes: { label: "YES", preview: "✅", file: "yes.mp4" },
    no: { label: "NO", preview: "❌", file: "no.mp4" },
    sorry: { label: "SORRY", preview: "🙏", file: "sorry.mp4" },
    thank_you: { label: "THANK YOU", preview: "🤝", file: "thank_you.mp4" },
    stop: { label: "STOP", preview: "✋", file: "stop.mp4" },
    come: { label: "COME", preview: "👉", file: "come.mp4" },
    go: { label: "GO", preview: "➡️", file: "go.mp4" },
    call: { label: "CALL", preview: "📞", file: "call.mp4" },
    hospital: { label: "HOSPITAL", preview: "🏥", file: "hospital.mp4" },
    where: { label: "WHERE", preview: "📍", file: "where.mp4" },
    name: { label: "NAME", preview: "🪪", file: "name.mp4" },
    good_morning: { label: "GOOD MORNING", preview: "🌅", file: "good_morning.mp4" },
    good_night: { label: "GOOD NIGHT", preview: "🌙", file: "good_night.mp4" },
    fine: { label: "I AM FINE", preview: "🙂", file: "fine.mp4" },
  };

  const el = {
    btnStart: document.getElementById("btnStart"),
    btnStop: document.getElementById("btnStop"),
    btnTest: document.getElementById("btnTest"),
    btnClear: document.getElementById("btnClear"),
    logBox: document.getElementById("logBox"),
    statusPill: document.getElementById("statusPill"),

    signTitle: document.getElementById("signTitle"),
    signBadge: document.getElementById("signBadge"),
    signMenu: document.getElementById("signMenu"),
    signVideo: document.getElementById("signVideo"),
    signFallback: document.getElementById("signFallback"),
  };

  function timeNow() {
    return new Date().toLocaleTimeString([], { hour:"2-digit", minute:"2-digit", second:"2-digit" });
  }

  function log(type, msg) {
    const d = document.createElement("div");
    d.className = type === "error" ? "e" : type === "speech" ? "s" : "t";
    d.textContent = `[${timeNow()}] ${msg}`;
    el.logBox.appendChild(d);
    el.logBox.scrollTop = el.logBox.scrollHeight;
  }

  function setStatus(s) {
    el.statusPill.textContent = "Status: " + s;
  }

  function speak(text) {
    try {
      if (!("speechSynthesis" in window)) return;
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "en-IN";
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    } catch {}
  }

  async function showSign(signKey, source="voice") {
    const data = SIGN_LIBRARY[signKey];

    if (!data) {
      el.signTitle.textContent = "Unknown sign";
      el.signBadge.textContent = "Unknown";
      el.signVideo.style.display = "none";
      el.signFallback.style.display = "flex";
      el.signFallback.textContent = "❓";
      log("error", "Unknown sign: " + signKey);
      return;
    }

    el.signTitle.textContent = `Showing: ${data.label}`;
    el.signBadge.textContent = `From ${source}`;

    // fallback first
    el.signFallback.style.display = "flex";
    el.signFallback.textContent = data.preview;
    el.signVideo.style.display = "none";

    // try video
    const videoPath = `./signs/${data.file}`;
    try {
      el.signVideo.src = videoPath;
      await el.signVideo.play();
      el.signVideo.style.display = "block";
      el.signFallback.style.display = "none";
      log("text", `Playing video: ${data.file}`);
    } catch {
      log("error", `Video missing/blocked (${data.file}). Using fallback emoji.`);
    }
  }

  function normalize(text) {
    return String(text || "")
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9 ]/g, "")
      .replace(/\s+/g, "_");
  }

  function parsePrompt(text) {
    if (!text) return null;
    const t = text.toLowerCase().trim();

    const direct = t.match(/show\s+(?:the\s+)?sign\s+(.*)/i);
    if (direct && direct[1]) return normalize(direct[1]);

    const rules = [
      { p:["help","save me","assist"], sign:"help" },
      { p:["emergency","danger","police"], sign:"emergency" },
      { p:["hospital","doctor"], sign:"hospital" },
      { p:["water","thirsty"], sign:"water" },
      { p:["food","hungry"], sign:"food" },
      { p:["bathroom","toilet","washroom"], sign:"bathroom" },
      { p:["hello","hi"], sign:"hello" },
      { p:["thank you","thanks"], sign:"thank_you" },
      { p:["sorry"], sign:"sorry" },
      { p:["yes","ok","okay"], sign:"yes" },
      { p:["no","not"], sign:"no" },
      { p:["stop","wait"], sign:"stop" },
      { p:["come"], sign:"come" },
      { p:["go"], sign:"go" },
      { p:["call","phone"], sign:"call" },
      { p:["where","location"], sign:"where" },
      { p:["name"], sign:"name" },
      { p:["good morning"], sign:"good_morning" },
      { p:["good night"], sign:"good_night" },
      { p:["fine","i am fine"], sign:"fine" },
    ];

    for (const r of rules) {
      if (r.p.some(x => t.includes(x))) return r.sign;
    }

    const norm = normalize(t);
    if (SIGN_LIBRARY[norm]) return norm;

    return null;
  }

  async function handlePrompt(text) {
    log("speech", `Blind said: "${text}"`);

    const key = parsePrompt(text);
    if (key && SIGN_LIBRARY[key]) {
      await showSign(key, "voice");
      speak("Showing sign " + SIGN_LIBRARY[key].label);
    } else {
      speak("Sorry. I did not understand. Say show sign help or emergency.");
      log("error", "No matching sign. Try: show sign hello / help / emergency / water / food / bathroom");
    }
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let rec = null;
  let listening = false;

  function setupRec() {
    if (!SpeechRecognition) return null;

    const r = new SpeechRecognition();
    r.lang = "en-IN";
    r.continuous = true;
    r.interimResults = false;

    r.onstart = () => {
      listening = true;
      setStatus("Listening");
      el.btnStart.disabled = true;
      el.btnStop.disabled = false;
      log("text", "Listening started...");
    };

    r.onend = () => {
      listening = false;
      setStatus("Idle");
      el.btnStart.disabled = false;
      el.btnStop.disabled = true;
      log("text", "Listening stopped.");
    };

    r.onerror = (e) => {
      log("error", "Speech error: " + (e.error || "unknown"));
      try { r.stop(); } catch {}
    };

    r.onresult = (event) => {
      const last = event.results[event.results.length - 1];
      const transcript = last?.[0]?.transcript || "";
      if (transcript) handlePrompt(transcript);
    };

    return r;
  }

  function startListening() {
    if (!SpeechRecognition) {
      log("error", "SpeechRecognition not supported. Use Chrome.");
      speak("Speech recognition not supported. Please use Google Chrome.");
      return;
    }
    if (!rec) rec = setupRec();
    try { rec.start(); } catch { log("error", "Already listening or blocked."); }
  }

  function stopListening() {
    try { if (rec && listening) rec.stop(); } catch {}
  }

  function renderMenu() {
    el.signMenu.innerHTML = "";
    Object.keys(SIGN_LIBRARY).forEach((k) => {
      const item = SIGN_LIBRARY[k];
      const div = document.createElement("div");
      div.className = "signBtn";
      div.innerHTML = `
        <div class="thumb">${item.preview}</div>
        <div>
          <div class="label">${item.label}</div>
          <div class="small">${k.replaceAll("_"," ")}</div>
        </div>
      `;
      div.onclick = async () => {
        await showSign(k, "menu");
        speak(item.label);
      };
      el.signMenu.appendChild(div);
    });
  }

  el.btnStart.onclick = startListening;
  el.btnStop.onclick = stopListening;
  el.btnClear.onclick = () => el.logBox.innerHTML = "";
  el.btnTest.onclick = () => handlePrompt("show sign emergency");

  renderMenu();
  setStatus("Idle");
  log("text", "Ready. Click Start Listening.");

  if (!SpeechRecognition) log("error", "SpeechRecognition not found. Menu still works.");
})();
