const API = "http://127.0.0.1:5000";

const videoStream = document.getElementById("videoStream");
const overlay = document.querySelector(".overlay");
const overlayText = document.getElementById("overlayText");

const cameraStatus = document.getElementById("cameraStatus");
const prediction = document.getElementById("prediction");
const hand = document.getElementById("hand");
const confidence = document.getElementById("confidence");

const historyList = document.getElementById("historyList");
const emptyState = document.getElementById("emptyState");
const count = document.getElementById("count");

const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");
const btnSpeak = document.getElementById("btnSpeak");
const btnSound = document.getElementById("btnSound");
const btnClear = document.getElementById("btnClear");

let poller = null;
let soundOn = true;

let lastSpoken = "";
let lastSpeakTime = 0;

let history = [];
let predBuffer = [];

// =======================
// ✅ SETTINGS FOR ACCURACY
// =======================
const BUFFER_SIZE = 12;          // smoothing buffer
const CONF_SPEAK_MIN = 50;       // ✅ speak only if >= 50%
const CONF_LOW_PRINT = 50;       // ✅ show LOW CONF text if < 50
const CONF_NOISE_MIN = 20;       // below this treat as Unclear to avoid noise
const SPEAK_GAP = 2500;          // 2.5 seconds cooldown

// =======================
// ✅ HELPERS
// =======================
function timeNow() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function normalizeConfidence(confValue) {
  let c = Number(confValue);
  if (!Number.isFinite(c)) return 0;

  // backend returns 0..1 float
  if (c <= 1.0) c = c * 100;

  c = Math.max(0, Math.min(100, c));
  return Math.round(c);
}

function majorityPrediction(buffer) {
  const freq = {};
  for (const p of buffer) freq[p] = (freq[p] || 0) + 1;

  let best = "No Hand";
  let bestCount = 0;

  for (const k in freq) {
    if (freq[k] > bestCount) {
      best = k;
      bestCount = freq[k];
    }
  }
  return best;
}

function setPredictionUI(label, conf) {
  // Always show label
  if (label !== "No Hand" && label !== "Unclear" && label !== "None") {
    if (conf < CONF_LOW_PRINT) {
      prediction.innerText = `${label} (LOW CONFIDENCE)`;
      prediction.style.color = "#fbbf24"; // amber
    } else {
      prediction.innerText = label;
      prediction.style.color = "#22c55e"; // green
    }
  } else {
    prediction.innerText = label;
    prediction.style.color = "#e5e7eb";
  }

  confidence.innerText = `${conf}%`;
}

function addHistory(item) {
  history.unshift(item);
  if (history.length > 25) history.pop();

  historyList.innerHTML = "";
  history.forEach(h => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div>
        <div style="font-weight:800">${h.prediction} <span class="small">(${h.hand})</span></div>
        <div class="small">${h.time}</div>
      </div>
      <div class="badge">${h.conf}%</div>
    `;
    historyList.appendChild(li);
  });

  emptyState.style.display = history.length ? "none" : "block";
  count.innerText = `${history.length} gestures detected`;
}

function speak(text) {
  if (!soundOn) return;
  if (!("speechSynthesis" in window)) return;

  // clean speech (remove warning)
  const clean = String(text)
    .replace("(LOW CONFIDENCE)", "")
    .replaceAll("_", " ")
    .trim();

  window.speechSynthesis.cancel();

  const msg = new SpeechSynthesisUtterance(clean);
  msg.lang = "en-IN";
  msg.rate = 0.95;
  msg.pitch = 1.1;
  msg.volume = 1.0;

  setTimeout(() => window.speechSynthesis.speak(msg), 150);
}

// =======================
// ✅ START / STOP
// =======================
async function start() {
  await fetch(`${API}/start`, { method: "POST" });

  cameraStatus.innerText = "Camera active";
  overlay.style.display = "none";
  videoStream.style.display = "block";
  videoStream.src = `${API}/video_feed`;

  predBuffer = [];
  lastSpoken = "";
  lastSpeakTime = 0;

  if (poller) clearInterval(poller);
  poller = setInterval(loadStatus, 250);
}

async function stop() {
  await fetch(`${API}/stop`, { method: "POST" });

  cameraStatus.innerText = "Camera inactive";
  overlay.style.display = "flex";
  overlayText.innerText = "Start recognition to activate camera";

  videoStream.style.display = "none";
  videoStream.src = "";

  prediction.innerText = "None";
  hand.innerText = "None";
  confidence.innerText = "0%";

  predBuffer = [];

  if (poller) clearInterval(poller);
}

// =======================
// ✅ POLLING STATUS
// =======================
async function loadStatus() {
  try {
    const res = await fetch(`${API}/status`);
    const s = await res.json();

    let pred = String(s.prediction || "No Hand").trim();
    const conf = normalizeConfidence(s.confidence || 0);
    const hnd = String(s.hand || "Unknown").trim();

    // ✅ Noise protection:
    // If confidence is too low, replace label with Unclear
    // (prevents random flickering)
    if (pred !== "No Hand" && pred !== "None" && conf < CONF_NOISE_MIN) {
      pred = "Unclear";
    }

    // Smoothing buffer
    predBuffer.push(pred);
    if (predBuffer.length > BUFFER_SIZE) predBuffer.shift();

    const stablePred = majorityPrediction(predBuffer);

    hand.innerText = hnd;
    setPredictionUI(stablePred, conf);

    const now = Date.now();

    // ✅ Only speak when confidence >= 50%
    // ✅ also avoid repeating and spam
    if (stablePred !== "No Hand" && stablePred !== "Unclear" && stablePred !== "None") {
      if (conf >= CONF_SPEAK_MIN) {
        if (stablePred !== lastSpoken && (now - lastSpeakTime) > SPEAK_GAP) {
          lastSpoken = stablePred;
          lastSpeakTime = now;

          addHistory({
            prediction: stablePred,
            hand: hnd,
            conf: conf,
            time: timeNow()
          });

          speak(stablePred);
        }
      }
    }
  } catch (err) {
    console.log("Status error:", err);
  }
}

// =======================
// ✅ BUTTONS
// =======================
btnStart.onclick = start;
btnStop.onclick = stop;

btnClear.onclick = () => {
  history = [];
  historyList.innerHTML = "";
  emptyState.style.display = "block";
  count.innerText = "0 gestures detected";
};

btnSound.onclick = () => {
  soundOn = !soundOn;
  btnSound.innerText = soundOn ? "🔊 Sound On" : "🔇 Sound Off";
};

btnSpeak.onclick = () => {
  const text = prediction.innerText;
  if (!text || text === "None" || text === "No Hand" || text === "Unclear") return;

  // ✅ only manual speak if confidence >=50
  const confNum = parseInt(String(confidence.innerText).replace("%", ""), 10) || 0;
  if (confNum >= CONF_SPEAK_MIN) speak(text);
};
