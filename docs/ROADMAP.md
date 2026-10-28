# Roadmap

Issues and milestones live on GitHub (created by `scripts/bootstrap_github.py` from
`scripts/github_plan.json`). This file is the short version.

| Milestone | Goal | Done when |
|---|---|---|
| **M0 Setup** | Repo, CI, keys, client connection | `python -m rift_coach` connects; CI green |
| **M1 MVP Console Coach** | Pick + loadout from Claude in console | Real champ select gives a pool-only pick and a sensible loadout in < 10 s |
| **M2 Auto Import** | Runes, spells, item set in the client | Lock in → page `RiftCoach` selected, spells and item set set |
| **M3 Personal Data** | My stats in the prompt | Pick reasoning cites my own results on the champion / matchup |
| **M4 Coach Loop** | Post-game review, weekly focus | After each game: 3 mistakes, 1 good thing, focus graded |
| **M5 Desktop UI** | Small window instead of console | Recommendation visible next to the client without alt-tabbing |

## Principles

1. **Teach, don't prescribe.** Every recommendation carries a short "why".
2. **Pool first.** Comfort beats theoretical win rate. Never suggest outside the pool.
3. **Facts from data, reasoning from the model.** Names and IDs come from Data Dragon / LCU.
4. **Pre-game and post-game only.** Nothing during the match.
