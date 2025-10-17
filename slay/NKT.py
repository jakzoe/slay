# das noch mal mit prints überprüfen
# try:
#     from pylablib.devices import NKT
# except ModuleNotFoundError:
#     from VirtualNKT import NKT

from pylablib.devices import NKT

# from VirtualNKT import NKT


class LaserController:

    def __init__(self, laser_path):
        """
        Initializes the LaserController with a laser instance.
        :param laser: An instance providing `ib_set_reg` and `ib_get_reg` methods.
        """
        self.laser = NKT.GenericInterbusDevice(laser_path)
        # try:
        #     self.laser = NKT.GenericInterbusDevice(laser_path)
        # except Exception:  # InterbusBackendError:
        #     from virtual_nkt import NKT
        #     self.laser = NKT.GenericInterbusDevice(laser_path)
        #     print("using virtual NKT LASER")

        self.laser_register = 1
        # 1/Faktor zur Basiseinheit
        self.registers = {
            "emission": {"addr": 0x30, "type": "u8", "mode": "w"},
            "power": {"addr": 0x3E, "type": "u8", "mode": "w"},
            "temperature": {"addr": 0x1B, "type": "i16", "factor": 10, "mode": "r"},
            "trig_level": {"addr": 0x24, "type": "u16", "factor": 1000, "mode": "r"},
            "display_backlight": {"addr": 0x26, "type": "u16", "mode": "w"},
            "operating_mode": {"addr": 0x31, "type": "u8", "mode": "w"},
            "interlock_status": {"addr": 0x32, "type": "u16", "mode": "rw"},
            "pulse_frequency": {"addr": 0x33, "type": "u32", "mode": "w"},
            "pulses_per_burst": {"addr": 0x34, "type": "u16", "mode": "w"},
            "watchdog_interval": {"addr": 0x35, "type": "u8", "mode": "w"},
            "max_frequency": {"addr": 0x36, "type": "u32", "mode": "r"},
            "status_bits": {"addr": 0x66, "type": "u16", "mode": "r"},
            "optical_frequency": {"addr": 0x71, "type": "u32", "mode": "r"},
            "actual_frequency": {
                "addr": 0x75,
                "type": "u32",
                "factor": 100,
                "mode": "r",
            },
            "display_text": {"addr": 0x78, "type": "ascii", "mode": "r"},
            "calculated_power": {"addr": 0x7A, "type": "u8", "mode": "r"},
            "user_area": {"addr": 0x8D, "type": "ascii", "mode": "w"},
            "voltage": {"addr": 0x1A, "type": "u16", "factor": 1000, "mode": "r"},
        }

    def set_register(self, name, value):

        print(f"set {name} to {value}")

        if name not in self.registers:
            raise ValueError(f"Unknown register: {name}")
        reg = self.registers[name]
        # if self.get_register(name) == value:
        if "w" not in reg["mode"]:
            print("NKT: Could not set register, read only")
            return
        self.laser.ib_set_reg(self.laser_register, reg["addr"], value, reg["type"])

    def get_register(self, name):
        if name not in self.registers:
            raise ValueError(f"Unknown register: {name}")
        reg = self.registers[name]
        if "r" not in reg["mode"]:
            return "ERROR: Write only"
        if "factor" in reg:
            return (
                self.laser.ib_get_reg(self.laser_register, reg["addr"], reg["type"])
                / reg["factor"]
            )
        return self.laser.ib_get_reg(self.laser_register, reg["addr"], reg["type"])
