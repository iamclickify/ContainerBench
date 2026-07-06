import json
import os
import platform
import subprocess
from pathlib import Path
from benchmark.config import SYSTEM_ENV_PATH


def get_cpu_model() -> str:
    """Returns the CPU Model name in a cross-platform manner."""
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run(
                'reg query "HKLM\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0" /v ProcessorNameString',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "ProcessorNameString" in line:
                        return line.split("REG_SZ")[-1].strip()
        except Exception:
            pass
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    elif system == "Darwin":
        try:
            result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"


def get_total_ram() -> str:
    """Returns total system RAM formatted in GB/MB."""
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run("wmic OS get TotalVisibleMemorySize /Value", shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "TotalVisibleMemorySize" in line:
                        parts = line.split("=")
                        if len(parts) > 1:
                            kb = int(parts[1].strip())
                            return f"{round(kb / (1024 * 1024), 2)} GB"
        except Exception:
            pass
    elif system == "Linux":
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        return f"{round(kb / (1024 * 1024), 2)} GB"
        except Exception:
            pass
    elif system == "Darwin":
        try:
            result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            if result.returncode == 0:
                bytes_val = int(result.stdout.strip())
                return f"{round(bytes_val / (1024 * 1024 * 1024), 2)} GB"
        except Exception:
            pass
    return "Unknown RAM"


def get_docker_version() -> str:
    """Gets the Docker client/server version string."""
    try:
        result = subprocess.run("docker --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().replace("Docker version ", "")
    except Exception:
        pass
    return "Unknown Docker"


def collect_environment() -> None:
    """Collects system environment information and saves it once to environment.json."""
    env_path = Path(SYSTEM_ENV_PATH)
    if env_path.exists():
        return

    env_info = {
        "operating_system": f"{platform.system()} {platform.release()} ({platform.version()})",
        "python_version": platform.python_version(),
        "docker_version": get_docker_version(),
        "cpu_model": get_cpu_model(),
        "cpu_core_count": os.cpu_count() or 0,
        "total_ram": get_total_ram()
    }

    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        with open(env_path, "w", encoding="utf-8") as f:
            json.dump(env_info, f, indent=4)
    except Exception:
        pass
