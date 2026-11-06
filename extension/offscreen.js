const TARGET_SAMPLE_RATE = 16000;

let audioContext = null;
let mediaStream = null;
let workletNode = null;
let isCapturing = false;

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
      if (event.data.type === "chunk") handleAudioChunk(event.data.samples);
    };

    sttSource.connect(workletNode);
    workletNode.connect(audioContext.destination);

    audioContext._playback = playbackContext;
    isCapturing = true;

    console.log("[Offscreen] Capture aktif.");

  } catch (err) {
    console.error("[Offscreen] Gagal:", err);
    chrome.runtime.sendMessage({
      type:  "offscreen_error",
      error: `Capture audio gagal: ${err.message}`,
    }).catch(() => {});
  }
}

function handleAudioChunk(samples) {
  let rms = 0;
  for (let i = 0; i < samples.length; i++) rms += samples[i] * samples[i];
  rms = Math.sqrt(rms / samples.length);
  if (rms < 0.001) return;

  const base64 = float32ToBase64(samples);
  chrome.runtime.sendMessage({ type: "audio_data", data: base64 })
    .catch((err) => console.warn("[Offscreen] Gagal kirim:", err.message));
}

function stopAudioCapture() {
  if (!isCapturing) return;
  isCapturing = false;

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
