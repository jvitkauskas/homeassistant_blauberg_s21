"""Deadlines and command serialization across entities."""

import asyncio

import pytest
from homeassistant.exceptions import HomeAssistantError


async def test_whole_command_deadline_cleans_up_and_recovers(
    hass, entry, client, monkeypatch
):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    blocked = asyncio.Event()
    client.turn_on.side_effect = blocked.wait
    monkeypatch.setattr(
        "custom_components.blauberg_s21.coordinator.OPERATION_TIMEOUT", 0
    )
    with pytest.raises(HomeAssistantError) as caught:
        await entry.runtime_data.async_execute(client.turn_on)
    assert isinstance(caught.value.__cause__, TimeoutError)
    assert not entry.runtime_data.last_update_success
    monkeypatch.setattr(
        "custom_components.blauberg_s21.coordinator.OPERATION_TIMEOUT", 20
    )
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.last_update_success


async def test_commands_and_confirmation_polls_are_serialized(hass, entry, client):
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client.reset_mock()
    started = asyncio.Event()
    release = asyncio.Event()

    async def turn_on():
        started.set()
        await release.wait()

    client.turn_on.side_effect = turn_on
    first = asyncio.create_task(entry.runtime_data.async_execute(client.turn_on))
    second = None
    try:
        async with asyncio.timeout(2):
            await started.wait()
            second = asyncio.create_task(
                entry.runtime_data.async_execute(client.turn_off)
            )
            await asyncio.sleep(0)
            client.turn_off.assert_not_awaited()
            client.poll.assert_not_awaited()
            release.set()
            await asyncio.gather(first, second)
    finally:
        release.set()
        for task in (first, second):
            if task and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert [item[0] for item in client.mock_calls] == [
        "turn_on",
        "poll",
        "turn_off",
        "poll",
    ]
