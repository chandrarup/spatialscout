import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT, Headline, Kicker, Rise, Tissue, Vignette, fade } from "./ui";

export const OUTRO_FRAMES = 30 * 16;

function Stamp({ at, label, color }: { at: number; label: string; color: string }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - at, fps, config: { damping: 12, stiffness: 180 } });
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: 40,
        fontWeight: 800,
        letterSpacing: 4,
        color,
        border: `5px solid ${color}`,
        borderRadius: 14,
        padding: "8px 26px",
        transform: `scale(${interpolate(s, [0, 1], [2.2, 1])}) rotate(-4deg)`,
        opacity: s,
        display: "inline-block",
      }}
    >
      {label}
    </div>
  );
}

function Verdicts() {
  const frame = useCurrentFrame();
  const row = (at: number, claim: string, detail: string, label: string, color: string) => (
    <Rise at={at} style={{ display: "flex", alignItems: "center", gap: 48, marginTop: 40 }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: FONT, fontSize: 46, color: C.ink, fontWeight: 600 }}>{claim}</div>
        <div style={{ fontFamily: FONT, fontSize: 28, color: C.dim, marginTop: 8 }}>{detail}</div>
      </div>
      <Stamp at={at + 18} label={label} color={color} />
    </Rise>
  );
  return (
    <AbsoluteFill style={{ background: C.bg, opacity: fade(frame, 0, 165, 12), padding: "0 170px", justifyContent: "center" }}>
      <Rise at={0}>
        <Kicker>The verdict · one recorded run</Kicker>
      </Rise>
      {row(10, "Podocytes really carry LRP2", "23.8% over the nucleus vs 24.4% expected from random loss · 7,926 cells", "CONFIRMED", C.ok)}
      {row(40, "B-cell UMOD is just spillover", "17.0% → 12.3% over the nucleus · above the 9.5% baseline, below the 13.7% one · a lead, not proof", "REFUTED", C.bad)}
      <Rise at={90} style={{ marginTop: 64 }}>
        <div style={{ fontFamily: FONT, fontSize: 32, color: C.dim }}>
          18 Meta model calls · $0.29 · about 3 minutes · every cited number recomputed
        </div>
      </Rise>
    </AbsoluteFill>
  );
}

function Close() {
  const frame = useCurrentFrame();
  const wink = interpolate(frame, [150, 165], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: fade(frame, 0, 9999, 14) }}>
      <Tissue src="31-10013.png" opacity={0.3} from={1.25} to={1.12} />
      <Vignette />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center" }}>
        <Rise at={0}>
          <Headline size={76}>It doesn't drink coffee.</Headline>
        </Rise>
        <Rise at={30} style={{ marginTop: 10 }}>
          <Headline size={76}>It doesn't sleep.</Headline>
        </Rise>
        <Rise at={60} style={{ marginTop: 10 }}>
          <Headline size={76}>
            It just <span style={{ color: C.warn, fontStyle: "italic" }}>really</span> wants to check your numbers.
          </Headline>
        </Rise>
        <Rise at={110} style={{ marginTop: 70 }}>
          <div style={{ fontFamily: FONT, fontSize: 120, fontWeight: 800, letterSpacing: -4, color: C.ink }}>
            Happy scouting<span style={{ color: C.rna, opacity: wink }}>.</span>
          </div>
        </Rise>
        <Rise at={135} style={{ marginTop: 24 }}>
          <div style={{ fontFamily: FONT, fontSize: 30, color: C.dim }}>
            SpatialScout · chandrarupdaka--spatialscout.us-east.modal.run
          </div>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  );
}

export function Outro() {
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sequence durationInFrames={165}>
        <Verdicts />
      </Sequence>
      <Sequence from={165}>
        <Close />
      </Sequence>
    </AbsoluteFill>
  );
}
