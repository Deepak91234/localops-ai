import asyncio
import os
import platform
import subprocess
import time
from ..models import utc_now


class DeviceTelemetry:
    def __init__(self):
        self.cache = None
        self.cache_time = 0.0

    @staticmethod
    def _number(value):
        try:
            return float(value.strip())
        except ValueError:
            return None

    @staticmethod
    def read_device():
        sample = {"timestamp": utc_now(), "scope": "device-level", "gpu_name": None, "gpu_utilization_percent": None, "gpu_memory_used_mb": None, "gpu_memory_total_mb": None, "temperature_c": None, "power_w": None, "available": False, "note": "Unavailable. No per-agent GPU allocations are inferred."}
        try:
            proc = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3, check=True)
            fields = proc.stdout.strip().splitlines()[0].split(",")
            if len(fields) == 6:
                sample.update(gpu_name=fields[0].strip(), gpu_utilization_percent=DeviceTelemetry._number(fields[1]), gpu_memory_used_mb=DeviceTelemetry._number(fields[2]), gpu_memory_total_mb=DeviceTelemetry._number(fields[3]), temperature_c=DeviceTelemetry._number(fields[4]), power_w=DeviceTelemetry._number(fields[5]), available=True, note="NVIDIA tooling, device-level. Unified-memory GPU memory may be unavailable; null means unavailable. Job figures report latency and tokens only.")
        except (OSError, subprocess.SubprocessError, IndexError):
            pass
        return sample

    async def sample(self):
        if self.cache is None or time.monotonic() - self.cache_time > 3:
            self.cache = await asyncio.to_thread(self.read_device)
            self.cache_time = time.monotonic()
        return self.cache


def machine_identity():
    total = None
    available = None
    try:
        memory = {}
        with open("/proc/meminfo") as source:
            for line in source:
                key, value = line.split(":", 1)
                memory[key] = int(value.strip().split()[0]) * 1024
        total, available = memory.get("MemTotal"), memory.get("MemAvailable")
    except (OSError, ValueError):
        pass
    return {"hostname": platform.node(), "os": platform.platform(), "architecture": platform.machine(), "ram_total_bytes": total, "ram_available_bytes": available, "python": platform.python_version()}
