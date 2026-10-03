"""Deterministic volume regressions using small HA lifecycle substitutes.

Run with: python -m unittest discover -s tests -v
These tests execute the production client, coordinator, flows and entity methods;
they do not replace validation inside a real Home Assistant instance.
"""

from __future__ import annotations

import asyncio
from enum import Enum, IntFlag
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import xml.etree.ElementTree as ET

import voluptuous as vol


REAL_SLEEP = asyncio.sleep
ROOT = Path(__file__).resolve().parents[1]


class FakeCoordinator:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.data = None
        self.last_update_success = True

    async def async_request_refresh(self):
        self.data = await self._async_update_data()

    async def async_config_entry_first_refresh(self):
        await self.async_request_refresh()


class FakeFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass


class FakeCoordinatorEntity:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator


def load_integration():
    """Isolate HA substitutes to imports, without polluting other test suites."""

    modules = {}
    for name in (
        "homeassistant", "homeassistant.core", "homeassistant.const",
        "homeassistant.config_entries", "homeassistant.data_entry_flow",
        "homeassistant.exceptions", "homeassistant.helpers",
        "homeassistant.helpers.update_coordinator",
        "homeassistant.helpers.aiohttp_client",
        "homeassistant.helpers.config_validation",
        "homeassistant.helpers.entity_registry",
        "homeassistant.helpers.entity_platform",
        "homeassistant.components", "homeassistant.components.media_player",
        "homeassistant.components.media_player.const",
    ):
        modules[name] = ModuleType(name)
    modules["homeassistant.core"].HomeAssistant = object
    modules["homeassistant.core"].ServiceCall = object
    modules["homeassistant.core"].callback = lambda func: func
    modules["homeassistant.const"].Platform = SimpleNamespace(
        MEDIA_PLAYER="media_player", SENSOR="sensor",
    )
    entries = modules["homeassistant.config_entries"]
    entries.ConfigEntry = object
    entries.ConfigFlow = FakeFlow
    entries.OptionsFlow = FakeFlow
    modules["homeassistant"].config_entries = entries
    modules["homeassistant.data_entry_flow"].FlowResult = dict
    modules["homeassistant.exceptions"].HomeAssistantError = RuntimeError
    update = modules["homeassistant.helpers.update_coordinator"]
    update.DataUpdateCoordinator = FakeCoordinator
    update.CoordinatorEntity = FakeCoordinatorEntity
    update.UpdateFailed = type("UpdateFailed", (Exception,), {})
    modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = (
        lambda hass: hass.session
    )
    helpers = modules["homeassistant.helpers"]
    helpers.config_validation = modules["homeassistant.helpers.config_validation"]
    helpers.entity_registry = modules["homeassistant.helpers.entity_registry"]
    modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object
    modules["homeassistant.components.media_player"].MediaPlayerEntity = type(
        "MediaPlayerEntity", (), {},
    )
    media_const = modules["homeassistant.components.media_player.const"]
    media_const.MediaPlayerEntityFeature = IntFlag(
        "MediaPlayerEntityFeature", ["TURN_ON", "TURN_OFF", "VOLUME_SET", "SELECT_SOURCE"],
    )
    media_const.MediaPlayerState = Enum(
        "MediaPlayerState", {name: name.lower() for name in (
            "IDLE", "PLAYING", "PAUSED", "OFF", "BUFFERING",
        )},
    )
    package_path = ROOT / "custom_components" / "bose_soundtouch"
    spec = importlib.util.spec_from_file_location(
        "_bose_volume_tests", package_path / "__init__.py",
        submodule_search_locations=[str(package_path)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(package)
        from _bose_volume_tests import client, config_flow, coordinator, media_player
    return package, client, config_flow, coordinator, media_player, update.UpdateFailed


integration, client_module, flows, controller, media, UpdateFailed = load_integration()


def state(volume):
    return client_module.SoundTouchState(
        device_id="MAC", name="Speaker", device_type="SoundTouch",
        volume=volume, target_volume=None, is_muted=False,
        source="AUX", source_account=None, status="PLAY_STATE",
        zone_members=[], is_master=False, zone_master_mac=None,
        ip_address="192.0.2.1",
    )


class Clock:
    def __init__(self):
        self.now = 0.0
        self.delays = []

    async def sleep(self, delay):
        self.delays.append(delay)
        self.now += delay
        await REAL_SLEEP(0)


class Speaker:
    host = "192.0.2.1"

    def __init__(self, volume=10):
        self.volume = volume
        self.writes = []
        self.ignored = 0
        self.write_failures = 0
        self.read_failures = 0
        self.poll_failures = 0
        self.reads = 0

    async def async_get_volume(self):
        self.reads += 1
        if self.read_failures:
            self.read_failures -= 1
            raise client_module.SoundTouchError("offline")
        return self.volume

    async def async_set_volume(self, volume):
        self.writes.append(volume)
        if self.write_failures:
            self.write_failures -= 1
            raise client_module.SoundTouchError("write failed")
        if self.ignored:
            self.ignored -= 1
        else:
            self.volume = volume

    async def async_get_state(self):
        if self.poll_failures:
            self.poll_failures -= 1
            raise client_module.SoundTouchError("poll failed")
        return state(self.volume)


class VolumeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clock = Clock()
        self.time_patch = patch.object(controller, "monotonic", lambda: self.clock.now)
        self.sleep_patch = patch.object(controller.asyncio, "sleep", self.clock.sleep)
        self.time_patch.start()
        self.sleep_patch.start()
        self.speaker = Speaker()
        self.tasks = []

        def create_task(coro, name):
            task = asyncio.create_task(coro, name=name)
            self.tasks.append(task)
            return task

        self.hass = SimpleNamespace(async_create_background_task=create_task)
        self.coordinator = controller.SoundTouchCoordinator(self.hass, self.speaker)
        self.coordinator.data = state(self.speaker.volume)

    async def asyncTearDown(self):
        await self.coordinator.async_stop_volume()
        self.sleep_patch.stop()
        self.time_patch.stop()
        for task in self.tasks:
            if not task.cancelled():
                task.result()

    async def finish(self):
        for _ in range(200):
            if self.coordinator._volume_task.done():
                await self.coordinator._volume_task
                return
            await REAL_SLEEP(0)
        self.fail("Volume controller did not converge")

    async def test_ignored_writes_are_retried_until_actual_target(self):
        self.speaker.ignored = 4
        await self.coordinator.async_set_volume(35)
        await self.finish()
        self.assertEqual(self.speaker.writes, [35] * 5)
        self.assertEqual(self.coordinator.data.volume, 35)
        self.assertEqual(self.coordinator.desired_volume, 35)

    async def test_failed_writes_and_reads_recover(self):
        self.speaker.write_failures = 2
        self.speaker.read_failures = 2
        with self.assertLogs(controller.__name__, level="WARNING"):
            await self.coordinator.async_set_volume(40)
            await self.finish()
        self.assertEqual(self.speaker.volume, 40)
        self.assertGreaterEqual(self.speaker.reads, 5)

    async def test_transport_backoff_is_capped_and_target_survives(self):
        self.speaker.read_failures = 8
        with self.assertLogs(controller.__name__, level="WARNING"):
            await self.coordinator.async_set_volume(40)
            await self.finish()
        self.assertEqual(self.clock.delays[:8], [1, 2, 4, 8, 15, 15, 15, 15])
        self.assertEqual(self.speaker.volume, 40)

    async def test_poll_corrects_drift_after_target_confirmation_without_outage(self):
        await self.coordinator.async_set_volume(30)
        await self.finish()
        self.clock.now += 3600
        self.speaker.volume = 9
        result = await self.coordinator._async_update_data()
        self.assertEqual(result.volume, 30)
        self.assertEqual(self.speaker.writes, [30, 30])

    async def test_poll_failure_does_not_discard_target_or_change_tolerance(self):
        await self.coordinator.async_set_volume(25)
        await self.finish()
        self.speaker.poll_failures = 4
        with self.assertLogs(controller.__name__, level="WARNING"):
            for _ in range(3):
                self.assertIs(
                    await self.coordinator._async_update_data(), self.coordinator.data,
                )
            with self.assertRaises(UpdateFailed):
                await self.coordinator._async_update_data()
        self.speaker.volume = 2
        self.clock.now += 3600
        self.assertEqual((await self.coordinator._async_update_data()).volume, 25)

    async def test_no_target_means_no_writes(self):
        await self.coordinator._async_update_data()
        self.assertEqual(self.speaker.writes, [])
        self.assertIsNone(self.coordinator.desired_volume)

    async def test_defaults_and_zero_duration_are_immediate(self):
        await self.coordinator.async_set_volume(20)
        self.assertEqual(self.speaker.writes, [20])
        self.assertEqual(self.coordinator.data.volume, 20)
        await self.finish()
        self.assertEqual(self.speaker.writes, [20])
        self.coordinator.configure_volume(True, 0)
        await self.coordinator.async_set_volume(0)
        self.assertEqual(self.speaker.writes, [20, 0])
        await self.finish()
        self.assertEqual(self.speaker.writes, [20, 0])

    async def test_upward_fade_is_linear_and_uses_fresh_not_cached_volume(self):
        self.coordinator.data = state(1)
        self.coordinator.configure_volume(True, 1000)
        await self.coordinator.async_set_volume(20)
        await self.finish()
        self.assertEqual(self.speaker.writes, list(range(11, 21)))
        self.assertAlmostEqual(self.clock.now, 2.0)
        self.assertEqual(self.coordinator.data.volume, 20)

    async def test_downward_fade_ends_at_zero(self):
        self.speaker.volume = 10
        self.coordinator.configure_volume(True, 1000)
        await self.coordinator.async_set_volume(0)
        await self.finish()
        self.assertEqual(self.speaker.writes, list(range(9, -1, -1)))

    async def test_short_fade_and_small_delta_skip_duplicate_steps(self):
        self.coordinator.configure_volume(True, 250)
        await self.coordinator.async_set_volume(11)
        await self.finish()
        self.assertEqual(self.speaker.writes, [11])
        self.assertAlmostEqual(self.clock.now, 1.25)

    async def test_superseding_request_cancels_old_fade(self):
        self.coordinator.configure_volume(True, 1000)
        await self.coordinator.async_set_volume(90)
        await REAL_SLEEP(0)
        await REAL_SLEEP(0)
        old_task = self.coordinator._volume_task
        before = len(self.speaker.writes)
        await self.coordinator.async_set_volume(0)
        await self.finish()
        self.assertTrue(old_task.cancelled())
        self.assertNotIn(90, self.speaker.writes[before:])
        self.assertEqual(self.speaker.volume, 0)
        self.assertEqual(self.coordinator.desired_volume, 0)

    async def test_poll_does_not_jump_to_target_during_fade(self):
        self.coordinator.configure_volume(True, 1000)
        await self.coordinator.async_set_volume(80)
        await REAL_SLEEP(0)
        await self.coordinator._async_update_data()
        self.assertNotIn(80, self.speaker.writes)
        await self.finish()
        self.assertEqual(self.speaker.volume, 80)

    async def test_fade_failure_resumes_with_direct_final_target(self):
        self.coordinator.configure_volume(True, 1000)
        self.speaker.write_failures = 1
        with self.assertLogs(controller.__name__, level="WARNING"):
            await self.coordinator.async_set_volume(20)
            await self.finish()
        self.assertEqual(self.speaker.writes, [11, 20])

    async def test_ignored_fade_steps_still_reach_final_target(self):
        self.coordinator.configure_volume(True, 1000)
        self.speaker.ignored = 10
        await self.coordinator.async_set_volume(20)
        await self.finish()
        self.assertEqual(self.speaker.writes, [*range(11, 21), 20])
        self.assertEqual(self.coordinator.data.volume, 20)

    async def test_failed_drift_correction_is_retried_on_next_poll(self):
        await self.coordinator.async_set_volume(20)
        await self.finish()
        self.speaker.volume = 5
        self.speaker.write_failures = 1
        with self.assertLogs(controller.__name__, level="WARNING"):
            self.assertEqual((await self.coordinator._async_update_data()).volume, 5)
        self.assertEqual(self.coordinator.desired_volume, 20)
        self.assertEqual((await self.coordinator._async_update_data()).volume, 20)

    async def test_options_change_preserves_target(self):
        await self.coordinator.async_set_volume(20)
        await self.finish()
        self.hass.data = {"bose_soundtouch": {"entry": {"coordinator": self.coordinator}}}
        entry = SimpleNamespace(
            entry_id="entry", options={"enable_volume_fade": True, "volume_fade_duration": 500},
        )
        await integration._async_update_options(self.hass, entry)
        self.assertEqual(self.coordinator.desired_volume, 20)
        self.assertTrue(self.coordinator._enable_volume_fade)
        self.assertEqual(self.coordinator._volume_fade_duration, 500)

    async def test_simultaneous_requests_leave_only_the_latest_controller(self):
        self.coordinator.configure_volume(True, 1000)
        await asyncio.gather(
            self.coordinator.async_set_volume(80),
            self.coordinator.async_set_volume(20),
            self.coordinator.async_set_volume(40),
        )
        await self.finish()
        self.assertEqual(self.coordinator.desired_volume, 40)
        self.assertEqual(self.speaker.volume, 40)
        self.assertEqual(sum(not task.cancelled() for task in self.tasks), 1)

    async def test_unload_cancels_fade_and_prevents_further_writes(self):
        self.coordinator.configure_volume(True, 10000)
        await self.coordinator.async_set_volume(100)
        await REAL_SLEEP(0)
        old_task = self.coordinator._volume_task
        self.hass.data = {"bose_soundtouch": {"entry": {"coordinator": self.coordinator}}}
        self.hass.config_entries = SimpleNamespace(async_unload_platforms=AsyncMock(return_value=True))
        self.assertTrue(await integration.async_unload_entry(
            self.hass, SimpleNamespace(entry_id="entry"),
        ))
        self.assertTrue(old_task.cancelled())
        before = list(self.speaker.writes)
        await self.coordinator._async_update_data()
        await REAL_SLEEP(0)
        self.assertEqual(self.speaker.writes, before)
        self.assertNotIn("entry", self.hass.data["bose_soundtouch"])
        with self.assertRaises(client_module.SoundTouchError):
            await self.coordinator.async_set_volume(50)

    async def test_failed_unload_keeps_controller(self):
        self.hass.data = {"bose_soundtouch": {"entry": {"coordinator": self.coordinator}}}
        self.hass.config_entries = SimpleNamespace(async_unload_platforms=AsyncMock(return_value=False))
        self.assertFalse(await integration.async_unload_entry(
            self.hass, SimpleNamespace(entry_id="entry"),
        ))
        await self.coordinator.async_set_volume(20)
        await self.finish()
        self.assertEqual(self.speaker.volume, 20)

    async def test_entity_routes_requests_through_controller_and_clamps(self):
        player = media.SoundTouchMediaPlayer(
            self.coordinator, SimpleNamespace(unique_id="MAC", entry_id="entry", title="Speaker"),
        )
        await player.async_set_volume_level(0.375)
        await self.finish()
        self.assertEqual(self.coordinator.desired_volume, 38)
        await player.async_set_volume_level(1.5)
        await self.finish()
        self.assertEqual(self.speaker.volume, 100)
        await player.async_set_volume_level(-1)
        await self.finish()
        self.assertEqual(self.speaker.volume, 0)


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_options_defaults_and_validation(self):
        flow = flows.BoseSoundTouchOptionsFlow()
        flow.config_entry = SimpleNamespace(options={})
        form = await flow.async_step_init()
        values = form["data_schema"]({})
        self.assertEqual(values, {
            "enable_volume_fade": False, "volume_fade_duration": 1000,
        })
        with self.assertRaises(vol.Invalid):
            form["data_schema"]({"volume_fade_duration": -1})
        with self.assertRaises(vol.Invalid):
            form["data_schema"]({"volume_fade_duration": "invalid"})
        with self.assertRaises(vol.Invalid):
            form["data_schema"]({"enable_volume_fade": "true"})
        values = form["data_schema"]({
            "enable_volume_fade": True, "volume_fade_duration": 2500,
        })
        self.assertEqual((await flow.async_step_init(values))["data"], values)

    async def test_options_keep_existing_values(self):
        flow = flows.BoseSoundTouchOptionsFlow()
        options = {"enable_volume_fade": True, "volume_fade_duration": 3500}
        flow.config_entry = SimpleNamespace(options=options)
        form = await flow.async_step_init()
        self.assertEqual(form["data_schema"]({}), options)

    async def test_onboarding_saves_host_and_fade_options_separately(self):
        flow = flows.BoseSoundTouchConfigFlow()
        flow.hass = SimpleNamespace()
        schema = (await flow.async_step_user())["data_schema"]
        values = schema({"host": "192.0.2.1", "enable_volume_fade": True})
        with patch.object(flows, "_async_validate_input", AsyncMock(return_value={
            "device_id": "MAC", "name": "Speaker",
        })):
            result = await flow.async_step_user(values)
        self.assertEqual(result["data"], {"host": "192.0.2.1"})
        self.assertEqual(result["options"], {
            "enable_volume_fade": True, "volume_fade_duration": 1000,
        })

    async def test_setup_applies_defaults_to_existing_entries(self):
        speaker = Speaker()
        hass = SimpleNamespace(
            data={"bose_soundtouch": {"services_registered": True}},
            session=object(),
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )
        entry = SimpleNamespace(
            entry_id="entry", data={"host": speaker.host}, options={},
            add_update_listener=lambda listener: listener,
            async_on_unload=lambda callback: None,
        )
        with patch.object(integration, "SoundTouchClient", return_value=speaker):
            self.assertTrue(await integration.async_setup_entry(hass, entry))
        coordinator = hass.data["bose_soundtouch"]["entry"]["coordinator"]
        self.assertFalse(coordinator._enable_volume_fade)
        self.assertEqual(coordinator._volume_fade_duration, 1000)
        self.assertIsNone(coordinator.desired_volume)
        self.assertEqual(speaker.writes, [])
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()


class ClientVolumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_actual_not_target_volume(self):
        client = client_module.SoundTouchClient(SimpleNamespace(), "192.0.2.1")
        client._request = AsyncMock(return_value=ET.fromstring(
            "<volume><actualvolume>12</actualvolume><targetvolume>50</targetvolume></volume>",
        ))
        self.assertEqual(await client.async_get_volume(), 12)
        client._request.assert_awaited_once_with("get", "/volume")

    async def test_missing_invalid_or_out_of_range_volume_is_not_success(self):
        client = client_module.SoundTouchClient(SimpleNamespace(), "192.0.2.1")
        for xml in (
            None, "<volume/>",
            "<volume><actualvolume>bad</actualvolume></volume>",
            "<volume><actualvolume>-1</actualvolume></volume>",
            "<volume><actualvolume>101</actualvolume></volume>",
            "<volume><actualvolume>1</actualvolume><targetvolume>bad</targetvolume></volume>",
        ):
            with self.subTest(xml=xml):
                client._request = AsyncMock(return_value=ET.fromstring(xml) if xml else None)
                with self.assertRaises(client_module.SoundTouchError):
                    await client.async_get_volume()


if __name__ == "__main__":
    unittest.main()
