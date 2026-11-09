const WS_URL        = "ws://localhost:8765/ws";
const OFFSCREEN_URL = chrome.runtime.getURL("offscreen.html");
const MAX_RECONNECT = 5;

let ws                  = null;
let captureTabId        = null;
let isCapturing         = false;
let activeSubtitleTabId = null;
let reconnectTimer      = null;
let reconnectCount      = 0;
let latestSubtitleSeq   = -1;
let latencyMs           = 0;
let latencyWriteTimer   = null;

function connectWebSocket() {
  return new Promise((resolve, reject) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      resolve();
      return;
    }

    if (ws && ws.readyState === WebSocket.CONNECTING) {
      const cek = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          clearInterval(cek); resolve();
        } else if (!ws || ws.readyState === WebSocket.CLOSED) {
          clearInterval(cek); reject(new Error("WebSocket gagal terhubung"));
        }
      }, 100);
      return;
    }

    const timeout = setTimeout(() => {
      reject(new Error("Server tidak merespons. Pastikan server Python sudah jalan."));
    }, 5000);

    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      clearTimeout(timeout);
      reconnectCount = 0;
      broadcastToContent({ type: "server_connected" });
      resolve();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "subtitle") {
          const seq = data.seq ?? 0;
          if (seq <= latestSubtitleSeq) return;
          latestSubtitleSeq = seq;
          latencyMs = data.latency_ms;

          if (latencyWriteTimer) clearTimeout(latencyWriteTimer);
          latencyWriteTimer = setTimeout(() => {
            chrome.storage.local.set({ latencyMs }).catch(() => {});
          }, 5000);

          if (activeSubtitleTabId) {
            chrome.tabs.sendMessage(activeSubtitleTabId, {
              type:       "show_subtitle",
              indonesian: data.indonesian,
              seq,
            }).catch(() => {
              injectSubtitleLangsung(activeSubtitleTabId, data.indonesian);
            });
          }
        }
      } catch (e) {
        console.error("[BG] Error parse WS:", e);
      }
    };

    ws.onerror = () => { clearTimeout(timeout); };

    ws.onclose = () => {
      ws = null;
      if (isCapturing && reconnectCount < MAX_RECONNECT) {
        reconnectCount++;
        const delay = Math.min(1000 * 2 ** reconnectCount, 30000);
        console.log(`[BG] Reconnect ${reconnectCount}/${MAX_RECONNECT} dalam ${delay}ms`);
        reconnectTimer = setTimeout(() => connectWebSocket().catch(console.error), delay);
      } else if (reconnectCount >= MAX_RECONNECT) {
        console.warn("[BG] Max reconnect tercapai, berhenti retry.");
        broadcastToContent({ type: "server_error", message: "Server tidak dapat dijangkau. Restart server dan klik Stop lalu Start lagi." });
        isCapturing = false;
        chrome.storage.local.set({ isCapturing: false }).catch(() => {});
      }
    };
  });
}

function sendAudioChunk(base64Data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "audio_chunk", data: base64Data }));
  }
}

function broadcastToContent(message) {
  if (activeSubtitleTabId) {
    chrome.tabs.sendMessage(activeSubtitleTabId, message).catch(() => {});
  }
}

function injectSubtitleLangsung(tabId, indonesian) {
  const ind = (indonesian || "").replace(/\\/g, "\\\\").replace(/`/g, "'");

  chrome.scripting.executeScript({
    target: { tabId },
    func: (ind) => {
      let overlay = document.getElementById("ws-subtitle-overlay");
      if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "ws-subtitle-overlay";
        overlay.style.cssText = [
          "position:fixed", "bottom:80px", "left:50%",
          "transform:translateX(-50%)", "z-index:2147483647",
          "max-width:80vw", "min-width:280px", "text-align:center",
          "pointer-events:none", "transition:opacity 0.3s",
        ].join("!important;") + "!important;";
        overlay.innerHTML = [
          '<div id="ws-subtitle-status" style="font-size:11px;color:#00e5ff;font-family:monospace;margin-bottom:6px;"></div>',
          '<div id="ws-subtitle-indonesian" style="font-size:22px;font-weight:700;color:#fff;text-shadow:-2px -2px 0 #000,2px -2px 0 #000,-2px 2px 0 #000,2px 2px 0 #000;background:rgba(0,0,0,.6);padding:6px 16px;border-radius:6px;margin-bottom:4px;line-height:1.4;font-family:sans-serif;"></div>',
        ].join("");
        document.documentElement.appendChild(overlay);
      }
      const idEl = document.getElementById("ws-subtitle-indonesian");
      const stEl = document.getElementById("ws-subtitle-status");
      if (idEl) { idEl.textContent = ind; idEl.style.display = ind ? "block" : "none"; }
      if (stEl) stEl.textContent = "";
      overlay.style.opacity = "1";
      if (window.__wsHideTimer) clearTimeout(window.__wsHideTimer);
      window.__wsHideTimer = setTimeout(() => { overlay.style.opacity = "0"; }, 5000);
    },
    args: [ind],
  }).catch(e => console.error("[BG] executeScript gagal:", e.message));
}

async function ensureOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ["OFFSCREEN_DOCUMENT"],
  }).catch(() => []);
  if (existingContexts.length > 0) return;
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_URL,
    reasons: ["USER_MEDIA"],
    justification: "Capture audio tab untuk subtitle real time",
  });
}

async function closeOffscreenDocument() {
  await chrome.offscreen.closeDocument().catch(() => {});
}

async function startCapture(tabId) {
  if (isCapturing) return { success: true };

  try {
    activeSubtitleTabId = tabId;
    latestSubtitleSeq   = -1;
    reconnectCount      = 0;

    const streamId = await new Promise((resolve, reject) => {
      chrome.tabCapture.getMediaStreamId({ targetTabId: tabId }, (id) => {
        if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
        else if (!id) reject(new Error("Gagal mendapat stream ID."));
        else resolve(id);
      });
    });

    await connectWebSocket();
    await ensureOffscreenDocument();
    await chrome.runtime.sendMessage({ type: "start_capture", streamId });

    isCapturing  = true;
    captureTabId = tabId;
    await chrome.storage.local.set({ isCapturing: true, captureTabId: tabId });
    return { success: true };

  } catch (err) {
    console.error("[BG] startCapture error:", err.message);
    broadcastToContent({ type: "capture_error", message: err.message });
    await chrome.offscreen.closeDocument().catch(() => {});
    isCapturing         = false;
    activeSubtitleTabId = null;
    return { success: false, error: err.message };
  }
}

async function stopCapture() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  if (latencyWriteTimer) { clearTimeout(latencyWriteTimer); latencyWriteTimer = null; }

  await chrome.runtime.sendMessage({ type: "stop_capture" }).catch(() => {});

  if (ws) {
    try { ws.send(JSON.stringify({ type: "reset" })); } catch (_) {}
    ws.close();
    ws = null;
  }

  await closeOffscreenDocument();

  const prevTab       = activeSubtitleTabId;
  isCapturing         = false;
  captureTabId        = null;
  activeSubtitleTabId = null;
  latestSubtitleSeq   = -1;
  reconnectCount      = 0;
  await chrome.storage.local.set({ isCapturing: false, captureTabId: null });

  if (prevTab) chrome.tabs.sendMessage(prevTab, { type: "hide_subtitle" }).catch(() => {});
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  switch (message.type) {
    case "start_subtitle":
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs[0]) { sendResponse({ success: false, error: "Tidak ada tab aktif" }); return; }
        startCapture(tabs[0].id).then(sendResponse);
      });
      return true;

    case "stop_subtitle":
      stopCapture().then(() => sendResponse({ success: true }));
      return true;

    case "get_status":
      sendResponse({ isCapturing, captureTabId, latencyMs });
      return false;

    case "audio_data":
      if (message.data) sendAudioChunk(message.data);
      return false;

    case "content_ready":
    case "offscreen_ready":
      return false;

    case "offscreen_error":
      broadcastToContent({ type: "capture_error", message: message.error });
      stopCapture();
      return false;
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === captureTabId) stopCapture();
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (tabId === captureTabId && changeInfo.url) stopCapture();
});
