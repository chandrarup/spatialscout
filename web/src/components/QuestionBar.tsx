// The question bar: type a question, pick a recorded example, or hold the mic button to speak one. A transcript
// lands in the editable field and starts nothing until the researcher presses Ask.
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { MAX_SECONDS, type Recorder, VoiceError, startRecording } from "../voice";

interface Props {
  examples: string[];
  busy: boolean;
  onAsk: (question: string) => void;
}

type Voice = "idle" | "starting" | "recording" | "transcribing";
type Note = { kind: "info" | "error"; text: string } | null;

export function QuestionBar({ examples, busy, onAsk }: Props) {
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
    await transcribe(await active.stop());
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
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        ask(question);
      }}
    >
      <div className="flex gap-2">
        <label htmlFor="question" className="sr-only">
          Question
        </label>
        <input
          id="question"
          ref={input}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about a gene, a cell type and an assignment condition…"
          className="min-w-0 flex-1 rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none"
        />
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
          className={`flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm select-none disabled:cursor-not-allowed disabled:opacity-40 ${
            voice === "recording"
              ? "border-red-500/60 bg-red-500/15 text-red-300"
              : "border-line text-ink-2 hover:border-ink-3 hover:text-ink"
          }`}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="3" width="6" height="11" rx="3" />
            <path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" />
          </svg>
          <span className="hidden sm:inline">{{ idle: "Hold", starting: "Mic…", recording: "Release", transcribing: "…" }[voice]}</span>
        </button>
        <button
          type="submit"
          disabled={busy || !question.trim() || voice !== "idle"}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          Ask
        </button>
      </div>
      {note && (
        <p
          role={note.kind === "error" ? "alert" : "status"}
          className={`text-xs ${note.kind === "error" ? "text-red-300" : "text-ink-2"}`}
        >
          {note.text}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {examples.length > 0 && <span className="text-ink-3">Recorded question:</span>}
        {examples.map((example) => (
          <button
            key={example}
            type="button"
            disabled={busy}
            onClick={() => {
              setQuestion(example);
              ask(example);
            }}
            className="rounded-full border border-line px-3 py-1 text-ink-2 hover:border-ink-3 hover:text-ink disabled:opacity-40"
          >
            {example}
          </button>
        ))}
        <button
          type="button"
          disabled={busy || voice !== "idle"}
          onClick={() => void useSample()}
          className="rounded-full border border-dashed border-line px-3 py-1 text-ink-3 hover:border-ink-3 hover:text-ink disabled:opacity-40"
        >
          Transcribe the recorded clip
        </button>
      </div>
    </form>
  );
}
