import serial
import time
import sys
from typing import Union, Dict, List, Optional
from dataclasses import dataclass
from enum import IntFlag


# Define laser modes and flag bit masks
class LaserMode(IntFlag):
    OFF = 0
    REPETITION = 1 << 4  # 0x10 (16)
    BURST = 1 << 5  # 0x20 (32)
    EXTERNAL_TRIGGER = 1 << 6  # 0x40 (64)


class LaserFlags1(IntFlag):
    SHUTTER_OPEN = 1
    LASER_READY = 1 << 2
    LASER_ON = 1 << 3
    MODE_MASK = 0xF0  # Bits 4-7


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
        status_lines = [
            f"Laser Mode: {self.mode.name if self.mode else 'OFF'}",
            f"Shutter: {'OPEN' if self.flags1 & LaserFlags1.SHUTTER_OPEN else 'CLOSED'}",
            f"Laser Ready: {'YES' if self.flags1 & LaserFlags1.LASER_READY else 'NO'}",
            f"Laser On: {'YES' if self.flags1 & LaserFlags1.LASER_ON else 'NO'}",
            f"Supply Voltage: {self.supply_voltage:.1f}V",
            f"Temperature 1: {self.temp1:.1f}°C",
            f"Temperature 2: {self.temp2:.1f}°C",
            f"Energy: {self.energy:.2f}µJ",
        ]
        if self.quantity_preset is not None:
            status_lines.append(f"Quantity Preset: {self.quantity_preset}")
        if self.frequency_preset is not None:
            status_lines.append(f"Frequency Preset: {self.frequency_preset} Hz")
        if self.hv_value is not None:
            status_lines.append(f"HV Value: {self.hv_value}%")
        status_lines.extend(
            [
                f"Quantity Counter: {self.quantity_counter}",
                f"Shot Counter: {self.shot_counter}",
            ]
        )
        if self.flags4 or self.flags5:
            status_lines.append("\nWarnings/Errors:")
            for flag in LaserFlags4:
                if self.flags4 & flag:
                    status_lines.append(f"- {flag.name}")
            for flag in LaserFlags5:
                if self.flags5 & flag:
                    status_lines.append(f"- {flag.name}")
        return "\n".join(status_lines)


class LaserError(Exception):
    """Base exception for laser-related errors."""

    pass


class LaserProtocolError(LaserError):
    """Raised when there's an error in the communication protocol."""

    pass


class LTB:

    SC1 = "#"  # Start character for requests
    SC2 = "<"  # Start character for replies
    DA = "!"  # Destination address (default: 0x21)
    SA = "@"  # Source address (default: 0x40)
    EC = "\r"  # End character (CR, 0x0D)

    def __new__(cls, port: str, baudrate: int = 9600, timeout: int = 1):
        try:
            instance = super().__new__(cls)
            instance.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                stopbits=serial.STOPBITS_ONE,
                parity=serial.PARITY_NONE,
            )
            return instance
        except serial.SerialException:
            print("using virtual LTB LASER")
            from VirtualLTB import LTB as VirtualLTB

            return VirtualLTB(port)

    def __init__(self, port: str, baudrate: int = 9600, timeout: int = 1):
        # __init__ won't run if __new__ returns an instance of a different class.
        pass

    def _calculate_fcs(self, telegram: str) -> str:
        checksum = sum(ord(c) for c in telegram) % 256
        return f"{checksum:02X}"

    def _verify_fcs(self, telegram: str) -> bool:
        if len(telegram) < 4:
            return False
        received_fcs = telegram[-3:-1]
        message = telegram[:-3]
        calculated_fcs = self._calculate_fcs(message)
        return received_fcs == calculated_fcs

    def _construct_request(self, req_data_unit: str) -> str:
        telegram = f"{self.SC1}{self.DA}{self.SA}{req_data_unit}"
        fcs = self._calculate_fcs(telegram)
        return f"{telegram}{fcs}{self.EC}"

    def _send_command(
        self, req_data_unit: str, expect_reply: bool = False, retries: int = 3
    ) -> Union[str, dict]:
        for attempt in range(retries):
            try:
                telegram = self._construct_request(req_data_unit)
                self.ser.write(telegram.encode("ascii"))
                response = self.ser.read_until(self.EC.encode()).decode("ascii")
                if not response:
                    raise LaserProtocolError("No response received from laser")
                if response == self.EC and not expect_reply:
                    return {"status": "ACK"}
                if not self._verify_fcs(response):
                    raise LaserProtocolError("Invalid checksum in response")
                return self._parse_response(response)
            except LaserProtocolError as e:
                if attempt < retries - 1:
                    if "Forbidden" in str(e):
                        time.sleep(2)
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        f"{ts} - WARNING - Retrying command {req_data_unit}... Attempt {attempt + 1}"
                    )
                    continue
                raise
            except serial.SerialException as e:
                raise LaserError(f"Serial communication error: {e}")

    def _parse_response(self, response: str) -> Union[str, dict]:
        if response == self.EC:
            return {"status": "ACK"}
        if response.startswith(self.SC2):
            if len(response) < 7:
                raise LaserProtocolError("Reply telegram too short")
            da = response[1]
            sa = response[2]
            data = response[3:-3]
            if da != self.SA or sa != self.DA:
                raise LaserProtocolError("Invalid address in reply")
            return {"type": "Reply", "data": data}
        elif response.startswith("\x1B\x1B"):
            error_type = response[2] if len(response) > 2 else "Unknown"
            error_messages = {
                "1": "Checksum Error",
                "2": "Incorrect Format",
                "3": "Incorrect Parameter",
                "4": "Forbidden Error",
                "5": "Busy Error (previous command still processing)",
                "6": "TX Queue Full",
            }
            error_msg = error_messages.get(error_type, "Unknown Error")
            raise LaserProtocolError(f"Laser error: {error_msg}")
        raise LaserProtocolError(f"Unknown response format: {response}")

    def _parse_status(self) -> LaserStatus:
        # Get Stat7 response
        stat7 = self._send_command("UT", expect_reply=True)
        if stat7["type"] != "Reply" or not stat7["data"].startswith("UT"):
            raise LaserProtocolError("Invalid Stat7 response")
        stat7_data = stat7["data"][2:]
        if len(stat7_data) < 22:
            raise LaserProtocolError("Stat7 data length insufficient")
        flags1 = int(stat7_data[0:2], 16)
        quantity_preset = int(stat7_data[6:10], 16)
        frequency_preset = int(stat7_data[10:12], 16)
        hv_value = int(stat7_data[12:14], 16)
        # Get Stat8 response
        stat8 = self._send_command("UU", expect_reply=True)
        if stat8["type"] != "Reply" or not stat8["data"].startswith("UU"):
            raise LaserProtocolError("Invalid Stat8 response")
        stat8_data = stat8["data"][2:]
        if len(stat8_data) < 26:
            raise LaserProtocolError("Stat8 data length insufficient")
        flags4 = int(stat8_data[0:2], 16)
        flags5 = int(stat8_data[2:4], 16)
        supply_voltage = int(stat8_data[4:6], 16) * 0.11
        # According to the protocol, positions [6:8] are temp2 and [8:10] are temp1.
        temp2 = int(stat8_data[6:8], 16)
        temp1 = int(stat8_data[8:10], 16)
        # Energy value is given in 4 hex digits (positions 10:14).
        energy_avg_raw = int(stat8_data[10:14], 16)
        # The conversion per the protocol is:
        # Energy [µJ] = (energy_avg_raw / 64000) * 250
        # If energy_avg_raw is zero, energy will be 0. This may be expected
        # if the laser is not equipped with an energy monitor.
        energy = (energy_avg_raw / 64000.0) * 250
        quantity_counter = int(stat8_data[14:18], 16)
        shot_counter = int(stat8_data[18:26], 16)
        return LaserStatus(
            flags1=LaserFlags1(flags1),
            flags4=LaserFlags4(flags4),
            flags5=LaserFlags5(flags5),
            supply_voltage=supply_voltage,
            temp1=float(temp1),
            temp2=float(temp2),
            energy=energy,
            quantity_counter=quantity_counter,
            shot_counter=shot_counter,
            quantity_preset=quantity_preset,
            frequency_preset=frequency_preset,
            hv_value=hv_value,
        )

    def turn_laser_off(self) -> None:
        self._send_command("X")

    def turn_laser_on(self) -> None:
        self._send_command("g")
        start_time = time.time()
        while time.time() - start_time < 20:
            try:
                status = self.get_extended_status()
                if (
                    status.flags1 & LaserFlags1.LASER_READY
                    and status.flags1 & LaserFlags1.LASER_ON
                ):
                    return
                time.sleep(1)
            except LaserProtocolError:
                pass
        raise LaserError("Laser not ready after 20 seconds")

    def start_repetition_mode(self) -> None:
        status = self.get_extended_status()
        if status.mode != LaserMode.OFF:
            self.stop_operation()
            time.sleep(1)
        if not (status.flags1 & LaserFlags1.LASER_ON):
            raise LaserError("Laser not in STANDBY mode")
        self._send_command("h", retries=5)
        time.sleep(1)
        new_status = self.get_extended_status()
        if new_status.mode != LaserMode.REPETITION:
            raise LaserError("Failed to activate repetition mode")

    def start_burst_mode(self) -> None:
        self._send_command("j")

    def activate_external_trigger(self) -> None:
        self._send_command("u")

    def stop_operation(self) -> None:
        self._send_command("i")

    def set_quantity(self, quantity: int) -> None:
        if not 0 <= quantity <= 65535:
            raise ValueError("Quantity must be between 0 and 65535")
        self._send_command(f"l{quantity:04X}")

    def set_repetition_rate(self, rate: int) -> None:
        if not 0 <= rate <= 255:
            raise ValueError("Rate must be between 0 and 255")
        self._send_command(f"m{rate:02X}")

    def set_hv_voltage(self, percent: int) -> None:
        """
        You can change the energy output by varying the high voltage within a range from 80-100 %.
        In this case, this functions excpects an input between 0 and 100, which is probably then mapped to the range 80-100 %
        """
        if not 0 <= percent <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        self._send_command(f"n{percent:02X}")

    def set_shutter(self, open_shutter: bool) -> None:
        status = self.get_extended_status()
        if not (status.flags1 & LaserFlags1.LASER_READY):
            raise LaserError("Laser not ready for shutter operation")
        for attempt in range(3):
            try:
                self._send_command("z1" if open_shutter else "z0")
                return
            except LaserProtocolError as e:
                if "Forbidden" in str(e) and attempt < 2:
                    time.sleep(1)
                    continue
                raise

    def set_stepper_position(self, position: int) -> None:
        if not 0 <= position <= 399:
            raise ValueError("Position must be between 0 and 399")
        self._send_command(f"O3{position:04X}")

    def set_transmission(self, setpoint: int) -> None:
        if not 0 <= setpoint <= 200:
            raise ValueError("Setpoint must be between 0 and 200")
        self._send_command(f"O4{setpoint:02X}")

    def set_attenuation_energy(self, value: int) -> None:
        """
        This is probably not working when the laser is without an energy monitor.
        """
        if not 0 <= value <= 65535:
            raise ValueError("Energy value must be between 0 and 65535")
        self._send_command(f"O5{value:04X}")

    def init_attenuator(self) -> None:
        self._send_command("O60000")

    def reset_permanent_error(self) -> None:
        self._send_command("s")

    def get_short_status(self) -> Dict:
        response = self._send_command("W", expect_reply=True)
        if response["type"] != "Reply" or not response["data"].startswith("W"):
            raise LaserProtocolError("Invalid short status response")
        return {"flags": int(response["data"][1:3], 16)}

    def get_stat7(self) -> Dict:
        response = self._send_command("UT", expect_reply=True)
        if response["type"] != "Reply" or not response["data"].startswith("UT"):
            raise LaserProtocolError("Invalid Stat7 response")
        data = response["data"][2:]
        return {
            "flags1": int(data[0:2], 16),
            "flags2": int(data[2:4], 16),
            "flags3": int(data[4:6], 16),
            "quantity_preset": int(data[6:10], 16),
            "frequency_preset": int(data[10:12], 16),
            "hv_value": int(data[12:14], 16),
            "energy": int(data[18:22], 16),
        }

    def get_extended_status(self) -> LaserStatus:
        return self._parse_status()

    def get_version_info(self) -> Dict:
        response = self._send_command("V3", expect_reply=True)
        if response["type"] != "Reply" or not response["data"].startswith("V"):
            raise LaserProtocolError("Invalid version info response")
        data = response["data"][1:]
        return {
            "main_revision": int(data[0:2], 16),
            "release": int(data[2:4], 16),
            "type1": int(data[4:6], 16),
            "type2": int(data[6:8], 16),
            "version": data[8:16],
            "laser_type": data[17 : 17 + int(data[16:17])],
        }

    def get_serial_numbers(self) -> Dict:
        response = self._send_command("US", expect_reply=True)
        if response["type"] != "Reply" or not response["data"].startswith("US"):
            raise LaserProtocolError("Invalid serial numbers response")
        data = response["data"][2:]
        return {"laser_serial": data[0:8], "energy_monitor_serial": data[8:12]}

    def get_attenuator_status(self) -> Dict:
        response = self._send_command("UV", expect_reply=True)
        if response["type"] != "Reply" or not response["data"].startswith("UV"):
            raise LaserProtocolError("Invalid attenuator status response")
        data = response["data"][2:]
        return {
            "stepper_mode": int(data[0:2], 16),
            "set_position": int(data[2:6], 16),
            "actual_position": int(data[6:10], 16),
            "transmission": int(data[10:12], 16) / 2.0,
        }

    def get_energy_values(self) -> List[float]:
        response = self._send_command("P", expect_reply=True)
        if response["type"] != "Reply" or not response["data"].startswith("P"):
            raise LaserProtocolError("Invalid energy values response")
        data = response["data"][1:]
        stored_count = int(data[0:2], 16)
        value_count = int(data[2:4], 16)
        values = []
        for i in range(value_count):
            pos = 4 + i * 4
            raw_value = int(data[pos : pos + 4], 16)
            energy = (raw_value / 64000) * 250
            values.append(energy)
        return values

    def close(self) -> None:
        if hasattr(self, "ser") and self.ser.is_open:
            try:
                self.turn_laser_off()
            except LaserError:
                pass
            self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    LASER_PORT = "/dev/ttyUSB0"
    # high voltate, to set the output power
    HV_PERCENTAGE = 8
    REP_RATE = 10
    OPERATION_TIME = 60  # seconds

    try:
        with LTB(port=LASER_PORT) as laser:
            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Initializing laser..."
            )
            version = laser.get_version_info()
            serials = laser.get_serial_numbers()
            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Laser Type: {version['laser_type']}"
            )
            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Firmware Version: {version['version']}"
            )
            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Serial Number: {serials['laser_serial']}"
            )

            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Turning laser on...")
            laser.turn_laser_on()

            status = laser.get_extended_status()
            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Initial status:\n{status}"
            )

            if not (status.flags1 & LaserFlags1.LASER_ON):
                raise LaserError("Laser failed to enter STANDBY")

            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Setting HV voltage to {HV_PERCENTAGE}%..."
            )
            laser.set_hv_voltage(HV_PERCENTAGE)
            time.sleep(1)

            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Setting repetition rate to {REP_RATE} Hz..."
            )
            laser.set_repetition_rate(REP_RATE)
            time.sleep(1)

            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Starting repetition mode..."
            )
            try:
                laser.start_repetition_mode()
            except LaserError as e:
                current_status = laser.get_extended_status()
                print(
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ERROR - Failed to start repetition mode. Current status:\n{current_status}"
                )
                raise

            # Use ANSI escape sequences to update the status in-place.
            previous_lines = 0
            start_time = time.time()
            while time.time() - start_time < OPERATION_TIME:
                status = laser.get_extended_status()
                status_message = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Operation status:\n{status}"
                # Count how many lines the status message spans
                num_lines = status_message.count("\n") + 1
                if previous_lines:
                    # Move the cursor up by the number of previously printed lines
                    sys.stdout.write(f"\033[{previous_lines}A")
                # Print the new status message (this will overwrite the old status)
                print(status_message)
                previous_lines = num_lines
                time.sleep(1)

            print(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Stopping operation..."
            )
            # With the command LASER OFF, the beam path closes automatically, regardless of the chosen mode of operation.
            laser.stop_operation()

    except LaserError as e:
        print(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ERROR - Laser operation failed: {e}"
        )
    except KeyboardInterrupt:
        print(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Operation interrupted by user"
        )
    except Exception as e:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ERROR - Unexpected error: {e}")
    finally:
        print(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - INFO - Operation completed. Laser shut down."
        )
