const toggleBtn           = document.getElementById("toggleBtn");
const statusDot           = document.getElementById("statusDot");
const statusText          = document.getElementById("statusText");
const latencyBadge        = document.getElementById("latencyBadge");
const notSupportedWarning = document.getElementById("notSupportedWarning");

let isCapturing = false;

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  const url = tab?.url ?? "";
  const isRestricted = !url
    || url.startsWith("chrome://")
    || url.startsWith("edge://")
    || url.startsWith("about:")
    || url.startsWith("chrome-extension://");

  if (isRestricted) {
    notSupportedWarning.classList.add("show");
    toggleBtn.disabled = true;
    setStatus("idle", "Halaman ini tidak didukung");
    return;
  }

  const result = await chrome.storage.local.get(["isCapturing", "captureTabId", "latencyMs"]);
  isCapturing  = !!(result.isCapturing && result.captureTabId === tab.id);

  if (isCapturing && result.latencyMs) {
    latencyBadge.textContent = `${result.latencyMs}ms`;
    latencyBadge.classList.add("show");
  }

  toggleBtn.disabled = false;
  updateUI();
  checkServerHealth();
}

async function checkServerHealth() {
  try {
    const res = await fetch("http://localhost:8765/health", {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok && !isCapturing) setStatus("warn", "Server OK — siap dimulai");
  } catch {
    if (!isCapturing) setStatus("error", "Server tidak berjalan");
  }
}

function setStatus(type, text) {
  statusText.textContent = text;
  statusDot.className    = "status-dot";
  if (type === "active") statusDot.classList.add("active");
  if (type === "error")  statusDot.classList.add("error");
  if (type === "warn")   statusDot.classList.add("warn");
}

function updateUI() {
  if (isCapturing) {
    toggleBtn.textContent = "⏹  Stop Subtitle";
    toggleBtn.classList.add("active");
    setStatus("active", "Aktif — mendengarkan...");
  } else {
    toggleBtn.textContent = "▶  Mulai Subtitle";
    toggleBtn.classList.remove("active");
    latencyBadge.classList.remove("show");
  }
}

toggleBtn.addEventListener("click", async () => {
  toggleBtn.disabled    = true;
  toggleBtn.textContent = "Memproses...";
  setStatus("idle", "Memulai...");

  try {
    if (!isCapturing) {
      const response = await chrome.runtime.sendMessage({ type: "start_subtitle" });
      if (response?.success) {
        isCapturing = true;
      } else {
        setStatus("error", "❌ " + (response?.error || "Gagal memulai"));
      }
    } else {
      const response = await chrome.runtime.sendMessage({ type: "stop_subtitle" });
      if (response?.success) isCapturing = false;
    }
  } catch (err) {
    setStatus("error", "❌ " + err.message);
  }

  toggleBtn.disabled = false;
  updateUI();
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.latencyMs && isCapturing) {
    latencyBadge.textContent = `${changes.latencyMs.newValue}ms`;
    latencyBadge.classList.add("show");
  }
});

init();
