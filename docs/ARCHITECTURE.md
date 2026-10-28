# Architecture

## Flow

1. **lcu-driver** finds the running League Client (lockfile), opens the local websocket.
2. Every `/lol-champ-select/v1/session` event goes to `Coach.on_session`.
3. `parse_session` reduces it to `DraftState`: positions, champions, bans, whether it is
   my turn, whether I locked. No player names.
4. `Coach` acts on two transitions only:
   - **my turn to pick** (and draft changed) → `Recommender.recommend_pick`
   - **I locked champion X** (once per champion) → `Recommender.recommend_loadout`
5. `Recommender` sends a JSON prompt and forces a tool call (`submit_pick` /
   `submit_loadout`) so the answer is always structured.
6. `validate_pick` drops anything outside the pool or unavailable.
7. `build_rune_page` maps rune names to perk IDs via Data Dragon, validating tree/row
   rules, then `lcu.actions.import_rune_page` replaces the `RiftCoach` page.

## Key LCU endpoints

| Purpose | Method | Endpoint |
|---|---|---|
| Champ select state | WS / GET | `/lol-champ-select/v1/session` |
| Summoner spells | PATCH | `/lol-champ-select/v1/session/my-selection` |
| Rune pages | GET / POST / DELETE | `/lol-perks/v1/pages`, `/lol-perks/v1/pages/{id}` |
| Rune page slots | GET | `/lol-perks/v1/inventory` |
| Item sets (M2) | PUT | `/lol-item-sets/v1/item-sets/{summonerId}/sets` |
| Me | GET | `/lol-summoner/v1/current-summoner` |

Community docs: HexDocs (lcu explorer), `awesome-league` on GitHub.

## Data sources

- **Data Dragon** (`ddragon.leagueoflegends.com`): champions, runes, items, spells per
  patch. Cached under `.cache/ddragon/<version>/`.
- **Riot API** (M3): account-v1, match-v5. Needs `RIOT_API_KEY`.
- **Claude API**: reasoning only. Model configurable in `config.toml`.

## Testing

All tests run offline against fixtures in `tests/fixtures`. Recorded sessions (M1 issue)
must have names and IDs stripped before committing.
