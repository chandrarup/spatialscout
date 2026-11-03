// Push-to-talk recording in the browser: capture PCM from the microphone with the Web Audio API, then encode the
// 16-bit mono WAV at 16 kHz that Muse Voice Transcribe accepts. No server-side conversion.

export const TARGET_RATE_HZ = 16_000;
export const MAX_SECONDS = 30; // the server refuses longer clips (gateway/audio.py)

export class VoiceError extends Error {}

export interface Recorder {
  /** Stop capturing and return the clip as a WAV file. */
  stop: () => Promise<Blob>;
  /** Stop capturing and discard the clip. */
  cancel: () => void;
}

/** Ask for the microphone and start capturing. Rejects with a VoiceError the question bar can show. */
export async function startRecording(onLimit: () => void): Promise<Recorder> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new VoiceError("This browser cannot record audio here. Type your question instead.");
  }
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
  } catch (error) {
    const name = error instanceof DOMException ? error.name : "";
    if (name === "NotAllowedError" || name === "SecurityError") {
      throw new VoiceError("Microphone permission was refused. Allow it in the browser, or type your question.");
    }
    if (name === "NotFoundError" || name === "OverconstrainedError") {
      throw new VoiceError("No microphone was found. Type your question instead.");
    }
    throw new VoiceError("The microphone could not be opened. Type your question instead.");
  }

  // Capture at the device's own rate: some browsers refuse a microphone stream into a context at another rate.
  const context = new AudioContext();
  // Created after the permission prompt, outside the user gesture, so Safari may start it suspended.
  await context.resume().catch(() => undefined);
  const input = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  let samples = 0;
  const limit = MAX_SECONDS * context.sampleRate;
  let limited = false;
  processor.onaudioprocess = (event) => {
    if (samples >= limit) {
      if (!limited) {
        limited = true;
        onLimit();
      }
      return;
    }
    const channel = event.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(channel));
    samples += channel.length;
  };
  input.connect(processor);
  processor.connect(context.destination);

  const release = () => {
    processor.onaudioprocess = null;
    processor.disconnect();
    input.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    void context.close();
  };

  return {
    cancel: release,
    stop: async () => {
      const sourceRate = context.sampleRate;
      release();
      if (samples === 0) {
        throw new VoiceError("No sound arrived from the microphone. Check it is not muted, or type your question.");
      }
      const pcm = new Float32Array(Math.min(samples, limit));
      let offset = 0;
      for (const chunk of chunks) {
        if (offset >= pcm.length) break;
        pcm.set(chunk.subarray(0, pcm.length - offset), offset);
        offset += chunk.length;
      }
      return encodeWav(await resample(pcm, sourceRate, TARGET_RATE_HZ), TARGET_RATE_HZ);
    },
  };
}

async function resample(pcm: Float32Array<ArrayBuffer>, fromHz: number, toHz: number): Promise<Float32Array> {
  if (pcm.length === 0 || fromHz === toHz) return pcm;
  const length = Math.max(1, Math.round((pcm.length * toHz) / fromHz));
  const offline = new OfflineAudioContext(1, length, toHz);
  const buffer = offline.createBuffer(1, pcm.length, fromHz);
  buffer.copyToChannel(pcm, 0);
  const node = offline.createBufferSource();
  node.buffer = buffer;
  node.connect(offline.destination);
  node.start();
  return (await offline.startRendering()).getChannelData(0);
}

/** A RIFF/WAVE file of mono 16-bit little-endian PCM. */
export function encodeWav(pcm: Float32Array, rateHz: number): Blob {
  const bytes = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(bytes);
  const text = (at: number, value: string) => [...value].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
  text(0, "RIFF");
  view.setUint32(4, 36 + pcm.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, rateHz, true);
  view.setUint32(28, rateHz * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  text(36, "data");
  view.setUint32(40, pcm.length * 2, true);
  pcm.forEach((sample, i) => {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  });
  return new Blob([bytes], { type: "audio/wav" });
}
