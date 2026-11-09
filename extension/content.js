(function () {
  "use strict";

  if (window.__transliteInjected) return;
  window.__transliteInjected = true;

  let overlayEl      = null;
  let indonesianEl   = null;
  let statusEl       = null;
  let hideTimer      = null;
  let overlayCreated = false;

  function createOverlay() {
    if (overlayCreated) return;

    overlayEl = document.getElementById("ws-subtitle-overlay");
    if (overlayEl) {
      indonesianEl = document.getElementById("ws-subtitle-indonesian");
      statusEl     = document.getElementById("ws-subtitle-status");
      overlayCreated = true;
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
      <div id="ws-subtitle-indonesian"></div>
    `;
    document.documentElement.appendChild(overlayEl);

    indonesianEl = document.getElementById("ws-subtitle-indonesian");
    statusEl     = document.getElementById("ws-subtitle-status");
    overlayCreated = true;

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
    if (statusEl) {
      statusEl.style.cssText = `
        display: block; font-size: 11px; color: #00e5ff;
        font-family: monospace; margin-bottom: 6px;
        text-shadow: 0 0 4px rgba(0,229,255,0.5);
      `;
    }
  }

  function showSubtitle(indonesian) {
    createOverlay();

    if (indonesianEl) {
      indonesianEl.textContent   = indonesian || "";
      indonesianEl.style.display = indonesian ? "block" : "none";
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
  }

  function setStatus(text, color) {
    createOverlay();
    if (statusEl) { statusEl.textContent = text; statusEl.style.color = color || "#00e5ff"; }
    if (overlayEl) overlayEl.style.opacity = "1";
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    switch (message.type) {
      case "show_subtitle":
        showSubtitle(message.indonesian);
        break;
      case "hide_subtitle":
        hideSubtitle();
        break;
      case "server_connected":
        setStatus("Server terhubung", "#4caf50");
        setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
        break;
      case "server_error":
        setStatus("Error server: " + (message.message || ""), "#f44336");
        break;
      case "capture_error":
        setStatus("Error capture: " + (message.message || ""), "#f44336");
        break;
      case "ping":
        sendResponse({ pong: true });
        break;
    }
    return false;
  });

  chrome.runtime.sendMessage({ type: "content_ready" }).catch(() => {});
})();
