import { Composition } from "remotion";
import { Intro, INTRO_FRAMES } from "./Intro";
import { Outro, OUTRO_FRAMES } from "./Outro";

export const FPS = 30;

export const Root = () => (
  <>
    <Composition id="Intro" component={Intro} durationInFrames={INTRO_FRAMES} fps={FPS} width={1920} height={1080} />
    <Composition id="Outro" component={Outro} durationInFrames={OUTRO_FRAMES} fps={FPS} width={1920} height={1080} />
  </>
);
