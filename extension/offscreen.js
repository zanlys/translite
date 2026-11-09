const TARGET_SAMPLE_RATE = 16000;

let audioContext       = null;
let mediaStream        = null;
let workletNode        = null;
let playbackSource     = null;
let isCapturing        = false;
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
    playbackSource        = playbackContext.createMediaStreamSource(mediaStream);
    playbackSource.connect(playbackContext.destination);

    audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
    await audioContext.audioWorklet.addModule(chrome.runtime.getURL("audio-processor.js"));

    const sttSource = audioContext.createMediaStreamSource(mediaStream);

    workletNode = new AudioWorkletNode(audioContext, "subtitle-processor", {
      numberOfInputs:     1,
      numberOfOutputs:    1,
      outputChannelCount: [1],
    });

    workletNode.port.onmessage = (event) => {
      if (!isCapturing) return;
      if (event.data.type === "chunk") {
        handleAudioChunk(event.data.samples);
      }
    };

    sttSource.connect(workletNode);
    workletNode.connect(audioContext.destination);

    audioContext._playback = playbackContext;
    isCapturing            = true;

  } catch (err) {
    console.error("[Offscreen] Gagal:", err);
    chrome.runtime.sendMessage({
      type:  "offscreen_error",
      error: `Capture audio gagal: ${err.message}`,
    }).catch(() => {});
  }
}

function handleAudioChunk(samples) {
  for (let i = 0; i < samples.length; i++) {
    if (Math.abs(samples[i]) > 0.0001) {
      chrome.runtime.sendMessage({
        type: "audio_data",
        data: float32ToBase64(samples),
      }).catch((err) => {
        if (!err.message?.includes("context invalidated")) {
          console.warn("[Offscreen] Gagal kirim chunk:", err.message);
        }
      });
      return;
    }
  }
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
      if (playbackSource) {
        playbackSource.disconnect();
        playbackSource = null;
      }
      audioContext._playback.close().catch(() => {});
      audioContext._playback = null;
    }
    audioContext.close().catch(() => {});
    audioContext = null;
  }
}

function float32ToBase64(float32Array) {
  const uint8 = new Uint8Array(float32Array.buffer);
  return btoa(String.fromCharCode.apply(null, uint8));
}
