# Researcher feedback session: facilitator guide

For ticket 13 ([#15](https://github.com/chandrarup/spatialscout/issues/15)). One researcher, about 20 minutes, on the public SpatialScout URL. You run it; the participant gets the [task sheet](task-sheet.md) and the [rating form](rating-form.md). Record what happened in a copy of the [results template](results-template.md).

This is informal product feedback, not a research study. Report it as one person's observed session, never as a validation study. If you want to publish it beyond the hackathon, check with your institution's IRB first.

## Before the session

- [ ] Tickets #5 (public deployment) and #13 (review and export) have landed, so the URL works end to end.
- [ ] You have the live-mode passcode, and the daily budget has room for one investigation.
- [ ] The recorded hero investigation plays as a fallback, in case live mode fails.
- [ ] You have printed or shared the task sheet and the rating form, with the URL filled in on the task sheet.
- [ ] A clock is visible to you, not to the participant.
- [ ] You only show public GSE286184 data: no unpublished lab data, no patient data.

## Running it (20 minutes)

| Minutes | Step | What you do |
| --- | --- | --- |
| 0–2 | Consent | Read the consent section of the rating form aloud and get their choices before anything else. If they decline recording, take notes only. |
| 2–3 | Background | They fill in "About you" on the rating form. |
| 3–15 | Task | Give the task sheet. Note the start time. Stay quiet; if they ask for help, help, then log it as an intervention with one line on what they needed. Note the time they finish, by the completion definition on the task sheet. |
| 15–19 | Ratings | They rate the claims they saw (up to 8) and answer the three task questions on the form. |
| 19–20 | Wrap-up | One improvement they would ask for, and whether they would use it. Thank them. |

Keep two kinds of time apart: what you **observed** (start to finish of the task) and what they **estimate** their current workflow would take. Never combine them into a single "time saved" number.

## What to record

- Run mode used (live run or immutable replay) and the investigation id shown in the banner.
- Observed task time, whether they completed it by the definition, and every intervention.
- Their claim ratings, counted by category: supported, plausible, unsupported, unassessable. Report each category; do not merge them into "correct".
- Their estimate of usual workflow time, labelled as an estimate.
- The one improvement, and what you built or triaged in response (ticket 13's last step).
- Errors or confusing moments, with the screen they were on.

## Afterwards

- Store the signed or recorded consent privately, outside the repo.
- Fill in `results-<date>.md` from the template. Use their name or title only if they chose attribution on the form; otherwise describe them by role.
- Commit the results file only if every quote and detail in it matches their consent choices.
- The README may report these results only from that file (ticket 12's condition). If the session does not happen, the README and whitepaper make no lab-validation claims at all.
