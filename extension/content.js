(function () {
  "use strict";

  if (window.__transliteInjected) return;
  window.__transliteInjected = true;

  let overlayEl    = null;
  let koreanEl     = null;
  let indonesianEl = null;
  let partialEl    = null;
  let statusEl     = null;
  let hideTimer    = null;
  let partialTimer = null;

  function createOverlay() {
    if (document.getElementById("ws-subtitle-overlay")) {
      overlayEl    = document.getElementById("ws-subtitle-overlay");
      koreanEl     = document.getElementById("ws-subtitle-korean");
      indonesianEl = document.getElementById("ws-subtitle-indonesian");
      partialEl    = document.getElementById("ws-subtitle-partial");
      statusEl     = document.getElementById("ws-subtitle-status");
      return;
    }

    overlayEl = document.createElement("div");
    overlayEl.id = "ws-subtitle-overlay";
    overlayEl.style.cssText = `
      position: fixed !important;
      bottom: 80px !important;
      left: 50% !important;
      transform: translateX(-50%) !important;
      z-index: 2147483647 !important;
      max-width: 80vw !important;
      min-width: 280px !important;
      text-align: center !important;
      pointer-events: none !important;
      transition: opacity 0.3s ease;
    `;

    overlayEl.innerHTML = `
      <div id="ws-subtitle-status"></div>
      <div id="ws-subtitle-partial"></div>
      <div id="ws-subtitle-korean"></div>
      <div id="ws-subtitle-indonesian"></div>
    `;
    document.documentElement.appendChild(overlayEl);

    koreanEl     = document.getElementById("ws-subtitle-korean");
    indonesianEl = document.getElementById("ws-subtitle-indonesian");
    partialEl    = document.getElementById("ws-subtitle-partial");
    statusEl     = document.getElementById("ws-subtitle-status");

    if (indonesianEl) {
      indonesianEl.style.cssText = `
        display: none; font-size: 22px; font-weight: 700;
        color: #ffffff; font-family: 'Segoe UI', sans-serif;
        text-shadow: -2px -2px 0 #000, 2px -2px 0 #000,
                     -2px 2px 0 #000, 2px 2px 0 #000, 0 0 8px rgba(0,0,0,0.9);
        background: rgba(0,0,0,0.6); padding: 6px 16px;
        border-radius: 6px; margin-bottom: 4px; line-height: 1.4;
      `;
    }
    if (koreanEl) {
      koreanEl.style.cssText = `
        display: none; font-size: 13px; color: #cccccc;
        font-family: 'Segoe UI', sans-serif;
        background: rgba(0,0,0,0.45); padding: 3px 12px;
        border-radius: 4px; margin-bottom: 4px;
      `;
    }
    if (partialEl) {
      partialEl.style.cssText = `
        display: none; font-size: 16px; font-weight: 400;
        color: #e8e8e8; font-family: 'Segoe UI', sans-serif;
        font-style: italic; opacity: 0.85;
        text-shadow: -1px -1px 0 #000, 1px -1px 0 #000,
                     -1px 1px 0 #000, 1px 1px 0 #000;
        background: rgba(0,0,0,0.45); padding: 4px 14px;
        border-radius: 5px; margin-bottom: 4px; line-height: 1.4;
        transition: opacity 0.15s ease;
      `;
    }
    if (statusEl) {
      statusEl.style.cssText = `
        display: block; font-size: 11px; color: #00e5ff;
        font-family: monospace; margin-bottom: 6px;
        text-shadow: 0 0 4px rgba(0,229,255,0.5);
      `;
    }
  }

  function showPartial(korean) {
    createOverlay();
    if (!korean) return;

    if (partialEl) {
      partialEl.textContent   = korean;
      partialEl.style.display = "block";
      partialEl.style.opacity = "0.8";
    }
    if (overlayEl) overlayEl.style.opacity = "1";

    if (hideTimer) clearTimeout(hideTimer);

    if (partialTimer) clearTimeout(partialTimer);
    partialTimer = setTimeout(() => {
      if (partialEl) {
        partialEl.style.opacity = "0";
        setTimeout(() => {
          if (partialEl) partialEl.style.display = "none";
        }, 150);
      }
    }, 3000);
  }

  function showSubtitle(korean, indonesian, latencyMs) {
    createOverlay();

    if (partialTimer) clearTimeout(partialTimer);
    if (partialEl) {
      partialEl.style.opacity = "0";
      setTimeout(() => {
        if (partialEl) partialEl.style.display = "none";
      }, 150);
    }

    if (indonesianEl) {
      indonesianEl.textContent   = indonesian || "";
      indonesianEl.style.display = indonesian ? "block" : "none";
    }
    if (koreanEl) {
      koreanEl.textContent   = "";
      koreanEl.style.display = "none";
    }
    if (statusEl) statusEl.textContent = "";

    if (overlayEl) overlayEl.style.opacity = "1";
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (overlayEl) overlayEl.style.opacity = "0";
    }, 5000);
  }

  function hideSubtitle() {
    if (overlayEl) overlayEl.style.opacity = "0";
    if (partialEl) partialEl.style.display = "none";
  }

  function setStatus(text, color) {
    createOverlay();
    if (statusEl) { statusEl.textContent = text; statusEl.style.color = color || "#00e5ff"; }
    if (overlayEl) overlayEl.style.opacity = "1";
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    switch (message.type) {
      case "show_partial":
        showPartial(message.korean);
        break;
      case "show_subtitle":
        showSubtitle(message.korean, message.indonesian, message.latency_ms);
        break;
      case "hide_subtitle":
        hideSubtitle();
        break;
      case "server_connected":
        setStatus("🟢 Server terhubung", "#4caf50");
        setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
        break;
      case "server_error":
        setStatus("🔴 " + (message.message || "Error server"), "#f44336");
        break;
      case "capture_error":
        setStatus("🔴 " + (message.message || "Error capture"), "#f44336");
        break;
      case "ping":
        sendResponse({ pong: true });
        break;
    }
    return false;
  });

  chrome.runtime.sendMessage({ type: "content_ready" }).catch(() => {});
})();
