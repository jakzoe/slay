from typing import Union, Dict, List, Optional
from dataclasses import dataclass
from enum import IntFlag


class LaserMode(IntFlag):
    OFF = 0
    REPETITION = 1 << 4
    BURST = 1 << 5
    EXTERNAL_TRIGGER = 1 << 6


class LaserFlags1(IntFlag):
    SHUTTER_OPEN = 1
    LASER_READY = 1 << 2
    LASER_ON = 1 << 3
    MODE_MASK = 0xF0


class LaserFlags4(IntFlag):
    STATIC_ERROR = 1
    ENCLOSURE_OPEN = 1 << 1
    REMOTE_INTERLOCK_OPEN = 1 << 2
    TEMPERATURE_LIMIT = 1 << 3
    TEMP_WARNING1 = 1 << 4
    TEMP_WARNING2 = 1 << 5
    PEM_ERROR = 1 << 6


class LaserFlags5(IntFlag):
    OPERATION_ERROR = 1
    HV_SUPPLY_ERROR = 1 << 3
    TEMP_ERROR1 = 1 << 4
    TEMP_ERROR2 = 1 << 5
    POWER_SWITCH_ERROR = 1 << 6
    POWER_SUPPLY_WEAK = 1 << 7


@dataclass
class LaserStatus:
    flags1: LaserFlags1
    flags4: LaserFlags4
    flags5: LaserFlags5
    supply_voltage: float
    temp1: float
    temp2: float
    energy: float
    quantity_counter: int
    shot_counter: int
    quantity_preset: Optional[int] = None
    frequency_preset: Optional[int] = None
    hv_value: Optional[int] = None

    @property
    def mode(self) -> LaserMode:
        return LaserMode(self.flags1 & LaserFlags1.MODE_MASK)

    def __str__(self) -> str:
        return "Fake LaserStatus"


class LaserError(Exception):
    pass


class LaserProtocolError(LaserError):
    pass


class LTB:
    SC1 = "#"  # Start character for requests
    SC2 = "<"  # Start character for replies
    DA = "!"  # Destination address
    SA = "@"  # Source address
    EC = "\r"  # End character

    def __init__(self, port: str, baudrate: int = 9600, timeout: int = 1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def _calculate_fcs(self, telegram: str) -> str:
        return "00"

    def _verify_fcs(self, telegram: str) -> bool:
        return True

    def _construct_request(self, req_data_unit: str) -> str:
        return ""

    def _send_command(
        self, req_data_unit: str, expect_reply: bool = False, retries: int = 3
    ) -> Union[str, dict]:
        if expect_reply:
            return {"type": "Reply", "data": req_data_unit}
        return {"status": "ACK"}

    def _parse_response(self, response: str) -> Union[str, dict]:
        return {}

    def _parse_status(self) -> LaserStatus:
        return LaserStatus(
            flags1=LaserFlags1(0),
            flags4=LaserFlags4(0),
            flags5=LaserFlags5(0),
            supply_voltage=0.0,
            temp1=0.0,
            temp2=0.0,
            energy=0.0,
            quantity_counter=0,
            shot_counter=0,
        )

    def turn_laser_off(self) -> None:
        pass

    def turn_laser_on(self) -> None:
        pass

    def start_repetition_mode(self) -> None:
        pass

    def start_burst_mode(self) -> None:
        pass

    def activate_external_trigger(self) -> None:
        pass

    def stop_operation(self) -> None:
        pass

    def set_quantity(self, quantity: int) -> None:
        pass

    def set_repetition_rate(self, rate: int) -> None:
        pass

    def set_hv_voltage(self, percent: int) -> None:
        pass

    def set_shutter(self, open_shutter: bool) -> None:
        pass

    def set_stepper_position(self, position: int) -> None:
        pass

    def set_transmission(self, setpoint: int) -> None:
        pass

    def set_attenuation_energy(self, value: int) -> None:
        pass

    def init_attenuator(self) -> None:
        pass

    def reset_permanent_error(self) -> None:
        pass

    def get_short_status(self) -> Dict:
        return 0

    def get_stat7(self) -> Dict:
        return 0

    def get_extended_status(self) -> LaserStatus:
        return self._parse_status()

    def get_version_info(self) -> Dict:
        return 0

    def get_serial_numbers(self) -> Dict:
        return 0

    def get_attenuator_status(self) -> Dict:
        return 0

    def get_energy_values(self) -> List[float]:
        return 0

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
