// The question bar: type a question, pick a recorded example, or hold the mic button to speak one. A transcript
// lands in the editable field and starts nothing until the researcher presses Ask.
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { MAX_SECONDS, type Recorder, VoiceError, startRecording } from "../voice";

interface Props {
  examples: string[];
  busy: boolean;
  onAsk: (question: string) => void;
  placeholder?: string;
}

type Voice = "idle" | "starting" | "recording" | "transcribing";
type Note = { kind: "info" | "error"; text: string } | null;

export function QuestionBar({ examples, busy, onAsk, placeholder = "Ask about a gene, a cell type, a condition…" }: Props) {
  const [question, setQuestion] = useState("");
  const [voice, setVoice] = useState<Voice>("idle");
  const [note, setNote] = useState<Note>(null);
  const recorder = useRef<Recorder | null>(null);
  const held = useRef(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => () => recorder.current?.cancel(), []);

  const ask = (text: string) => {
    const trimmed = text.trim();
    if (trimmed && !busy) {
      setNote(null);
      onAsk(trimmed);
    }
  };

  const transcribe = async (wav: Blob) => {
    setVoice("transcribing");
    try {
      const result = await api.transcribe(wav);
      setQuestion(result.transcript);
      const mode = result.run_mode === "live" ? "live" : "stored response, cached tool rerun";
      setNote({ kind: "info", text: `Transcribed (${mode}). Check and edit the question, then press Ask.` });
      input.current?.focus();
    } catch (error) {
      setNote({ kind: "error", text: error instanceof Error ? error.message : String(error) });
      input.current?.focus();
    } finally {
      setVoice("idle");
    }
  };

  const finish = async () => {
    held.current = false;
    const active = recorder.current;
    recorder.current = null;
    if (!active) return;
    let wav: Blob;
    try {
      wav = await active.stop();
    } catch (error) {
      setVoice("idle");
      setNote({ kind: "error", text: error instanceof VoiceError ? error.message : "Recording failed. Type your question instead." });
      input.current?.focus();
      return;
    }
    await transcribe(wav);
  };

  const begin = async () => {
    if (voice !== "idle" || busy) return;
    held.current = true;
    setNote(null);
    setVoice("starting");
    try {
      const started = await startRecording(() => {
        setNote({ kind: "info", text: `Recording stopped at the ${MAX_SECONDS}-second limit.` });
        void finish();
      });
      if (!held.current) {
        // Released while the microphone was still opening (often at the permission prompt): send nothing.
        started.cancel();
        setVoice("idle");
        setNote({ kind: "info", text: "The microphone is ready. Hold the button while you speak, then release." });
        return;
      }
      recorder.current = started;
      setVoice("recording");
    } catch (error) {
      held.current = false;
      setVoice("idle");
      setNote({ kind: "error", text: error instanceof VoiceError ? error.message : "Recording failed. Type your question instead." });
      input.current?.focus();
    }
  };

  const release = () => {
    held.current = false;
    if (recorder.current) void finish();
  };

  const useSample = async () => {
    setNote(null);
    try {
      await transcribe(await api.sampleClip());
    } catch (error) {
      setNote({ kind: "error", text: error instanceof Error ? error.message : String(error) });
    }
  };

  const micLabel = {
    idle: "Hold to speak",
    starting: "Opening the microphone…",
    recording: "Recording… release to send",
    transcribing: "Transcribing…",
  }[voice];

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        ask(question);
      }}
    >
      {examples.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-[12px] text-ink-3">Recorded questions, ready to replay</p>
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              disabled={busy}
              onClick={() => {
                setQuestion(example);
                ask(example);
              }}
              className="rounded-2xl bg-raised px-3.5 py-2.5 text-left text-[13px] leading-snug text-ink transition-colors hover:bg-[#2a2d32] active:scale-[0.99] disabled:opacity-40"
            >
              {example}
            </button>
          ))}
          <button
            type="button"
            disabled={busy || voice !== "idle"}
            onClick={() => void useSample()}
            className="self-start rounded-full px-1 py-1 text-[12px] text-ink-3 underline-offset-4 hover:text-ink hover:underline disabled:opacity-40"
          >
            Transcribe the recorded spoken question
          </button>
        </div>
      )}
      {note && (
        <p role={note.kind === "error" ? "alert" : "status"} className={`text-[12px] ${note.kind === "error" ? "text-bad" : "text-ink-2"}`}>
          {note.text}
        </p>
      )}
      <div className="flex items-center gap-2 rounded-full bg-raised p-1.5 pl-4">
        <label htmlFor="question" className="sr-only">
          Question
        </label>
        {voice === "recording" || voice === "transcribing" || voice === "starting" ? (
          <span className="flex min-w-0 flex-1 items-center gap-3 text-[14px] text-ink" role="status">
            <span className="flex h-5 items-center gap-[3px]" aria-hidden="true">
              {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                <span key={i} className={`wave-bar w-[3px] rounded-full ${voice === "recording" ? "bg-stable" : "bg-ink-3"}`} style={{ animationDelay: `${i * 90}ms` }} />
              ))}
            </span>
            <span className={voice === "transcribing" ? "shimmer-text" : ""}>{voice === "recording" ? "Listening… release to send" : voice === "transcribing" ? "Muse Voice is transcribing…" : "Opening the microphone…"}</span>
          </span>
        ) : (
          <input
            id="question"
            ref={input}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={placeholder}
            className="min-w-0 flex-1 bg-transparent text-[14px] text-ink placeholder:text-ink-3 focus:outline-none"
          />
        )}
        <button
          type="button"
          aria-label={micLabel}
          title={`${micLabel} (up to ${MAX_SECONDS} s). Space also works while focused.`}
          aria-pressed={voice === "recording"}
          disabled={busy || voice === "transcribing"}
          onPointerDown={(event) => {
            if (event.button !== 0) return;
            event.currentTarget.setPointerCapture(event.pointerId);
            void begin();
          }}
          onPointerUp={release}
          onPointerCancel={release}
          onKeyDown={(event) => {
            if ((event.key === " " || event.key === "Enter") && !event.repeat) {
              event.preventDefault();
              void begin();
            }
          }}
          onKeyUp={(event) => {
            if (event.key === " " || event.key === "Enter") {
              event.preventDefault();
              release();
            }
          }}
          onContextMenu={(event) => event.preventDefault()}
          className={`flex h-9 shrink-0 items-center gap-1.5 rounded-full px-3 select-none touch-none transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
            voice === "recording" ? "talk-live bg-stable text-black" : "bg-[#2a2d32] text-ink hover:bg-[#33363c]"
          }`}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <path d="M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4" />
          </svg>
          <span className="text-[13px] font-medium">{voice === "recording" ? "Release" : "Talk"}</span>
        </button>
        <button
          type="submit"
          disabled={busy || !question.trim() || voice !== "idle"}
          className="h-9 shrink-0 rounded-full bg-white px-4 text-[14px] font-medium text-black transition-transform active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
        >
          Ask
        </button>
      </div>
    </form>
  );
}
