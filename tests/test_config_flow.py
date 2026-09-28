"""UI setup, duplicate detection, errors, and endpoint reconfiguration."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pybls21 import ModbusCommunicationException, UnsupportedDeviceException

from custom_components.blauberg_s21.const import DOMAIN


async def test_user_flow(hass, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    with patch("custom_components.blauberg_s21.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": " S21.LOCAL ", "port": 502}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {"host": "s21.local", "port": 502}
    assert result["result"].unique_id is None


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (ModbusCommunicationException("offline"), "cannot_connect"),
        (TimeoutError(), "cannot_connect"),
        (UnsupportedDeviceException("wrong type"), "unsupported_device"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
async def test_flow_errors(hass, client, error, reason):
    client.poll.side_effect = error
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={"host": "s21.local", "port": 502}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": reason}


async def test_duplicate_and_empty_host(hass, entry, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={"host": "S21.LOCAL", "port": 502}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={"host": " ", "port": 502}
    )
    assert result["errors"] == {"host": "invalid_host"}
    client.poll.assert_not_called()


async def test_reconfigure_keeps_entry_identity(hass, entry, client):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    assert result["step_id"] == "reconfigure"
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "new.local", "port": 1502}
        )
        await hass.async_block_till_done()
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {"host": "new.local", "port": 1502}
    reload.assert_awaited_once_with(entry.entry_id)
