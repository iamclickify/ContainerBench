import subprocess
import json
import time
import urllib.request
import urllib.error
import shutil


def build_image(command: str) -> subprocess.CompletedProcess:
    """Executes a docker build command and returns the CompletedProcess result."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    return result


def get_image_size(image_tag: str) -> float:
    """Inspects a docker image to retrieve its size in Megabytes (MB)."""
    result = subprocess.run(
        f"docker image inspect {image_tag}",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return 0.0
    try:
        data = json.loads(result.stdout)
        if isinstance(data, list) and len(data) > 0:
            size_in_bytes = data[0].get("Size", 0)
            return round(size_in_bytes / (1024 * 1024), 2)
    except Exception:
        pass
    return 0.0


def get_layer_count(image_tag: str) -> int:
    """Retrieves the layer count of a Docker image."""
    result = subprocess.run(
        f"docker image inspect {image_tag}",
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"docker image inspect failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    if isinstance(data, list) and len(data) > 0:
        root_fs = data[0].get("RootFS", {})
        layers = root_fs.get("Layers", [])
        return len(layers)
    raise Exception("Invalid image inspect data format")


def measure_startup_time(image_tag: str, timeout: float = 15.0) -> float:
    """Runs the container with -P, performs a 4-stage verification flow,
    and measures startup time in seconds.
    """
    # 1. Inspect image to get exposed port
    inspect_result = subprocess.run(
        f"docker image inspect {image_tag}",
        shell=True,
        capture_output=True,
        text=True
    )
    if inspect_result.returncode != 0:
        raise Exception("Failed to inspect image for exposed ports")
        
    inspect_data = json.loads(inspect_result.stdout)
    exposed_port = 3000
    if isinstance(inspect_data, list) and len(inspect_data) > 0:
        ports = inspect_data[0].get("Config", {}).get("ExposedPorts", {})
        if ports:
            for port_key in ports.keys():
                try:
                    exposed_port = int(port_key.split("/")[0])
                    break
                except ValueError:
                    pass

    container_id = f"containerbench-temp-{int(time.time())}"
    
    # Start container publishing all ports (-P flag)
    run_cmd = f'docker run -d -P --name {container_id} {image_tag}'
    run_result = subprocess.run(run_cmd, shell=True, capture_output=True, text=True)
    if run_result.returncode != 0:
        raise Exception(f"docker run failed. Stdout: {run_result.stdout.strip()}. Stderr: {run_result.stderr.strip()}")

    # Capture actual container ID/hash from stdout
    actual_container_id = run_result.stdout.strip()

    try:
        # Stage 1: Wait 2 seconds and check if container is running
        time.sleep(2.0)
        
        inspect_res = subprocess.run(f"docker inspect {actual_container_id}", shell=True, capture_output=True, text=True)
        if inspect_res.returncode != 0:
            raise Exception(f"docker inspect failed: {inspect_res.stderr.strip()}")
            
        inspect_info = json.loads(inspect_res.stdout)
        if not isinstance(inspect_info, list) or len(inspect_info) == 0:
            raise Exception("docker inspect returned empty/invalid list output")
            
        state_dict = inspect_info[0].get("State", {})
        running = state_dict.get("Running", False)
        
        # Diagnostic prints as requested
        print(f"State.Running value: {running}")
        print(f"Type: {type(running)}")
        
        if not running:
            raise Exception("Stage 1 failed: Container not running after 2 seconds delay.")

        # Get published dynamic port
        port_cmd = f"docker port {actual_container_id} {exposed_port}"
        port_result = subprocess.run(port_cmd, shell=True, capture_output=True, text=True)
        if port_result.returncode != 0 or not port_result.stdout.strip():
            raise Exception(f"Failed to retrieve dynamic port mapping for port {exposed_port}")
            
        port_line = port_result.stdout.strip().splitlines()[0]
        host_port = int(port_line.split(":")[-1])
        
        # Stage 2 & 3: Polling loop
        start_time = time.perf_counter()
        ready = False
        
        while time.perf_counter() - start_time < timeout:
            # Check if container died using JSON parsing
            state_res = subprocess.run(f"docker inspect {actual_container_id}", shell=True, capture_output=True, text=True)
            if state_res.returncode == 0:
                state_info = json.loads(state_res.stdout)
                if isinstance(state_info, list) and len(state_info) > 0:
                    st_dict = state_info[0].get("State", {})
                    status_str = st_dict.get("Status", "").lower()
                    running_state = st_dict.get("Running", False)
                    if status_str in ["exited", "dead"] or not running_state:
                        raise Exception(f"Container exited unexpectedly. Status: {status_str}, Running: {running_state}")
                
            try:
                # Attempt HTTP request
                req = urllib.request.Request(f"http://localhost:{host_port}/")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    # Connection succeeded (2xx)
                    ready = True
                    break
            except urllib.error.HTTPError as e:
                # Any HTTP response indicates server is alive and responding (Stage 3)
                ready = True
                break
            except urllib.error.URLError:
                # Connection refused / not ready yet, sleep and retry (Stage 4)
                time.sleep(1.0)
            except Exception:
                # Other transient socket errors, sleep and retry (Stage 4)
                time.sleep(1.0)
                
        elapsed = round(time.perf_counter() - start_time, 3)
        if not ready:
            raise Exception("Stage 2/3 timeout: Startup poll timed out after 15 seconds")
        return elapsed

    except Exception as e:
        # Stage 4 / Debug: Compile comprehensive log details on failure
        inspect_res = subprocess.run(f"docker inspect {actual_container_id}", shell=True, capture_output=True, text=True)
        ps_res = subprocess.run("docker ps", shell=True, capture_output=True, text=True)
        port_map_res = subprocess.run(f"docker port {actual_container_id}", shell=True, capture_output=True, text=True)
        logs_res = subprocess.run(f"docker logs {actual_container_id}", shell=True, capture_output=True, text=True)
        
        debug_info = (
            f"\n=== DEBUG LOGS ===\n"
            f"Container ID   : {actual_container_id}\n"
            f"Port Mapping   : {port_map_res.stdout.strip()}\n"
            f"Inspect Status : {inspect_res.stdout.strip()[:1000]}\n"
            f"docker ps      : {ps_res.stdout.strip()[:1000]}\n"
            f"Container Logs : {(logs_res.stdout + logs_res.stderr).strip()[:1000]}\n"
            f"==================\n"
        )
        raise Exception(f"{e} {debug_info}")

    finally:
        # Guarantee stop and remove
        subprocess.run(f"docker stop {actual_container_id}", shell=True, capture_output=True)
        subprocess.run(f"docker rm {actual_container_id}", shell=True, capture_output=True)


def is_trivy_installed() -> bool:
    """Checks if Trivy executable is available on the system PATH."""
    return shutil.which("trivy") is not None


def run_trivy_scan(image_tag: str) -> dict:
    """Scans the image using Trivy and returns severity counts if installed."""
    if not is_trivy_installed():
        raise FileNotFoundError("Trivy is not installed on the system PATH.")
        
    scan_cmd = f"trivy image --format json --quiet {image_tag}"
    result = subprocess.run(scan_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Trivy scan execution failed: {result.stderr}")
        
    try:
        report = json.loads(result.stdout)
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        
        results = report.get("Results", [])
        for res in results:
            vulns = res.get("Vulnerabilities", [])
            for vuln in vulns:
                severity = vuln.get("Severity", "UNKNOWN").upper()
                if severity in counts:
                    counts[severity] += 1
                else:
                    counts["UNKNOWN"] += 1
        return counts
    except Exception as e:
        raise Exception(f"Failed to parse Trivy JSON report: {e}")
