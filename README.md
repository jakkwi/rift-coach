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

copy .env.example .env                # add ANTHROPIC_API_KEY
copy config.example.toml config.toml  # set role + champion_pool

pytest                                # sanity check
python -m rift_coach                  # start with the League Client open
```

## Put it on GitHub (private) with milestones and issues

Requires [GitHub CLI](https://cli.github.com) and `gh auth login` once.

```powershell
git init -b main
git add .
git commit -m "Initial skeleton"
gh repo create rift-coach --private --source=. --push
python scripts/bootstrap_github.py    # labels, 6 milestones, ~19 issues
```

The bootstrap script is idempotent; use `--dry-run` to preview.

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
  recommender.py  Claude prompts, tool schemas, pool validation
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

Two Claude calls per game (pick + loadout). Token usage logging is tracked in an issue.
