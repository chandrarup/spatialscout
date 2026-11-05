import { AbsoluteFill, Easing, Sequence, interpolate, useCurrentFrame } from "remotion";
import { C, Counter, FONT, Headline, Kicker, Rise, Tissue, Vignette, fade } from "./ui";

export const INTRO_FRAMES = 30 * 22;

function Hook() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity: fade(frame, 0, 120, 15) }}>
      <Tissue src="31-10013.png" opacity={0.7} />
      <Vignette />
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 180px" }}>
        <Rise at={8}>
          <Kicker>A kidney biopsy · KPMP participant 31-10013</Kicker>
        </Rise>
        <Rise at={22} style={{ marginTop: 24 }}>
          <Headline size={104}>Every kidney biopsy<br />is a crime scene.</Headline>
        </Rise>
        <Rise at={60} style={{ marginTop: 28 }}>
          <div style={{ fontFamily: FONT, fontSize: 38, color: C.dim }}>
            Millions of molecules. Thousands of cells. One question: <span style={{ color: C.ink }}>who did it?</span>
          </div>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

function Scale() {
  const frame = useCurrentFrame();
  const stat = (n: React.ReactNode, label: string, at: number, color: string) => (
    <Rise at={at} style={{ flex: 1 }}>
      <div style={{ fontFamily: FONT, fontSize: 112, fontWeight: 700, color, letterSpacing: -2 }}>{n}</div>
      <div style={{ fontFamily: FONT, fontSize: 30, color: C.dim, marginTop: 6 }}>{label}</div>
    </Rise>
  );
  return (
    <AbsoluteFill style={{ background: C.bg, opacity: fade(frame, 0, 120, 12), padding: "0 160px", justifyContent: "center" }}>
      <Rise at={0}>
        <Kicker>GSE286184 · Xenium · 5 kidney conditions</Kicker>
      </Rise>
      <div style={{ display: "flex", gap: 60, marginTop: 48 }}>
        {stat(<Counter to={21.8} decimals={1} at={8} suffix="M" />, "RNA molecules, each placed in space", 8, C.rna)}
        {stat(<Counter to={753099} at={18} />, "cells, each with a boundary someone drew", 18, C.ink)}
        {stat(<Counter to={21} at={28} dur={25} />, "tissue sections, 19 donors", 28, C.nuc)}
      </div>
      <Rise at={56} style={{ marginTop: 56 }}>
        <div style={{ fontFamily: FONT, fontSize: 29, color: C.dim, whiteSpace: "nowrap" }}>
          Healthy · Diabetic kidney disease · IgA nephropathy · Minimal change disease · Membranous nephropathy
        </div>
      </Rise>
    </AbsoluteFill>
  );
}

const MOLECULES = Array.from({ length: 26 }, (_, i) => {
  const a = (i * 137.5 * Math.PI) / 180;
  const r = 40 + ((i * 53) % 120);
  return { x: Math.cos(a) * r, y: Math.sin(a) * r, leaks: i % 3 === 0 };
});

function Spillover() {
  const frame = useCurrentFrame();
  const drift = interpolate(frame, [20, 90], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const cellA = { x: 760, y: 560 };
  const cellB = { x: 1160, y: 560 };
  return (
    <AbsoluteFill style={{ background: C.bg, opacity: fade(frame, 0, 150, 12) }}>
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 110 }}>
        <Rise at={0}>
          <Kicker color={C.warn}>The catch</Kicker>
        </Rise>
        <Rise at={10} style={{ marginTop: 18, textAlign: "center" }}>
          <Headline size={72}>Draw a boundary a little too wide…</Headline>
        </Rise>
      </AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <circle cx={cellA.x} cy={cellA.y} r={190} fill="rgba(74,222,128,0.08)" stroke={C.rna} strokeWidth={3} />
        <circle cx={cellB.x} cy={cellB.y} r={150 + drift * 40} fill="rgba(109,124,255,0.08)" stroke={C.nuc} strokeWidth={3} strokeDasharray={drift > 0.1 ? "14 10" : undefined} />
        <circle cx={cellB.x} cy={cellB.y} r={60} fill="rgba(109,124,255,0.35)" />
        {MOLECULES.map((m, i) => {
          const x = cellA.x + m.x + (m.leaks ? drift * (cellB.x - cellA.x - m.x - 70 + (i % 5) * 18) : 0);
          const y = cellA.y + m.y * (m.leaks ? 1 - drift * 0.6 : 1);
          return <circle key={i} cx={x} cy={y} r={9} fill={m.leaks && drift > 0.5 ? C.warn : C.rna} />;
        })}
        <text x={cellA.x} y={cellA.y + 250} textAnchor="middle" fill={C.dim} fontFamily={FONT} fontSize={30}>tubule cell · makes UMOD</text>
        <text x={cellB.x} y={cellB.y + 250} textAnchor="middle" fill={C.dim} fontFamily={FONT} fontSize={30}>immune B cell</text>
      </svg>
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 110 }}>
        <Rise at={95}>
          <div style={{ fontFamily: FONT, fontSize: 44, color: C.ink, fontWeight: 600 }}>
            …and an immune cell suddenly "expresses" a kidney gene.
          </div>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

function Reveal() {
  const frame = useCurrentFrame();
  const glow = interpolate(frame, [0, 60], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: fade(frame, 0, 999, 14) }}>
      <Tissue src="164-17.png" opacity={0.35} from={1.2} to={1.3} />
      <Vignette />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center" }}>
        <Rise at={4}>
          <Kicker color={C.rna}>Meet your new lab partner</Kicker>
        </Rise>
        <Rise at={14} style={{ marginTop: 20 }}>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 168,
              fontWeight: 800,
              letterSpacing: -5,
              color: C.ink,
              textShadow: `0 0 ${60 * glow}px rgba(74,222,128,0.45)`,
            }}
          >
            SpatialScout
          </div>
        </Rise>
        <Rise at={34} style={{ marginTop: 14 }}>
          <div style={{ fontFamily: FONT, fontSize: 44, color: C.ink }}>An agentic lab for spatial omics</div>
        </Rise>
        <Rise at={52} style={{ marginTop: 26 }}>
          <div style={{ fontFamily: FONT, fontSize: 30, color: C.dim }}>
            Plans · Counts · Doubts itself · Verifies every number &nbsp;—&nbsp; built on Meta models
          </div>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function Intro() {
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sequence durationInFrames={120}>
        <Hook />
      </Sequence>
      <Sequence from={120} durationInFrames={120}>
        <Scale />
      </Sequence>
      <Sequence from={240} durationInFrames={150}>
        <Spillover />
      </Sequence>
      <Sequence from={390}>
        <Reveal />
      </Sequence>
    </AbsoluteFill>
  );
}
