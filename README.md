# Rift Coach

Personal champ-select coach for League of Legends. Watches the League Client during
champ select, asks Claude for the best pick **from your own champion pool**, then
recommends runes, summoner spells and build, explains *why*, and imports the rune
page into the client.

The model only reasons. Champion, rune and item names come from Riot's Data Dragon
for the current patch, and every pick is validated against your pool.

## Quick start (Windows, PowerShell)

```powershell
cd rift-coach
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

copy config.example.toml config.toml  # set role + champion_pool
copy .env.example .env                # set ANTHROPIC_API_KEY

python -m rift_coach check            # one test question to Claude
python -m rift_coach                  # start with the League Client open
```

### Claude backends

- `backend = "api"` (default): Claude API with `ANTHROPIC_API_KEY` in `.env`. Two calls per
  game cost a fraction of a cent each.
- `backend = "subscription"`: Claude Agent SDK signed in with your own Claude plan
  (`python -m rift_coach login` once). **Personal, local use only.** Anthropic does not
  allow apps that are shared or distributed to offer claude.ai login, so use the API
  backend for anything beyond your own machine.

Both backends return the same structured output, so the rest of the app does not care
which one is active.

## Project management

Milestones and issues are defined as data in `scripts/github_plan.json` and created with
`python scripts/bootstrap_github.py` (needs [GitHub CLI](https://cli.github.com)). The
script is idempotent; `--dry-run` previews the changes.

## How it works

```
League Client ──websocket──▶ champ select session
        │                         │ parse_session()  (champions + positions only)
        │                         ▼
        │                    DraftState ──▶ Recommender ──▶ Claude API (forced tool call)
        │                                       ▲               │
        │                 Data Dragon (patch) ──┘               ▼
        │                                         pick / loadout (validated)
        └──◀── POST /lol-perks/v1/pages ◀── build_rune_page()
```

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.

## Project layout

```
src/rift_coach/
  __main__.py     entry point, lcu-driver wiring
  coach.py        event handling: when to ask, what to import, console output
  champselect.py  LCU session -> DraftState
  recommender.py  Claude prompts, schemas, pool validation
  llm.py          backends: subscription (Agent SDK) or API key
  runes.py        rune names -> LCU perk page payload
  ddragon.py      Data Dragon download + cache
  config.py       config.toml + .env
  lcu/actions.py  client write actions (runes, spells)
scripts/          GitHub bootstrap (labels, milestones, issues)
tests/            pytest, offline fixtures
```

## Riot policy (personal use)

- Pre-game only: nothing runs or displays during the match.
- No summoner names of other players are read into the draft state or shown.
- Rune and item-set import through the LCU API is the same thing RuneChanger / u.gg / iTero do.
- Sharing the app with others requires registering it at developer.riotgames.com first.

## Cost

Two Claude calls per game (pick + loadout): a fraction of a cent each on the API backend.

## Legal

Rift Coach isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot
Games or anyone officially involved in producing or managing Riot Games properties. Riot
Games, and all associated properties are trademarks or registered trademarks of Riot
Games, Inc.
