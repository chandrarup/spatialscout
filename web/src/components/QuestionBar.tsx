// The question bar: type a question, or pick a recorded example. Ticket 08 adds push-to-talk here.
import { useState } from "react";

interface Props {
  examples: string[];
  busy: boolean;
  onAsk: (question: string) => void;
}

export function QuestionBar({ examples, busy, onAsk }: Props) {
  const [question, setQuestion] = useState("");
  const ask = (text: string) => {
    const trimmed = text.trim();
    if (trimmed && !busy) onAsk(trimmed);
  };
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
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about a gene, a cell type and an assignment condition…"
          className="min-w-0 flex-1 rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          Ask
        </button>
      </div>
      {examples.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-ink-3">Recorded question:</span>
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
        </div>
      )}
    </form>
  );
}
