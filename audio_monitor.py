import math
import numpy as np
import pyaudiowpatch as pyaudio


class AudioProcessor:
    def __init__(self, gain=3.0, threshold=4.0):
        self.global_gain = gain
        self.base_threshold = threshold
        self.p = pyaudio.PyAudio()
        self.CHUNK = 1024
        self.stream = None
        self.freq_resolution = 0

    def get_device_list(self):
        """获取所有可用输入设备"""
        devices = []
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            for i in range(self.p.get_device_count()):
                dev = self.p.get_device_info_by_index(i)
                if dev["hostApi"] == wasapi_info["index"] and dev["maxInputChannels"] > 0:
                    devices.append({
                        "index": i,
                        "name": dev["name"],
                        "is_loopback": dev["isLoopbackDevice"]
                    })
        except:
            pass
        return devices

    def open_stream(self, device_index):
        dev_info = self.p.get_device_info_by_index(device_index)
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=dev_info["maxInputChannels"],
            rate=int(dev_info["defaultSampleRate"]),
            frames_per_buffer=self.CHUNK,
            input=True,
            input_device_index=device_index
        )
        self.freq_resolution = int(dev_info["defaultSampleRate"]) / self.CHUNK
        return True

    def close_stream(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None

    def get_audio_frame(self):
        if not self.stream: return [0] * 6
        try:
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            data_np = np.frombuffer(data, dtype=np.int16)
            if len(data_np) % 2 == 0:
                data_np = np.mean(data_np.reshape(-1, 2), axis=1)

            fft_data = np.abs(np.fft.rfft(data_np * np.hanning(len(data_np))))[1:]
            levels = []
            bands = [150, 400, 1000, 2500, 6000, 20000]
            gains = [1.0, 1.2, 1.5, 2.0, 3.0, 4.0]

            start_idx = 0
            for i, limit in enumerate(bands):
                end_idx = min(int(limit / self.freq_resolution), len(fft_data))
                energy = np.max(fft_data[start_idx:end_idx]) if start_idx < end_idx else 0
                start_idx = end_idx

                weighted = energy * gains[i]
                if weighted < 10:
                    lvl = 0
                else:
                    log_val = math.log10(weighted)
                    lvl = int(
                        (log_val - self.base_threshold) * self.global_gain) if log_val > self.base_threshold else 0
                levels.append(max(0, min(10, lvl)))
            return levels
        except:
            return [0] * 6

    def terminate(self):
        self.close_stream()
        self.p.terminate()