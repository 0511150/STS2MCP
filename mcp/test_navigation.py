"""Regression cases reproduced by the new-run live test."""
import json
import unittest
from unittest.mock import AsyncMock, patch
import server


def response(payload):
    return type("Response", (), {"text": json.dumps(payload),
                                 "raise_for_status": lambda self: None})()


class NavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_old_game_over_response_waits_for_new_menu_without_reclicking(self):
        old = {"state_type": "game_over", "player": {"hp": 0}}
        new = {"state_type": "menu", "menu_screen": "main"}
        client = type("Client", (), {"post": AsyncMock(return_value=response(
            {"status": "ok", "settled": True, "changed": False, "state": old}))})()
        # One pre-read, one old observation, then three stable new observations.
        get = AsyncMock(side_effect=[json.dumps(x) for x in [old, old, new, new, new]])
        with patch.object(server, "_get_client", return_value=client), \
             patch.object(server, "_get", get), \
             patch.object(server.asyncio, "sleep", AsyncMock()):
            result = json.loads(await server.menu_select("main_menu"))
        self.assertEqual(result["state"]["menu_screen"], "main")
        self.assertTrue(result["settled"])
        self.assertTrue(result["transition_checked"])
        self.assertEqual(result["transition_polls"], 4)
        client.post.assert_awaited_once()

    async def test_already_changed_ready_navigation_uses_no_followup_get(self):
        before = {"state_type": "card_reward"}
        after = {"state_type": "rewards"}
        client = type("Client", (), {"post": AsyncMock(return_value=response(
            {"status": "ok", "settled": True, "changed": True, "state": after}))})()
        with patch.object(server, "_get_client", return_value=client), \
             patch.object(server, "_get", AsyncMock(return_value=json.dumps(before))) as get:
            result = await server.rewards_skip_card()
        self.assertEqual(json.loads(result)["state"]["state_type"], "rewards")
        get.assert_awaited_once()
        client.post.assert_awaited_once()

    async def test_observation_error_retains_accepted_action_and_does_not_retry(self):
        before = {"state_type": "menu", "menu_screen": "character_select"}
        client = type("Client", (), {"post": AsyncMock(return_value=response(
            {"status": "ok", "settled": True, "state": before}))})()
        get = AsyncMock(side_effect=[json.dumps(before), server.httpx.ReadTimeout("late")])
        with patch.object(server, "_get_client", return_value=client), \
             patch.object(server, "_get", get), \
             patch.object(server.asyncio, "sleep", AsyncMock()):
            result = json.loads(await server.menu_select("confirm"))
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["settled"])
        self.assertIn("transition_warning", result)
        self.assertIn("transition_observation_error", result)
        client.post.assert_awaited_once()

    async def test_deadline_returns_unsettled_instead_of_claiming_successful_settlement(self):
        state = {"state_type": "menu"}
        accepted = {"status": "ok", "settled": True, "state": state}
        with patch.object(server, "_get", AsyncMock()) as get:
            result = await server._finish_transition(accepted, state, timeout=0)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["settled"])
        self.assertIn("transition_warning", result)
        get.assert_not_awaited()

    async def test_enemy_phase_is_not_an_actionable_arrival(self):
        before = {"state_type": "map"}
        enemy = {"state_type": "monster", "battle": {"is_play_phase": False}}
        ready = {"state_type": "monster", "battle": {"is_play_phase": True}}
        accepted = {"status": "ok", "settled": True, "state": enemy}
        get = AsyncMock(side_effect=[json.dumps(x) for x in [enemy, ready, ready, ready]])
        with patch.object(server, "_get", get), \
             patch.object(server.asyncio, "sleep", AsyncMock()):
            result = await server._finish_transition(accepted, before)
        self.assertTrue(result["settled"])
        self.assertTrue(result["state"]["battle"]["is_play_phase"])
        self.assertEqual(result["transition_polls"], 4)


    async def test_map_highlight_is_not_a_completed_map_travel(self):
        before = {"state_type": "map", "run": {"act": 1, "floor": 1}, "map": {"marks": []}}
        intermediate = {**before, "map": {"marks": ["selected"]}}
        arrived = {"state_type": "monster", "run": {"act": 1, "floor": 2},
                   "battle": {"is_play_phase": True}}
        accepted = {"status": "ok", "settled": True, "changed": False, "state": intermediate}
        get = AsyncMock(side_effect=[json.dumps(x) for x in [intermediate, arrived, arrived, arrived]])
        with patch.object(server, "_get", get), \
             patch.object(server.asyncio, "sleep", AsyncMock()):
            result = await server._finish_transition(accepted, before, body={"action": "choose_map_node"})
        self.assertEqual(result["state"]["state_type"], "monster")
        self.assertTrue(result["settled"])
        self.assertEqual(result["transition_polls"], 4)

    async def test_character_selection_metadata_change_does_not_mean_embarked(self):
        before = {"state_type": "menu", "menu_screen": "character_select", "ready": False}
        intermediate = {**before, "ready": True}
        arrived = {"state_type": "event", "run": {"act": 1, "floor": 1}}
        accepted = {"status": "ok", "settled": True, "state": intermediate}
        get = AsyncMock(side_effect=[json.dumps(arrived)] * 3)
        with patch.object(server, "_get", get), \
             patch.object(server.asyncio, "sleep", AsyncMock()):
            result = await server._finish_transition(accepted, before,
                            body={"action": "menu_select", "option": "confirm"})
        self.assertEqual(result["state"]["state_type"], "event")
        self.assertTrue(result["settled"])


if __name__ == "__main__": unittest.main()
