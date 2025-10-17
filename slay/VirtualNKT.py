class NKT:
    @staticmethod
    def GenericInterbusDevice(laser_path):
        return NKT()

    def ib_set_reg(self, laser_register, addr, value, val_type):
        pass

    def ib_get_reg(self, laser_register, addr, val_type):
        return 0
