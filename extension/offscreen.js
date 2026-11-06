const TARGET_SAMPLE_RATE = 16000;

let audioContext = null;
let mediaStream = null;
let workletNode = null;
let isCapturing = false;

const latencyLog = {
  captureToSend: [],
  maxSamples: 50,
  add(arr, val) {
    arr.push(val);
    if (arr.length > this.maxSamples) arr.shift();
  },
  p50(arr) {
    if (!arr.length) return 0;
    const sorted = [...arr].sort((a,b) => a-b);
    return sorted[Math.floor(sorted.length * 0.5)];
  },
  p95(arr) {
    if (!arr.length) return 0;
    const sorted = [...arr].sort((a,b) => a-b);
    return sorted[Math.floor(sorted.length * 0.95)];
  },
  report() {
    console.log(`[Latency] capture→send p50=${this.p50(this.captureToSend).toFixed(1)}ms p95=${this.p95(this.captureToSend).toFixed(1)}ms (n=${this.captureToSend.length})`);
  }
};
let latencyReportTimer = null;

chrome.runtime.sendMessage({ type: "offscreen_ready" }).catch(() => {});

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "start_capture") {
    startAudioCapture(message.streamId);
  } else if (message.type === "stop_capture") {
    stopAudioCapture();
  }
  return false;
});

async function startAudioCapture(streamId) {
  if (isCapturing) return;

  console.log("[Offscreen] Mulai capture, streamId:", streamId?.substring(0, 20));

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource:   "tab",
          chromeMediaSourceId: streamId,
        },
      },
      video: false,
    });

    const playbackContext = new AudioContext();
    const playbackSource  = playbackContext.createMediaStreamSource(mediaStream);
    playbackSource.connect(playbackContext.destination);

    audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });

    await audioContext.audioWorklet.addModule(
      chrome.runtime.getURL("audio-processor.js")
    );

    const sttSource = audioContext.createMediaStreamSource(mediaStream);

    workletNode = new AudioWorkletNode(audioContext, "subtitle-processor", {
      numberOfInputs:     1,
      numberOfOutputs:    1,
      outputChannelCount: [1],
    });

    workletNode.port.onmessage = (event) => {
      if (!isCapturing) return;
      if (event.data.type === "chunk") {
        handleAudioChunk(event.data.samples, event.data.seq, event.data.captureTs);
      }
    };

    sttSource.connect(workletNode);
    workletNode.connect(audioContext.destination);

    audioContext._playback = playbackContext;
    isCapturing = true;

    latencyReportTimer = setInterval(() => latencyLog.report(), 30000);

    console.log("[Offscreen] Capture aktif, chunk size: 100ms");

  } catch (err) {
    console.error("[Offscreen] Gagal:", err);
    chrome.runtime.sendMessage({
      type:  "offscreen_error",
      error: `Capture audio gagal: ${err.message}`,
    }).catch(() => {});
  }
}

function handleAudioChunk(samples, seq, captureTs) {
  let hasAudio = false;
  for (let i = 0; i < samples.length; i++) {
    if (Math.abs(samples[i]) > 0.0001) { hasAudio = true; break; }
  }
  if (!hasAudio) return;

  const sendTs = performance.now();
  const base64 = float32ToBase64(samples);

  chrome.runtime.sendMessage({
    type:      "audio_data",
    data:      base64,
    seq:       seq,
    captureTs: captureTs,
    sendTs:    sendTs,
  }).catch((err) => {
    if (!err.message?.includes("context invalidated")) {
      console.warn("[Offscreen] Gagal kirim chunk:", err.message);
    }
  });
}

function stopAudioCapture() {
  if (!isCapturing) return;
  isCapturing = false;

  if (latencyReportTimer) {
    clearInterval(latencyReportTimer);
    latencyReportTimer = null;
    latencyLog.report();
  }

  if (workletNode) {
    workletNode.disconnect();
    workletNode.port.onmessage = null;
    workletNode = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }

  if (audioContext) {
    if (audioContext._playback) {
      audioContext._playback.close().catch(() => {});
      audioContext._playback = null;
    }
    audioContext.close().catch(() => {});
    audioContext = null;
  }

  console.log("[Offscreen] Capture dihentikan.");
}

function float32ToBase64(float32Array) {
  const uint8     = new Uint8Array(float32Array.buffer);
  let   binary    = "";
  const chunkSize = 8192;
  for (let i = 0; i < uint8.length; i += chunkSize) {
    binary += String.fromCharCode(...uint8.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}
