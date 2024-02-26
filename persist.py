import sys
import machine
import uctypes

RTC_ADDR = 0x50000200
RTC_MEM_SIZE = 2048
MAGIC = 0x19620101

persist_data_def = {
    "magic":            0 | uctypes.UINT32,
    "counter":          4 | uctypes.UINT32,
    "prev_runtime":     8 | uctypes.UINT32
}

class Persist:
    def __init__(self):
        self.data = uctypes.struct(RTC_ADDR, persist_data_def)
        if self.data.magic != MAGIC:
            self.data.magic = MAGIC
            self.data.counter = 0
            self.data.prev_runtime = 0
            
    #@property and @counter.setter not supported in upython
    def get_counter(self):
        return self.data.counter

    def set_counter(self, value):
        self.data.counter = value

    def get_prev_runtime(self):
        return self.data.prev_runtime

    def set_prev_runtime(self, value):
        self.data.prev_runtime = value
    