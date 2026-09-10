import asyncio
from typing import Any, Awaitable, Callable, List, Optional

from homeassistant.components.climate import (
    HVACAction,
    HVACMode,
)
from homeassistant.exceptions import HomeAssistantError
from pymodbus.client import AsyncModbusTcpClient

from .const import *
from .models import (
    ALARM_STATES,
    FILTER_STATES,
)


def _parse_firmware_version(firmware_info: List[int]) -> str:
    major, minor = firmware_info[0].to_bytes(2, "big")

    day, month = firmware_info[1].to_bytes(2, "big")
    year: int = firmware_info[2]

    return f"{major}.{minor} ({year}-{month:02d}-{day:02d})"


def _to_signed_16bit(value: int) -> int:
    return value - 0x10000 if value > 0x7FFF else value

def _parse_min_hours_days_to_min(datetime_info: List[int]) -> int:
    hours, minutes = datetime_info[0].to_bytes(2, "big")
    days: int = datetime_info[1]
    total_minutes = days * 1440 + hours * 60 + minutes

    return total_minutes

class S21Client:
    def __init__(self, host: str, port: int = 502):
        self.host = host
        self.port = port
        self.client = AsyncModbusTcpClient(host=self.host, port=self.port)
        self.data = {}
        self.lock = asyncio.Lock()

    async def poll(self) -> dict:
        return await self._do_with_connection(self._poll)

    async def turn_on(self) -> None:
        await self._do_with_connection(self._turn_on)

    async def turn_off(self) -> None:
        await self._do_with_connection(self._turn_off)

    async def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._do_with_connection(lambda: self._set_hvac_mode(hvac_mode))

    async def set_fan_mode(self, mode: int) -> None:
        self._validate_fan_mode(mode)
        await self._do_with_connection(lambda: self._set_fan_mode(mode))

    async def set_manual_fan_speed_percent(self, speed_percent: int) -> None:
        self._validate_manual_fan_speed_percent(speed_percent)
        await self._do_with_connection(
            lambda: self._set_manual_fan_speed_percent(speed_percent)
        )

    async def set_temperature(self, temp_celsius: int) -> None:
        self._validate_temperature(temp_celsius)
        await self._do_with_connection(lambda: self._set_temperature(temp_celsius))

    async def reset_filter_change_timer(self) -> None:
        await self._do_with_connection(self._reset_filter_change_timer)

    async def reset_alarm(self) -> None:
        await self._do_with_connection(self._reset_alarm)

    async def boost_on(self) -> None:
        await self._do_with_connection(self._set_boost_on)

    async def boost_off(self) -> None:
        await self._do_with_connection(self._set_boost_off)

    @staticmethod
    def _validate_modbus_response(response: Any, operation: str) -> Any:
        if response is None:
            raise HomeAssistantError(f"Modbus {operation} failed: empty response")

        is_error = getattr(response, "isError", None)
        if callable(is_error) and response.isError():
            raise HomeAssistantError(
                f"Modbus {operation} failed: {response!r}"
            )

        return response

    def _get_registers(self, response: Any, count: int, operation: str) -> List[int]:
        registers = getattr(self._validate_modbus_response(response, operation), "registers", None)
        if not isinstance(registers, list) or len(registers) < count:
            raise HomeAssistantError(
                f"Modbus {operation} failed: expected {count} registers"
            )
        return registers

    def _get_bits(self, response: Any, count: int, operation: str) -> List[bool]:
        bits = getattr(self._validate_modbus_response(response, operation), "bits", None)
        if not isinstance(bits, list) or len(bits) < count:
            raise HomeAssistantError(
                f"Modbus {operation} failed: expected {count} coil bits"
            )
        return bits

    @staticmethod
    def _validate_fan_mode(mode: int) -> None:
        if not isinstance(mode, int) or mode not in (1, 2, 3, 4, 5, 255):
            raise ValueError("Fan mode must be one of: 1, 2, 3, 4, 5, 255")

    @staticmethod
    def _validate_manual_fan_speed_percent(speed_percent: int) -> None:
        if not isinstance(speed_percent, int) or not 0 <= speed_percent <= 100:
            raise ValueError("Manual fan speed percent must be between 0 and 100")

    @staticmethod
    def _validate_temperature(temp_celsius: int) -> None:
        if not isinstance(temp_celsius, int) or not 15 <= temp_celsius <= 30:
            raise ValueError("Temperature must be between 15 and 30 °C")

    async def _read_input_registers(self, address: int, count: int) -> List[int]:
        response = await self.client.read_input_registers(address, count=count)
        return self._get_registers(response, count, f"read input registers at {address}")

    async def _read_holding_registers(self, address: int, count: int) -> List[int]:
        response = await self.client.read_holding_registers(address, count=count)
        return self._get_registers(response, count, f"read holding registers at {address}")

    async def _read_coils(self, address: int, count: int) -> List[bool]:
        response = await self.client.read_coils(address, count=count)
        return self._get_bits(response, count, f"read coils at {address}")

    async def _write_register(self, address: int, value: int) -> None:
        response = await self.client.write_register(address, value)
        self._validate_modbus_response(response, f"write register {address}")

    async def _write_coil(self, address: int, value: bool) -> None:
        response = await self.client.write_coil(address, value)
        self._validate_modbus_response(response, f"write coil {address}")

    async def _do_with_connection(self, func: Callable[[], Awaitable[Any]]) -> Any:
        async with self.lock:  # Device does not support multiple connections
            if not await self.client.connect():
                raise HomeAssistantError("Modbus: Failed to open Modbus TCP connection")

            try:
                return await func()
            except Exception:
                self.data["available"] = False
                raise
            finally:
                self.client.close()  # Also, long connections break over time and become unusable

    async def _poll(self) -> dict:
        if (await self._read_input_registers(IR_DeviceTYPE, count=1))[0] != 1:
            raise HomeAssistantError("Modbus: Unsupported device (IR_DeviceTYPE != 1)")

        coils = await self._read_coils(0, count=4)
        holding_registers = await self._read_holding_registers(0, count=45)
        input_registers = await self._read_input_registers(0, count=54)

        is_on: bool = coils[CL_POWER]
        is_boosting: bool = coils[CL_Boost_MODE]
        current_humidity: int = input_registers[IR_CurRH_Int]
        filter_state: int = input_registers[IR_StateFILTER]
        alarm_state: int = input_registers[IR_ALARM]
        max_fan_level: int = holding_registers[HR_MaxSPEED_MODE]
        current_fan_level: int = holding_registers[HR_SPEED_MODE]  # 255 - manual
        temp_before_heating_x10: int = _to_signed_16bit(
            input_registers[IR_CurTEMP_SuAirIn]
        )
        temp_after_heating_x10: int = _to_signed_16bit(
            input_registers[IR_CurTEMP_SuAirOut]
        )
        temp_extract_air_x10: int = _to_signed_16bit(
            input_registers[IR_CurTEMP_ExAirIn]
        )
        temp_exhaust_air_x10: int = _to_signed_16bit(
            input_registers[IR_CurTEMP_ExAirOut]
        )
        target_temperature: int = holding_registers[HR_SetTEMP]
        supply_airflow: int = input_registers[IR_CurSuAirFLOW]
        extract_airflow: int = input_registers[IR_CurExAirFLOW]
        supply_pressure: int = input_registers[IR_CurSuPRESS]
        extract_pressure: int = input_registers[IR_CurExPRESS]
        filter_countdown_days: int = input_registers[IR_CurFILTER_TIMER_DAYS]
        supply_fan_speed: int = input_registers[IR_SuRPM]
        extract_fan_speed: int = input_registers[IR_ExRPM]
        supply_fan_state: int = input_registers[IR_CurSuFanSpeed]
        extract_fan_state: int = input_registers[IR_CurExFanSpeed]
        firmware_info: List[int] = input_registers[
            IR_VerMAIN_FMW_start : IR_VerMAIN_FMW_end + 1
        ]
        operation_mode: int = holding_registers[HR_OPERATION_MODE]
        manual_fan_speed_percent: int = holding_registers[HR_ManualSPEED]
        engine_running_time: List[int] = input_registers[
            IR_TotalWorkingTime_HOURS_MINUTES : IR_TotalWorkingTime_DAYS + 1
        ]
        bypass_state: int = input_registers[IR_StatusBpsRotor]
        self.data = {
            "available": True,
            "manufacturer": "Blauberg",
            "model": "S21",
            "sw_version": _parse_firmware_version(firmware_info),
            "name": "Blauberg S21",
            "unique_id": f"S21_{self.host}_{self.port}",
            "precision": 1,
            "current_supply_temperature": temp_after_heating_x10 / 10,
            "current_intake_temperature": temp_before_heating_x10 / 10,
            "current_extract_temperature": temp_extract_air_x10 / 10,
            "current_exhaust_temperature": temp_exhaust_air_x10 / 10,
            "target_temperature": target_temperature,
            "target_temperature_step": 1,
            "min_temp": 15,
            "max_temp": 30,
            "supply_airflow": supply_airflow,
            "extract_airflow": extract_airflow,
            "supply_pressure": supply_pressure,
            "extract_pressure": extract_pressure,
            "current_humidity": None if current_humidity == 0 else current_humidity,
            "is_on": is_on,
            "is_boosting": is_boosting,
            "supply_fan_speed": supply_fan_speed,
            "extract_fan_speed": extract_fan_speed,
            "supply_fan_state": supply_fan_state,
            "extract_fan_state": extract_fan_state,
            "manual_fan_speed_percent": manual_fan_speed_percent,
            "max_fan_level": max_fan_level,
            "engine_running_time": _parse_min_hours_days_to_min(engine_running_time),
            "bypass_state": bypass_state,
            "filter_state": FILTER_STATES[filter_state],
            "filter_countdown_days": filter_countdown_days,
            "alarm_state": ALARM_STATES[alarm_state],
            "fan_mode": current_fan_level,
            "fan_modes": [x + 1 for x in range(max_fan_level)] + [255],
        }
        if not is_on:
            self.data["hvac_mode"] = HVACMode.OFF
            self.data["hvac_action"] = HVACAction.OFF
        elif operation_mode == 0:
            self.data["hvac_mode"] = HVACMode.FAN_ONLY
            self.data["hvac_action"] = HVACAction.FAN
        elif operation_mode == 1:
            self.data["hvac_mode"] = HVACMode.HEAT
            self.data["hvac_action"] = HVACAction.HEATING
        elif operation_mode == 2:
            self.data["hvac_mode"] = HVACMode.COOL
            self.data["hvac_action"] = HVACAction.COOLING
        else:
            self.data["hvac_mode"] = HVACMode.AUTO
            if temp_before_heating_x10 < temp_after_heating_x10:
                self.data["hvac_action"] = HVACAction.HEATING
            elif temp_before_heating_x10 > temp_after_heating_x10:
                self.data["hvac_action"] = HVACAction.COOLING
            else:
                self.data["hvac_action"] = HVACAction.IDLE

        return self.data

    async def _turn_on(self) -> None:
        await self._write_coil(CL_POWER, True)

    async def _turn_off(self) -> None:
        await self._write_coil(CL_POWER, False)

    async def _set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._turn_off()
        elif hvac_mode == HVACMode.FAN_ONLY:
            await self._turn_on()
            await self._write_register(HR_OPERATION_MODE, 0)
        elif hvac_mode == HVACMode.HEAT:
            await self._turn_on()
            await self._write_register(HR_OPERATION_MODE, 1)
        elif hvac_mode == HVACMode.COOL:
            await self._turn_on()
            await self._write_register(HR_OPERATION_MODE, 2)
        else:
            await self._turn_on()
            await self._write_register(HR_OPERATION_MODE, 3)

    async def _set_fan_mode(self, mode: int) -> None:
        await self._write_register(HR_SPEED_MODE, mode)

    async def _set_manual_fan_speed_percent(self, speed_percent: int) -> None:
        await self._write_register(HR_ManualSPEED, speed_percent)

    async def _set_temperature(self, temp_celsius: int) -> None:
        await self._write_register(HR_SetTEMP, temp_celsius)

    async def _reset_filter_change_timer(self) -> None:
        await self._write_coil(CL_RESET_FILTER_TIMER, True)

    async def _reset_alarm(self) -> None:
        await self._write_coil(CL_RESET_ALARM, True)

    async def _set_boost_on(self) -> None:
        await self._write_coil(CL_BoostSWITCH_CTRL, True)

    async def _set_boost_off(self) -> None:
        await self._write_coil(CL_BoostSWITCH_CTRL, False)
