import asyncio
from copy import deepcopy
import inspect
import json
import unittest
from unittest.mock import AsyncMock, patch

from compact_state import compact_response, compact_state
import server


class CompactTests(unittest.TestCase):
    def test_grouping_preserves_differences_and_instance_selectors(self):
        cards = [{"uid": "a", "index": 0, "cost": "1", "description": "6 damage", "upgrade_level": 1},
                 {"uid": "b", "index": 1, "cost": "1", "description": "6 damage", "upgrade_level": 1},
                 {"uid": "c", "index": 2, "cost": "0", "description": "6 damage", "upgrade_level": 1},
                 {"uid": "d", "index": 3, "cost": "1", "description": "8 damage", "upgrade_level": 2}]
        state = {"state_type": "monster", "player": {"hand": cards, "deck": cards, "draw_pile": cards}}
        original = deepcopy(state)
        compact = compact_state(state)
        self.assertEqual(state, original)
        self.assertEqual(compact["player"]["hand"], cards)
        groups = compact["player"]["deck"]
        self.assertEqual(compact["player"]["draw_pile"], ["a", "b", "c", "d"])
        self.assertTrue(compact["player"]["pile_details_omitted"])
        self.assertEqual(compact["player"]["draw_pile_order"], "display_sorted_not_draw_order")
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0]["uids"], ["a", "b"])
        self.assertEqual(groups[0]["indices"], [0, 1])
        self.assertEqual(sum(g["count"] for g in groups), 4)

    def test_keyword_dedup_keeps_distinct_dynamic_definitions(self):
        a = {"id": "LocString with Title=long", "name": "stance", "description": "gain 2"}
        b = {**a, "description": "gain 3"}
        state = {"state_type": "monster", "player": {"hand": [
            {"keywords": [a, b], "description": "x"}, {"keywords": [a]}]}}
        result = compact_state(state)
        self.assertEqual(len(result["keyword_definitions"]), 2)
        refs = result["player"]["hand"][0]["keyword_refs"]
        self.assertNotEqual(refs[0], refs[1])
        self.assertEqual(refs[0], result["player"]["hand"][1]["keyword_refs"][0])
        self.assertEqual(result["keyword_definitions"][refs[0]]["description"], "gain 2")
        self.assertEqual(compact_state(state), result)  # no cross-call cache

    def test_dynamic_decision_fields_and_unknown_extensions_survive(self):
        state = {"state_type": "boss", "is_resolving": False,
                 "battle": {"enemies": [{"alive": False, "hp": 0, "intent": {"damage": 0}}]},
                 "player": {"hand": [{"uid": "x", "can_play": False, "cost": "X",
                     "vs_targets": [{"damage": 12, "hits": 3, "damage_cap": 5}],
                     "upgrade_preview": {"description": "new"}}],
                     "relics": [{"counter": 0, "description": "effect"}],
                     "status": [{"description": "dynamic 9", "amount": -1}],
                     "potions": [{"slot": 2, "can_use_in_combat": False}]},
                 "future_extension": {"important": [0, False, ""]}}
        result = compact_state(state)
        for key in state: self.assertEqual(result[key], state[key])

    def test_map_only_omits_graph_and_keeps_action_selectors(self):
        state = {"state_type": "map", "map": {"nodes": [{"row": 1}],
                 "next_options": [{"index": 2, "leads_to": [{"row": 2}]}], "marks": [1]}}
        result = compact_state(state)
        self.assertTrue(result["map"]["nodes_omitted"])
        self.assertNotIn("nodes", result["map"])
        self.assertEqual(result["map"]["next_options"], state["map"]["next_options"])

    def test_selection_arrays_keep_original_indices(self):
        options = [{"index": 2, "description": "same"}, {"index": 5, "description": "same"}]
        for screen in ("hand_select", "card_reward", "card_select", "event", "shop", "rewards"):
            state = {"state_type": screen, "options": options}
            self.assertEqual(compact_state(state)["options"], options)

    def test_action_envelope_retains_errors_and_settle_flags(self):
        envelope = {"status": "ok", "settled": False, "changed": False,
                    "wait_error": "timeout", "state": {"state_type": "monster"}}
        result = json.loads(compact_response(json.dumps(envelope)))
        for key in ("status", "settled", "changed", "wait_error"):
            self.assertEqual(result[key], envelope[key])
        self.assertEqual(result["state"]["response_mode"], "compact")
        self.assertEqual(compact_response("not json"), "not json")
        self.assertEqual(json.loads(compact_response('{"status":"error","error":"bad"}')),
                         {"status": "error", "error": "bad"})


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_compact_get_requests_json_but_explicit_full_is_unchanged(self):
        text = '{"state_type":"map","map":{"nodes":[1]}}'
        response = type("Response", (), {"text": text, "raise_for_status": lambda self: None})()
        client = type("Client", (), {"get": AsyncMock(return_value=response)})()
        with patch.object(server, "_get_client", return_value=client):
            compact = json.loads(await server.get_game_state())
            self.assertTrue(compact["map"]["nodes_omitted"])
            self.assertEqual(client.get.call_args.kwargs["params"], {"format": "json"})
            self.assertEqual(await server.get_game_state("json"), text)
            self.assertEqual(await server.get_game_state("markdown"), text)

    async def test_action_defaults_waits_and_projects_once_without_retry(self):
        text = '{"status":"ok","settled":true,"state":{"state_type":"monster"}}'
        response = type("Response", (), {"text": text, "raise_for_status": lambda self: None})()
        client = type("Client", (), {"post": AsyncMock(return_value=response)})()
        with patch.object(server, "_get_client", return_value=client):
            result = json.loads(await server.combat_play_card(card_uid="x"))
            self.assertEqual(result["state"]["response_mode"], "compact")
            self.assertTrue(client.post.call_args.kwargs["json"]["wait"])
            client.post.assert_awaited_once()
            await server.combat_end_turn(wait=False)
            self.assertNotIn("wait", client.post.call_args.kwargs["json"])

    async def test_timeout_is_not_retried(self):
        client = type("Client", (), {"post": AsyncMock(side_effect=server.httpx.ReadTimeout("late"))})()
        with patch.object(server, "_get_client", return_value=client):
            self.assertTrue((await server.combat_end_turn()).startswith("Error:"))
            client.post.assert_awaited_once()

    async def test_detail_selection_and_unavailable_sections(self):
        state = {"state_type": "map", "run": {"floor": 40}, "map": {"nodes": [1]},
                 "player": {"relics": [{"description": "full"}], "draw_pile": [{"uid": "a"}]}}
        with patch.object(server, "_get", AsyncMock(return_value=json.dumps(state))) as get:
            result = json.loads(await server.get_state_details("map"))
            self.assertEqual(result["data"], {"nodes": [1]})
            self.assertNotIn("player", result)
            self.assertFalse(json.loads(await server.get_state_details("hand"))["available"])
            self.assertTrue((await server.get_state_details("bad")).startswith("Error:"))
            pile = json.loads(await server.get_state_details("draw_pile"))
            self.assertEqual(pile["order"], "display_sorted_not_draw_order")
            self.assertEqual(pile["data"], [{"uid": "a"}])
            self.assertEqual(get.await_count, 3)

    async def test_registered_schema_defaults(self):
        tools = {t.name: t for t in await server.mcp.list_tools()}
        self.assertIn("get_state_details", tools)
        self.assertIsNone(tools["get_game_state"].outputSchema)
        with patch.object(server, "_get", AsyncMock(return_value='{"state_type":"map"}')):
            result = await server.mcp.call_tool("get_game_state", {})
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "text")
        self.assertEqual(tools["get_game_state"].inputSchema["properties"]["format"]["default"], "compact")
        self.assertTrue(tools["combat_end_turn"].inputSchema["properties"]["wait"]["default"])


if __name__ == "__main__": unittest.main()
