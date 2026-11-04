# SpatialScout tickets

Published Nov 2 2026 as sub-issues of the spec issue [#1](https://github.com/chandrarup/spatialscout/issues/1), with native "blocked by" edges. **The issues are canonical**; read one with `gh issue view <n>`. The validated draft text (revision 2) is in git history.

| Ticket | Issue | Blocked by | Label |
| --- | --- | --- | --- |
| 01: Walking skeleton on replay, with persisted investigations | [#2](https://github.com/chandrarup/spatialscout/issues/2) | None | ready-for-agent |
| 02: Real dataset store, label rules and capability report | [#3](https://github.com/chandrarup/spatialscout/issues/3) | #2 | ready-for-agent |
| 02b: Dual-biopsy viewer with rendered channels and region selection (revision 3) | [#18](https://github.com/chandrarup/spatialscout/issues/18) | #3 | ready-for-agent |
| 02c: KPMP CODEX real-image dataset and protein-level audit (revision 3) | [#19](https://github.com/chandrarup/spatialscout/issues/19) | #18 | ready-for-agent |
| 03: Model gateway with cache, run modes, budget and telemetry | [#4](https://github.com/chandrarup/spatialscout/issues/4) | #2 | ready-for-agent |
| 04: Public deployment on Modal | [#5](https://github.com/chandrarup/spatialscout/issues/5) | #2 | ready-for-agent |
| 05: Assignment audit with thinning controls and evidence regions | [#6](https://github.com/chandrarup/spatialscout/issues/6) | #3 | ready-for-agent |
| 06: Descriptive disease contrasts | [#7](https://github.com/chandrarup/spatialscout/issues/7) | #6 | ready-for-agent |
| 07: SAM 3.1 outlines as an exploratory condition | [#8](https://github.com/chandrarup/spatialscout/issues/8) | #4, #6 | ready-for-agent |
| 08: Voice question with editable transcript | [#9](https://github.com/chandrarup/spatialscout/issues/9) | #4 | ready-for-agent |
| 09a: Agent loop on audit results, with agent-chosen controls | [#10](https://github.com/chandrarup/spatialscout/issues/10) | #4, #6 | ready-for-agent |
| 09b: Disease contrasts in the agent loop | [#11](https://github.com/chandrarup/spatialscout/issues/11) | #7, #10 | ready-for-agent |
| 10: Verification, injected errors, benchmark and "Challenge the verifier" | [#12](https://github.com/chandrarup/spatialscout/issues/12) | #10 | ready-for-agent |
| 10b: Hypothesis verdict banner (revision 3) | [#20](https://github.com/chandrarup/spatialscout/issues/20) | #12 | ready-for-agent |
| 11: Review decisions and evidence package | [#13](https://github.com/chandrarup/spatialscout/issues/13) | #12 | ready-for-agent |
| 12: Golden path recording, README and demo script | [#14](https://github.com/chandrarup/spatialscout/issues/14) | #5, #13 | ready-for-agent |
| 13: Researcher feedback session | [#15](https://github.com/chandrarup/spatialscout/issues/15) | #5, #13 (task sheet can start now) | ready-for-human |
| 14: Stretch: Muse Glimmer LoRA annotator, agreement study | [#16](https://github.com/chandrarup/spatialscout/issues/16) | #14 | ready-for-agent |

Critical path: #2 → #3 → #6 → #10 → #12 → #13 → #14. After #2, tickets #3, #4 and #5 run in parallel.
