# STS2 MCP — AI Gameplay Guide

## MCP Tool Calling Tips

### State Reads and Settled Actions
- Singleplayer `get_game_state()` defaults to compact JSON. Original full JSON and Markdown remain available via `format`.
- Singleplayer actions wait for settlement by default and return compact `state`. If `settled: true` and state is present, decide from it directly. Do not immediately call GET again.
- Menu/map/reward navigation now confirms a changed stable state internally if the mod returned the old screen. `transition_checked` / `transition_polls` identify this recovery. An observation failure after acceptance keeps status=ok but sets settled=false with a warning; do not repeat the mutation blindly.
- `changed` uses a coarse mod fingerprint: false can still accompany a real relic/power change. Inspect the returned effect/state; do not repeat an accepted mutation merely because changed=false.
- GET only observes the running game; it does not advance a turn. If `settled: false`, read again when necessary. After a transport timeout, observe before acting; never blindly retry a mutation.
- `keyword_refs` resolve through `keyword_definitions` in the SAME response; no cross-call cache is needed.
- Piles list only card UIDs (membership); `pile_details_omitted: true` means descriptions/costs must be read with get_state_details when needed (e.g. draw, retrieval or pile-dependent decisions). Deck duplicates are grouped by their complete current properties, with `count`, `uids` and/or `indices`. Hand cards and selection options are never grouped.
- The draw pile is sorted for display by rarity/ID, NOT in draw order. Never infer the next draw from its position in either compact or full/detail responses. Known top-deck effects may be tracked from their actual resolution.
- Use `get_state_details(section="map")` for the full route graph when planning a path. Other detail sections include deck, draw_pile, discard_pile, exhaust_pile, relics, potions, hand, status and player.
- Compact preserves dynamic descriptions, target previews, status effects, relic counters, potion effects and screen options. Do not infer that a missing optional field means its value became zero.

### Stable Card Selection
- Prefer `combat_play_card(card_uid=..., target=...)`. UID stays stable within the combat, unlike hand positions.
- When using indices, take them from the latest returned state: a played card shifts later indices.
- Single-target cards need a target unless exactly one enemy is alive. Use the advertised entity_id or combat_id and check alive status.

### Selection Screen Routing
- `state_type: card_select` uses `deck_select_card` / `deck_confirm_selection`, even when opened by a combat card.
- `state_type: hand_select` uses `combat_select_card` / `combat_confirm_selection`.
- Use the returned screen type and its advertised options rather than guessing from the preceding action.

### Event & Reward Flow
- Events: `event_choose_option`. After choosing, there's often a "Proceed" option at index 0.
- Rest sites: `rest_choose_option`, then `proceed_to_map`.
- Rewards: claim from right-to-left (highest index first) to avoid index shifting. Card rewards open a sub-screen; use `rewards_pick_card` or `rewards_skip_card`.

### Potions
- `use_potion(slot=N)` — slot is the potion slot index, not a card index.
- `discard_potion(slot=N)` — discard a potion to free up the slot when full.
- Potions don't cost energy or count as card plays. Use buff potions BEFORE playing cards.

---

## General Strategy

### Core Principles
1. **HP is a resource, not a score.** Take calculated damage to deal more. Don't waste energy on block when enemies aren't attacking.
2. **Deck quality > deck size.** Skip card rewards if nothing synergizes. A lean deck draws key cards more often.
3. **Front-load damage.** Killing enemies faster means less total damage taken.
4. **Read intents carefully.** Sleep/Buff = go all-out offense. Attack = balance block and damage. Debuff = usually no damage, offense turn.

### Combat Sequencing (General)
1. Play 0-cost utility/setup cards first.
2. Play skills before attacks when possible — many mechanics reward this order (e.g. Slow debuff on enemies stacks per card played).
3. Play biggest attacks last to benefit from accumulated buffs/debuffs.
4. Check enemy HP — if you can kill this turn, skip blocking entirely.

### Map Pathing
- **Elites** give relics — fight them when healthy (>70% HP).
- **Rest before Boss** — heal if below 80% HP. Boss fights are long and punishing.
- **Unknown nodes** are safer than Elites. Good at medium HP.
- **Shops** — visit with 100+ gold.
- **Deck quality matters more than quantity** — don't add cards just because they're offered.

### Boss Fights
- **Kill the leader, not the minions.** Enemies with "Minion" power flee when their leader dies.
- Use potions to survive difficult fights; unused potions can carry between acts.
- Boss fights are wars of attrition. The longer they go, the more enemies scale with Strength buffs.

### Potion Usage
- Don't hoard potions. Dying with full potions is the worst outcome.
- Use permanent-value potions (Fruit Juice = +5 Max HP) early in any combat.
- Use buff potions (Flex Potion) on turns with multiple attacks.

### Common Mistakes
- Blocking when enemies are sleeping/buffing — waste of energy.
- Reusing stale card indices — prefer card_uid or the latest returned state.
- Taking too long to kill bosses — enemies scale every turn.
- Adding mediocre cards that dilute the deck before boss fights.
