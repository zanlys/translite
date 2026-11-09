class SubtitleProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._chunkSamples = 16000 * 0.1;
    this._buffer       = [];
    this._chunkSeq     = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const left  = input[0];
    const right = input[1] || input[0];

    for (let i = 0; i < left.length; i++) {
      this._buffer.push((left[i] + right[i]) * 0.5);
    }

    while (this._buffer.length >= this._chunkSamples) {
      const chunk = new Float32Array(this._buffer.splice(0, this._chunkSamples));
      this.port.postMessage({
        type:      "chunk",
        samples:   chunk,
        seq:       this._chunkSeq++,
        captureTs: currentTime,
      }, [chunk.buffer]);
    }

    return true;
  }
}

registerProcessor("subtitle-processor", SubtitleProcessor);
