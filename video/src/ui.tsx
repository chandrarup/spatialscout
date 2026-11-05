import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export const C = {
  bg: "#07090f",
  ink: "#f4f1ea",
  dim: "#9aa3b2",
  rna: "#4ade80",
  lrp2: "#f472b6",
  nuc: "#6d7cff",
  warn: "#fbbf24",
  ok: "#34d399",
  bad: "#f87171",
};

export const FONT = "'Inter', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif";
export const SERIF = "'Iowan Old Style', 'Georgia', serif";

export function fade(frame: number, start: number, end: number, len = 12) {
  return interpolate(frame, [start, start + len, end - len, end], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}

export function Rise({ at, children, style }: { at: number; children: ReactNode; style?: CSSProperties }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - at, fps, config: { damping: 200 } });
  return (
    <div style={{ opacity: s, transform: `translateY(${(1 - s) * 28}px)`, ...style }}>{children}</div>
  );
}

export function Tissue({ src, from = 1.08, to = 1.22, x = 0, opacity = 0.55 }: { src: string; from?: number; to?: number; x?: number; opacity?: number }) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [from, to], { easing: Easing.inOut(Easing.quad) });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
      <Img
        src={staticFile(src)}
        style={{ height: "140%", transform: `translateX(${x}px) scale(${scale}) rotate(90deg)`, opacity, filter: "saturate(1.15)" }}
      />
    </AbsoluteFill>
  );
}

export function Vignette() {
  return (
    <AbsoluteFill
      style={{ background: `radial-gradient(ellipse at center, rgba(7,9,15,0.25) 0%, rgba(7,9,15,0.85) 62%, ${C.bg} 100%)` }}
    />
  );
}

export function Kicker({ children, color = C.dim }: { children: ReactNode; color?: string }) {
  return (
    <div style={{ fontFamily: FONT, fontSize: 26, letterSpacing: 6, textTransform: "uppercase", color, fontWeight: 600 }}>
      {children}
    </div>
  );
}

export function Headline({ children, size = 92 }: { children: ReactNode; size?: number }) {
  return (
    <div style={{ fontFamily: SERIF, fontSize: size, lineHeight: 1.08, color: C.ink, fontWeight: 500, letterSpacing: -1 }}>
      {children}
    </div>
  );
}

export function Counter({ to, at, dur = 40, decimals = 0, suffix = "" }: { to: number; at: number; dur?: number; decimals?: number; suffix?: string }) {
  const frame = useCurrentFrame();
  const v = interpolate(frame, [at, at + dur], [0, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (
    <span style={{ fontVariantNumeric: "tabular-nums" }}>
      {v.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}
