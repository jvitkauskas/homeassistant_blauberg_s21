"""Discovery setup and interface selection using the actual HA flow manager."""

import asyncio
import socket
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pybls21 import DiscoveredDevice, DiscoveryError

from custom_components.blauberg_s21.const import DOMAIN
from custom_components.blauberg_s21.discovery import (
    async_discover_devices,
    async_identify_device,
)

DEVICE = DiscoveredDevice(host="192.168.1.149", device_id="0024005433375107")


async def discovered_flow(hass, discovery):
    discovery[0].return_value = (DEVICE,)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "discovered"}
    )
    assert result["step_id"] == "discovered"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device": DEVICE.device_id}
    )
    assert result["step_id"] == "manual"
    assert result["data_schema"]({}) == {"host": DEVICE.host, "port": 502}
    return result


async def test_discovered_setup_confirms_modbus_and_identity(hass, discovery, client):
    result = await discovered_flow(hass, discovery)
    discovery[1].return_value = DEVICE.device_id
    with patch("custom_components.blauberg_s21.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": DEVICE.host, "port": 1502}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == DEVICE.device_id
    assert result["data"] == {"host": DEVICE.host, "port": 1502}
    client.poll.assert_awaited_once()
    discovery[1].assert_awaited_once_with(DEVICE.host)


@pytest.mark.parametrize(
    "identity,reason",
    [(None, "cannot_identify"), ("another-controller", "wrong_device")],
)
async def test_stale_discovery_does_not_configure_another_device(
    hass, discovery, client, identity, reason
):
    result = await discovered_flow(hass, discovery)
    discovery[1].return_value = identity
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": DEVICE.host, "port": 502}
    )
    assert result["errors"] == {"base": reason}
    assert result["type"] == FlowResultType.FORM


async def test_manual_choice_remains_available(hass, discovery, client):
    discovery[0].return_value = (DEVICE,)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["step_id"] == "manual"
    with patch("custom_components.blauberg_s21.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "remote.local", "port": 502}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id is None


async def test_hardware_id_detects_duplicate_at_different_host(
    hass, discovery, client, entry
):
    hass.config_entries.async_update_entry(entry, unique_id=DEVICE.device_id)
    discovery[1].return_value = DEVICE.device_id
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={"host": DEVICE.host, "port": 502}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == "s21.local"


async def test_reconfigure_learns_identity_without_replacing_entry(
    hass, discovery, client, entry
):
    original_id = entry.entry_id
    discovery[1].return_value = DEVICE.device_id
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            data={"host": DEVICE.host, "port": 502},
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == DEVICE.device_id
    assert entry.entry_id == original_id
    assert entry.data["host"] == DEVICE.host
    reload.assert_awaited_once_with(original_id)


async def test_reconfigure_rejects_different_controller(hass, discovery, client, entry):
    hass.config_entries.async_update_entry(entry, unique_id=DEVICE.device_id)
    discovery[1].return_value = "different"
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        data={"host": "new.local", "port": 502},
    )
    assert result["errors"] == {"base": "wrong_device"}
    assert entry.data["host"] == "s21.local"
    assert entry.unique_id == DEVICE.device_id


def adapter(enabled, *addresses):
    return {
        "enabled": enabled,
        "ipv4": [{"address": ip, "network_prefix": prefix} for ip, prefix in addresses],
    }


async def test_enabled_interfaces_subnets_duplicates_and_failures(hass):
    adapters = [
        adapter(True, ("192.168.1.10", 24)),
        adapter(True, ("192.168.1.10", 24)),
        adapter(True, ("10.0.0.10", 23)),
        adapter(False, ("192.168.2.10", 24)),
        adapter(True, ("127.0.0.1", 8), ("10.9.0.1", 32)),
        adapter(True, ("172.16.0.10", 24)),
    ]

    async def scan(**kwargs):
        if kwargs["local_address"] == "172.16.0.10":
            raise DiscoveryError("unavailable")
        return (DEVICE,)

    with (
        patch(
            "custom_components.blauberg_s21.discovery.network.async_get_adapters",
            return_value=adapters,
        ),
        patch(
            "custom_components.blauberg_s21.discovery.discover", side_effect=scan
        ) as discover,
    ):
        assert await async_discover_devices(hass) == (DEVICE,)
        assert discover.await_count == 3
        assert {c.kwargs["address"] for c in discover.await_args_list} == {
            "192.168.1.255",
            "10.0.1.255",
            "172.16.0.255",
        }
        assert all(c.kwargs["timeout"] == 3 for c in discover.await_args_list)


async def test_no_enabled_ipv4_interfaces(hass):
    with (
        patch(
            "custom_components.blauberg_s21.discovery.network.async_get_adapters",
            return_value=[],
        ),
        patch("custom_components.blauberg_s21.discovery.discover") as discover,
    ):
        assert await async_discover_devices(hass) == ()
        discover.assert_not_called()


async def test_identify_literal_hostname_and_unrelated_responses():
    loop = asyncio.get_running_loop()
    unrelated = DiscoveredDevice(host="192.168.2.1", device_id="other")
    with patch(
        "custom_components.blauberg_s21.discovery.discover",
        return_value=(unrelated, DEVICE),
    ) as discover:
        assert await async_identify_device(DEVICE.host) == DEVICE.device_id
        with patch.object(
            loop,
            "getaddrinfo",
            return_value=[
                (socket.AF_INET, socket.SOCK_DGRAM, 17, "", (DEVICE.host, 4000))
            ],
        ) as resolve:
            assert await async_identify_device("s21.local") == DEVICE.device_id
            resolve.assert_awaited_once()
        discover.return_value = (unrelated,)
        assert await async_identify_device(DEVICE.host) is None
        discover.side_effect = DiscoveryError("blocked")
        assert await async_identify_device(DEVICE.host) is None


@pytest.mark.parametrize("result", [[], OSError("DNS unavailable"), TimeoutError()])
async def test_identify_dns_failure(result):
    with patch.object(
        asyncio.get_running_loop(),
        "getaddrinfo",
        side_effect=result if isinstance(result, Exception) else None,
        return_value=result,
    ):
        assert await async_identify_device("missing.local") is None


async def test_discovery_cancellation_propagates(hass):
    entered = asyncio.Event()

    async def wait(**kwargs):
        entered.set()
        await asyncio.Event().wait()

    with (
        patch(
            "custom_components.blauberg_s21.discovery.network.async_get_adapters",
            return_value=[adapter(True, ("192.168.1.10", 24))],
        ),
        patch("custom_components.blauberg_s21.discovery.discover", side_effect=wait),
    ):
        task = asyncio.create_task(async_discover_devices(hass))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
