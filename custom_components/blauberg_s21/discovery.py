"""Discover controllers using Home Assistant's selected network interfaces."""

import asyncio
import logging
import socket
from ipaddress import IPv4Address, IPv4Interface

from homeassistant.components import network
from homeassistant.core import HomeAssistant
from pybls21 import DiscoveredDevice, DiscoveryError, discover

_LOGGER = logging.getLogger(__name__)


async def _async_discover(
    *, address: str, timeout: float, local_address: str = "0.0.0.0"
) -> tuple[DiscoveredDevice, ...]:
    """Let a failed interface or blocked UDP fall back to manual configuration."""
    try:
        return await discover(
            address=address, timeout=timeout, local_address=local_address
        )
    except DiscoveryError:
        _LOGGER.debug("S21 discovery unavailable", exc_info=True)
        return ()


async def async_discover_devices(hass: HomeAssistant) -> tuple[DiscoveredDevice, ...]:
    """Search enabled IPv4 interfaces concurrently, deduplicating controller IDs."""
    adapters = await network.async_get_adapters(hass)
    interfaces = {
        IPv4Interface(f"{ip['address']}/{ip['network_prefix']}")
        for adapter in adapters
        if adapter["enabled"]
        for ip in adapter["ipv4"]
    }
    results = await asyncio.gather(
        *(
            _async_discover(
                address=str(interface.network.broadcast_address),
                local_address=str(interface.ip),
                timeout=3.0,
            )
            for interface in sorted(interfaces)
            if not interface.ip.is_loopback and interface.network.prefixlen < 31
        )
    )
    devices: dict[str, DiscoveredDevice] = {}
    for result in results:
        for device in result:
            devices.setdefault(device.device_id, device)
    return tuple(devices[key] for key in sorted(devices))


async def async_identify_device(host: str) -> str | None:
    """Read an endpoint's controller ID, optionally resolving an IPv4 hostname."""
    try:
        async with asyncio.timeout(3):
            try:
                address = str(IPv4Address(host))
            except ValueError:
                addresses = await asyncio.get_running_loop().getaddrinfo(
                    host, 4000, family=socket.AF_INET, type=socket.SOCK_DGRAM
                )
                if not addresses:
                    return None
                address = str(addresses[0][4][0])
            devices = await _async_discover(address=address, timeout=1.0)
            return next(
                (device.device_id for device in devices if device.host == address), None
            )
    except OSError, TimeoutError:
        return None
