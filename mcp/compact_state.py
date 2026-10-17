"""Stateless compaction of STS2 state responses with explicit on-demand details.

Actionable hand descriptions, target previews, options and effects are preserved.
Duplicate definitions/instances are grouped. Pile details and map graph are on demand.
"""
import json
from copy import deepcopy


def _dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _group_cards(cards):
    if not isinstance(cards, list) or not all(isinstance(c, dict) for c in cards):
        return cards
    groups = {}
    for card in cards:
        item = {k: v for k, v in card.items() if k not in ("uid", "index")}
        key = _dump(item)
        if key not in groups:
            groups[key] = {**item, "count": 0}
        group = groups[key]
        group["count"] += 1
        if "uid" in card:
            group.setdefault("uids", []).append(card["uid"])
        if "index" in card:
            group.setdefault("indices", []).append(card["index"])
    return list(groups.values())


def compact_state(state):
    if not isinstance(state, dict) or "state_type" not in state:
        return deepcopy(state)
    result = deepcopy(state)
    player = result.get("player")
    if isinstance(player, dict):
        # Never group the hand or selection options: their selectors stay unchanged.
        if "deck" in player:
            player["deck"] = _group_cards(player["deck"])
        for field in ("draw_pile", "discard_pile", "exhaust_pile"):
            cards = player.get(field)
            if isinstance(cards, list) and all(isinstance(c, dict) and "uid" in c for c in cards):
                # These are not the actionable hand. Retain membership, not repeated text.
                player[field] = [c["uid"] for c in cards]
                player["pile_details_omitted"] = True
                if field == "draw_pile":
                    player["draw_pile_order"] = "display_sorted_not_draw_order"
    glossary = {}
    lookup = {}

    def visit(value):
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        output = {}
        for key, item in value.items():
            if key == "keywords" and isinstance(item, list):
                refs = []
                for keyword in item:
                    # Unknown keyword shapes are retained verbatim, never discarded.
                    if not isinstance(keyword, dict) or not keyword.get("description"):
                        refs.append(visit(keyword))
                        continue
                    definition = dict(keyword)
                    if str(definition.get("id", "")).startswith("LocString with Title="):
                        definition.pop("id")
                    signature = _dump(definition)
                    if signature not in lookup:
                        ref = "k" + str(len(lookup))
                        lookup[signature] = ref
                        glossary[ref] = definition
                    refs.append(lookup[signature])
                if refs:
                    output["keyword_refs"] = refs
            elif item is not None:
                output[key] = visit(item)
        return output

    result = visit(result)
    if glossary:
        result["keyword_definitions"] = glossary
    map_state = result.get("map")
    if isinstance(map_state, dict) and "nodes" in map_state:
        map_state.pop("nodes")
        map_state["nodes_omitted"] = True
    result["response_mode"] = "compact"
    result["compact_schema_version"] = 1
    return result


def compact_response(text):
    """Project a GET state or an action envelope without altering error semantics."""
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return text
    if not isinstance(payload, dict):
        return text
    if "state_type" in payload:
        payload = compact_state(payload)
    elif isinstance(payload.get("state"), dict):
        payload = {**payload, "state": compact_state(payload["state"])}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
