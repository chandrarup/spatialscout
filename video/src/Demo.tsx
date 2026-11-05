import { AbsoluteFill, Easing, OffthreadVideo, Series, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import marksJson from "./marks.json";
import cursorJson from "./cursor.json";
import { Intro, INTRO_FRAMES } from "./Intro";
import { Outro, OUTRO_FRAMES } from "./Outro";
import { C, FONT } from "./ui";

type Mark = { name: string; t: number; rect: number[] | null };
const MARKS = marksJson as Mark[];
const FPS = 30;
const W = 1920;
const H = 1080;
const MAX_RATE = 2.5;
const CARD = 0.9;

type Shot = { from: string; to: string; dur: number; zoom?: string; title?: string; maxZoom?: number; maxRate?: number; keep?: "start" | "end" };

// Order follows docs/demo-script.md; the capture ran depth before the verdict, so those shots are reordered here.
const SHOTS: Shot[] = [
  { from: "overview", to: "explore", dur: 13, title: "Two real kidney biopsies" },
  { from: "explore", to: "zoom-top", dur: 4, title: "Healthy vs diseased, side by side" },
  { from: "zoom-top", to: "box-top", dur: 3, zoom: "zoom-top", title: "Each specimen moves on its own" },
  { from: "box-top", to: "box-top-result", dur: 4, zoom: "box-top", title: "Draw a region" },
  { from: "box-top-result", to: "box-bottom", dur: 3, zoom: "box-top-result", title: "Protein audit on exactly this box", maxZoom: 2 },
  { from: "box-bottom", to: "box-bottom-result", dur: 3, zoom: "box-bottom", title: "Same on the diseased biopsy" },
  { from: "box-bottom-result", to: "ask-both", dur: 3, zoom: "box-bottom-result", maxZoom: 2 },
  { from: "ask-both", to: "data-fit", dur: 6, zoom: "question", title: "Ask about both regions", maxZoom: 1.6 },
  { from: "data-fit", to: "go-live", dur: 3, zoom: "data-fit", maxZoom: 1.6 },
  { from: "go-live", to: "live-running", dur: 5, title: "Live: Muse Wonder writes the plan" },
  { from: "follow", to: "resize", dur: 8, zoom: "team", title: "Here's one I made earlier", maxZoom: 1.5 },
  { from: "resize", to: "evidence", dur: 9, title: "The research team at work" },
  { from: "findings", to: "verdict-2", dur: 10, zoom: "verdict-1", title: "Part 1 · Confirmed", maxZoom: 1.8 },
  { from: "verdict-2", to: "challenge", dur: 12, zoom: "verdict-2", title: "Part 2 · Refuted, with caveats", maxZoom: 1.8 },
  { from: "evidence", to: "depth", dur: 3, title: "Molecules at measured depth" },
  { from: "depth", to: "orbit", dur: 1.2 },
  { from: "orbit", to: "slice", dur: 6, title: "Orbit in 3D, at measured depth" },
  { from: "challenge", to: "failed", dur: 6, zoom: "challenge", title: "Try to cheat the verifier", maxZoom: 1.8 },
  { from: "failed", to: "package", dur: 8, zoom: "failed", title: "Altered claim: caught", maxZoom: 1.8 },
  { from: "package", to: "end", dur: 12, zoom: "package", title: "Evidence package and next experiment", maxZoom: 1.5 },
];

const at = (name: string) => MARKS.find((m) => m.name === name);

type Clip = Shot & { start: number; end: number; rate: number; frames: number; rect: number[] | null };

function clips(): Clip[] {
  const out: Clip[] = [];
  for (const s of SHOTS) {
    const a = at(s.from);
    const b = at(s.to) ?? MARKS[MARKS.indexOf(a as Mark) + 1];
    if (!a || !b || b.t <= a.t) continue;
    const span = b.t - a.t;
    let rate = span / s.dur;
    let start = a.t;
    let end = b.t;
    const cap = s.maxRate ?? MAX_RATE;
    if (rate > cap) {
      rate = cap;
      if (s.keep === "start") end = a.t + s.dur * cap;
      else start = b.t - s.dur * cap;
    }
    rate = Math.max(rate, 0.5);
    const frames = Math.round(((end - start) / rate) * FPS);
    out.push({ ...s, start, end, rate, frames, rect: s.zoom ? at(s.zoom)?.rect ?? null : null });
  }
  return out;
}

export const CLIPS = clips();
export const SCREEN_FRAMES = CLIPS.reduce((n, c) => n + c.frames, 0);
export const DEMO_FRAMES = INTRO_FRAMES + SCREEN_FRAMES + OUTRO_FRAMES;

function camera(rect: number[] | null, maxZoom: number) {
  if (!rect) return { s: 1, x: 0, y: 0 };
  const [rx, ry, rw, rh] = rect;
  const s = Math.max(1, Math.min(maxZoom, W / rw, H / rh));
  const cx = rx + rw / 2;
  const cy = ry + rh / 2;
  const x = Math.min(Math.max(W / 2 - cx * s, W - W * s), 0);
  const y = Math.min(Math.max(H / 2 - cy * s, H - H * s), 0);
  return { s, x, y };
}

const PATH = (cursorJson as { path: number[][]; clicks: number[] }).path;
const CLICKS = (cursorJson as { path: number[][]; clicks: number[] }).clicks;
const CARD_X = (W * (1 - CARD)) / 2;
const CARD_Y = (H * (1 - CARD)) / 2 - 22;

function pointer(t: number) {
  if (t <= PATH[0][0]) return { x: PATH[0][1], y: PATH[0][2] };
  for (let i = 1; i < PATH.length; i++) {
    const [t1, x1, y1] = PATH[i];
    if (t <= t1) {
      const [t0, x0, y0] = PATH[i - 1];
      const u = t1 > t0 ? (t - t0) / (t1 - t0) : 1;
      const e = u * u * (3 - 2 * u);
      return { x: x0 + (x1 - x0) * e, y: y0 + (y1 - y0) * e };
    }
  }
  const last = PATH[PATH.length - 1];
  return { x: last[1], y: last[2] };
}

function Cursor({ t, rate, place }: { t: number; rate: number; place: (x: number, y: number) => { x: number; y: number } }) {
  const p = pointer(t);
  const { x, y } = place(p.x, p.y);
  if (x < CARD_X || y < CARD_Y || x > CARD_X + W * CARD || y > CARD_Y + H * CARD) return null;
  const ages = CLICKS.map((c) => (t - c) / rate).filter((a) => a >= 0 && a < 0.6);
  const press = ages.some((a) => a < 0.16) ? 0.82 : 1;
  return (
    <>
      {ages.map((a, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: x - 14,
            top: y - 14,
            width: 28,
            height: 28,
            borderRadius: 14,
            border: `3px solid ${C.rna}`,
            transform: `scale(${1 + (a / 0.6) * 2.6})`,
            opacity: 1 - a / 0.6,
          }}
        />
      ))}
      <svg width={34} height={34} viewBox="0 0 24 24" style={{ position: "absolute", left: x - 5, top: y - 3, transform: `scale(${press})`, transformOrigin: "5px 3px", filter: "drop-shadow(0 3px 6px rgba(0,0,0,0.55))" }}>
        <path d="M5 3 L5 20 L9.5 15.8 L12.6 22 L15.3 20.7 L12.3 14.6 L18.5 14.6 Z" fill="#fff" stroke="#111" strokeWidth={1.3} strokeLinejoin="round" />
      </svg>
    </>
  );
}

function Title({ text }: { text: string }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = spring({ frame: frame - 4, fps, config: { damping: 200 } });
  return (
    <div
      style={{
        position: "absolute",
        left: 96,
        bottom: 34,
        fontFamily: FONT,
        fontSize: 30,
        fontWeight: 600,
        color: C.ink,
        display: "flex",
        alignItems: "center",
        gap: 14,
        opacity: k,
        transform: `translateY(${(1 - k) * 16}px)`,
      }}
    >
      <span style={{ width: 10, height: 10, borderRadius: 5, background: C.rna, boxShadow: `0 0 16px ${C.rna}` }} />
      {text}
    </div>
  );
}

function Shot({ clip, title }: { clip: Clip; title: string | null }) {
  const frame = useCurrentFrame();
  const cam = camera(clip.rect, clip.maxZoom ?? 2.2);
  const inK = interpolate(frame, [0, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const outK = interpolate(frame, [clip.frames - 14, clip.frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const k = Math.min(inK, outK);
  const s = 1 + (cam.s - 1) * k;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 30% 0%, #16213a 0%, ${C.bg} 60%)` }}>
      <div
        style={{
          position: "absolute",
          left: CARD_X,
          top: CARD_Y,
          width: W * CARD,
          height: H * CARD,
          borderRadius: 18,
          overflow: "hidden",
          boxShadow: "0 30px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.08)",
        }}
      >
        <div style={{ width: W, height: H, transformOrigin: "0 0", transform: `scale(${CARD}) translate(${cam.x * k}px, ${cam.y * k}px) scale(${s})` }}>
          <OffthreadVideo
            src={staticFile("screen.webm")}
            startFrom={Math.round(clip.start * FPS)}
            endAt={Math.round(clip.end * FPS)}
            playbackRate={clip.rate}
            muted
            style={{ width: W, height: H }}
          />
        </div>
      </div>
      <Cursor
        t={clip.start + (frame / FPS) * clip.rate}
        rate={clip.rate}
        place={(px, py) => ({ x: CARD_X + CARD * (px * s + cam.x * k), y: CARD_Y + CARD * (py * s + cam.y * k) })}
      />
      {title && <Title text={title} />}
    </AbsoluteFill>
  );
}

export function Demo() {
  let title: string | null = null;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Series>
        <Series.Sequence durationInFrames={INTRO_FRAMES}>
          <Intro />
        </Series.Sequence>
        {CLIPS.map((clip, i) => {
          title = clip.title ?? title;
          return (
            <Series.Sequence key={i} durationInFrames={clip.frames}>
              <Shot clip={clip} title={title} />
            </Series.Sequence>
          );
        })}
        <Series.Sequence durationInFrames={OUTRO_FRAMES}>
          <Outro />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
}
