class SubtitleProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._chunkSamples = 16000 * 0.25;

    this._silenceThreshold = 0.0008;
    this._consecutiveSilence = 0;
    this._maxSilenceFrames = 3;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const left  = input[0];
    const right = input[1] || input[0];

    let rms = 0;
    for (let i = 0; i < left.length; i++) {
      const s = (left[i] + right[i]) * 0.5;
      rms += s * s;
      this._buffer.push(s);
    }
    rms = Math.sqrt(rms / left.length);

    if (rms < this._silenceThreshold) {
      this._consecutiveSilence++;
      if (this._consecutiveSilence > this._maxSilenceFrames) {
        this._buffer = [];
        this._consecutiveSilence = 0;
        return true;
      }
    } else {
      this._consecutiveSilence = 0;
    }

    if (this._buffer.length >= this._chunkSamples) {
      const chunk = new Float32Array(this._buffer.splice(0, this._chunkSamples));
      this.port.postMessage({ type: "chunk", samples: chunk }, [chunk.buffer]);
    }

    return true;
  }
}

registerProcessor("subtitle-processor", SubtitleProcessor);
