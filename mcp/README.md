# MCP Tools

## Singleplayer

| Tool | Scope | Description |
|---|---|---|
| `get_game_state(format?)` | General | Get current game state (`markdown` or `json`) |
| `menu_select(option, seed?)` | General | Select a visible menu/game-over option |
| `open_pause_menu()` | General | Open the in-run pause menu (resume / settings / compendium / give_up / save_and_quit) |
| `get_profile()` | Profiles | Get active profile progress |
| `get_compendium()` | Profiles | Get active profile progress grouped like the in-game Compendium |
| `search_wiki(query, item_type?, limit?)` | Profiles | Fuzzy-search discovered card and relic wiki entries |
| `list_profiles()` | Profiles | List profile slots and active slot |
| `switch_profile(profile_id)` | Profiles | Switch to a profile slot through the game UI |
| `delete_profile(profile_id)` | Profiles | Delete an inactive profile slot |
| `use_potion(slot, target?, wait?)` | General | Use a potion (works in and out of combat) |
| `discard_potion(slot)` | General | Discard a potion to free up the slot |
| `proceed_to_map(wait?)` | General | Proceed from rewards/rest site/shop/treasure to the map |
| `combat_play_card(card_index, target?, card_uid?, wait?)` | Combat | Play a card from hand |
| `combat_end_turn(wait?)` | Combat | End the current turn |
| `combat_select_card(card_index)` | Combat Selection | Select a card from hand during exhaust/discard prompts |
| `combat_confirm_selection()` | Combat Selection | Confirm the in-combat card selection |
| `rewards_claim(reward_index)` | Rewards | Claim a reward from the post-combat screen |
| `rewards_pick_card(card_index)` | Rewards | Select a card from the card reward screen |
| `rewards_skip_card()` | Rewards | Skip the card reward |
| `map_choose_node(node_index)` | Map | Choose a map node to travel to |
| `rest_choose_option(option_index, option_id)` | Rest Site | Choose a rest site option (rest, smith, dig, …). Prefer `option_id` from `rest_site.options[].id` |
| `shop_purchase(item_index)` | Shop | Purchase an item from the shop |
| `event_choose_option(option_index)` | Event | Choose an event option (including Proceed) |
| `event_advance_dialogue()` | Event | Advance ancient event dialogue |
| `deck_select_card(card_index)` | Card Select | Pick/toggle a card in the selection screen |
| `deck_confirm_selection()` | Card Select | Confirm the current card selection |
| `deck_cancel_selection()` | Card Select | Cancel/skip card selection |
| `bundle_select(bundle_index)` | Bundle Select | Open a bundle preview |
| `bundle_confirm_selection()` | Bundle Select | Confirm the current bundle preview |
| `bundle_cancel_selection()` | Bundle Select | Cancel the current bundle preview |
| `relic_select(relic_index)` | Relic Select | Choose a relic from the selection screen |
| `relic_skip()` | Relic Select | Skip relic selection |
| `treasure_claim_relic(relic_index)` | Treasure | Claim a relic from the treasure chest |
| `crystal_sphere_set_tool(tool)` | Crystal Sphere | Switch the active divination tool |
| `crystal_sphere_click_cell(x, y)` | Crystal Sphere | Click a hidden cell in the grid |
| `crystal_sphere_proceed()` | Crystal Sphere | Continue after the minigame finishes |

### Waiting for the Game to Settle (`wait?`)

`combat_play_card`, `combat_end_turn`, `use_potion` and `proceed_to_map` default to `wait=True`. The mod
then holds the HTTP response until the game has settled — animations, card resolution and the redraw
finished — and returns the settled state with it, replacing the usual "act, then poll
`get_game_state` until `is_resolving` is false" loop with a single call.

The reply gains `settled`, `changed`, `waited_ms`, `polls` and `state` (the same payload
`get_game_state(format="compact")` now returns through the bridge (raw HTTP remains full JSON)). `changed: false` means the mod's coarse fingerprint did not detect a change
(relic/power changes can be missed, so inspect the returned state); `settled: false` means the wait timed out and the state may still be mid-resolution.

These hot paths expose `wait` as a tool parameter. Other singleplayer action tools
also wait internally by default. Raw HTTP accepts `"wait": true`, `wait_timeout_ms`
and `include_state`. Multiplayer behavior is unchanged.

### Profile Tools

`get_profile()` returns the raw active-profile progress summary: character totals, global totals, discoveries, achievements, epochs, and aggregate stats.

`get_compendium()` presents the same profile data in the shape agents usually need when reasoning about long-term progress. It groups the response into `card_library`, `relic_collection`, `potion_lab`, `bestiary`, `character_stats`, and `run_history`, matching the high-level Compendium cards in the game UI. It also includes `current_run` while a run is active, with a derived `run_id` in `{save_scope}:profile{profile_id}:{start_time}` format.

The Compendium response is profile-scoped, not run-state-scoped. It works from the main menu, does not require navigating the in-game Compendium UI, and summarizes only the 20 most recent saved run-history files to keep the MCP response bounded.

`search_wiki(query, item_type="all", limit=10)` is the selective wiki lookup. It fuzzy-matches names and IDs such as `ironclad perfect strike` or `silver spoon`, but it searches only cards and relics discovered by the active profile. The default response is capped at 10 entries; callers may pass a higher or lower `limit`, and the mod clamps oversized requests. Card matches include `base` and `upgraded` blocks so agents can compare pre-upgrade and post-upgrade text without asking for the full card library.

## Multiplayer

All multiplayer tools are prefixed with `mp_`. They route through `/api/v1/multiplayer` and are only available during multiplayer (co-op) runs. The endpoints automatically guard against cross-mode calls.

| Tool | Scope | Description |
|---|---|---|
| `mp_get_game_state(format?)` | General | Get multiplayer game state (all players, votes, bids) |
| `mp_combat_play_card(card_index, target?)` | Combat | Play a card from the local player's hand |
| `mp_combat_end_turn()` | Combat | Submit end-turn vote (turn ends when all players submit) |
| `mp_combat_undo_end_turn()` | Combat | Retract end-turn vote |
| `mp_use_potion(slot, target?)` | General | Use a potion from the local player's slots |
| `mp_discard_potion(slot)` | General | Discard a potion from the local player's slots |
| `mp_proceed_to_map()` | General | Proceed from current screen to the map |
| `mp_map_vote(node_index)` | Map | Vote for a map node (travel when all agree) |
| `mp_event_choose_option(option_index)` | Event | Vote for / choose an event option |
| `mp_event_advance_dialogue()` | Event | Advance ancient event dialogue |
| `mp_rest_choose_option(option_index)` | Rest Site | Choose a rest site option (per-player, no vote) |
| `mp_shop_purchase(item_index)` | Shop | Purchase an item (per-player inventory) |
| `mp_rewards_claim(reward_index)` | Rewards | Claim a post-combat reward |
| `mp_rewards_pick_card(card_index)` | Rewards | Select a card from the card reward screen |
| `mp_rewards_skip_card()` | Rewards | Skip the card reward |
| `mp_deck_select_card(card_index)` | Card Select | Pick/toggle a card in the selection screen |
| `mp_deck_confirm_selection()` | Card Select | Confirm the current card selection |
| `mp_deck_cancel_selection()` | Card Select | Cancel/skip card selection |
| `mp_bundle_select(bundle_index)` | Bundle Select | Open a bundle preview |
| `mp_bundle_confirm_selection()` | Bundle Select | Confirm the current bundle preview |
| `mp_bundle_cancel_selection()` | Bundle Select | Cancel the current bundle preview |
| `mp_combat_select_card(card_index)` | Combat Selection | Select a card during in-combat selection prompts |
| `mp_combat_confirm_selection()` | Combat Selection | Confirm in-combat card selection |
| `mp_relic_select(relic_index)` | Relic Select | Choose a relic from the selection screen |
| `mp_relic_skip()` | Relic Select | Skip relic selection |
| `mp_treasure_claim_relic(relic_index)` | Treasure | Bid on a relic (relic fight if contested) |
| `mp_crystal_sphere_set_tool(tool)` | Crystal Sphere | Switch the active divination tool |
| `mp_crystal_sphere_click_cell(x, y)` | Crystal Sphere | Click a hidden cell in the grid |
| `mp_crystal_sphere_proceed()` | Crystal Sphere | Continue after the minigame finishes |


### Compact singleplayer responses

`get_game_state()` now defaults to `format="compact"`. Explicit `format="json"`
and `format="markdown"` retain the original HTTP representations. Singleplayer
actions default to waiting and return the same compact representation in `state`.
Use this returned state directly when `settled` is true. `wait=False` remains
available on the hot-path tools. Other singleplayer actions also wait internally.
Multiplayer behavior is unchanged.

Compact responses are self-contained (no session cache): keyword definitions are
sent once per response and referenced by `keyword_refs`; duplicate deck cards
are grouped with `count`, `uids` and/or `indices`. Piles list only UIDs with
`pile_details_omitted: true`; query their details for pile-dependent decisions. All dynamic descriptions, target
previews, effects, counters, hand selectors and screen options remain available.
Full map `nodes` are omitted with `nodes_omitted: true`; current position, next
options, lookahead, marks and boss information remain. Retrieve the route graph
with `get_state_details("map")` before choosing a long-term path.

`get_state_details(section)` fetches a single full current section (deck,
draw_pile, discard_pile, exhaust_pile, relics, potions, hand, status, player, map).
It reports screen/run and whether the section exists; it is a fresh observation,
not the historical state returned by an earlier action.

An action timeout is NOT permission to retry it. Observe the state first.
The bridge ignores proxy environment variables by default for the local game
API; opt in with `--trust-env` if required. `--no-trust-env` remains supported.
Restart the MCP process/client connection after upgrading the Python files.
No DLL rebuild or game restart is required for this bridge-only change.

Newer FastMCP versions automatically duplicated string results into both text
and `structuredContent.result`. Tool registration now explicitly requests text
output only when supported by the SDK. The JSON text stays the same; each result
is transmitted once. Older SDKs keep their existing text-only behavior.

The draw pile API is display-sorted by rarity and ID, not actual draw order.
Compact state now reports `draw_pile_order: "display_sorted_not_draw_order"`;
`get_state_details("draw_pile")` carries the same warning as `order`.

### Navigation settlement safeguard

Live new-run testing found that the mod can return the old game-over/character
screen with `settled=true` before a click-triggered transition begins. For menu
navigation, map travel, rewards and other navigation actions, the bridge now
reads a pre-action snapshot. If the accepted response is still that old state,
it performs bounded, read-only polling internally until a changed state is ready
and identical across three observations. No mutation is ever retried. Failure to
confirm within five seconds returns `settled=false` plus an observation warning;
the action remains accepted. Ordinary combat cards incur no extra pre-read.
These hidden HTTP reads do not expose repeated full states to the model.
