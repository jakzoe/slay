# from slay.measurement import Measurement
# from slay.measurement import SpectrumData
import time


class BackupService:

    def __init__(self, measurement_manager, messdata, cache_dir: str):
        self.measurement_manager = measurement_manager
        self.messdata = messdata
        self.past_measurement_index = -1
        self.last_save_time = -1
        self.cache_dir = cache_dir
        # aktuell schreibe ich jedes Mal einfach den kompletten Array neu, statt nur zu appenden.
        # das könnte bei größeren Messungen zu delays führen, da es aktuell nur ein Thread, kein Prozess ist...
        self.max_save_interval = max(
            30, self.measurement_manager.MEASUREMENT_SETTINGS.measurement_time / 1000
        )

    def start(self):

        self.last_save_time = time.time()
        while True:
            if self.messdata.stop_event.is_set():
                return

            if (
                len(self.messdata.measurements) == 0
                or self.messdata.curr_measurement_index < 0
                or self.past_measurement_index == self.messdata.curr_measurement_index
                or self.last_save_time + self.max_save_interval > time.time()
            ):
                time.sleep(self.max_save_interval / 2)
                continue

            self.measurement_manager.save(
                measurements_only=True, plt_only=False, cache_path=self.cache_dir
            )

            self.past_measurement_index = self.messdata.curr_measurement_index
            self.last_save_time = time.time()
