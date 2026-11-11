"""Execute generated tests in a disposable, resource-limited Docker container."""
import os
import subprocess
import tempfile
from pathlib import Path

IMAGE = os.getenv("QA_SANDBOX_IMAGE", "agentic-qa-sandbox:local")

def run(code: str, artifacts: Path, timeout: int = 180) -> tuple[bool, str]:
    artifacts = artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    network = os.getenv("QA_SANDBOX_NETWORK", "bridge")
    if not network or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for ch in network):
        raise ValueError("Invalid QA_SANDBOX_NETWORK")
    if os.getenv("QA_REQUIRE_ISOLATED_NETWORK", "0") == "1" and network in {"bridge", "host", "default"}:
        raise ValueError("Production mode requires a dedicated externally firewalled Docker network")
    junit = artifacts / "junit.xml"
    junit.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="qa-source-") as tmp:
        source = Path(tmp)
        (source / "test_generated.py").write_text(code, encoding="utf-8")
        cmd = ["docker", "run", "--rm", "--init", "--user", f"{os.getuid()}:{os.getgid()}",
               "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
               "--pids-limit=128", "--memory=1g", "--cpus=1", f"--network={network}",
               "--tmpfs=/tmp:rw,nosuid,nodev,size=128m",
               "--mount", f"type=bind,src={source},dst=/work,readonly",
               "--mount", f"type=bind,src={artifacts},dst=/results",
               "-e", "HOME=/tmp", "-e", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
               "-e", "BASE_URL=" + os.environ.get("BASE_URL", "https://www.saucedemo.com"),
               IMAGE, "python", "-m", "pytest", "-q", "/work/test_generated.py",
               "--junitxml=/results/junit.xml"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, (result.stdout + "\n" + result.stderr)[-12000:]
        except subprocess.TimeoutExpired:
            return False, f"Sandbox timeout after {timeout} seconds"
        except FileNotFoundError:
            return False, "Docker executable not found; sandbox execution required"
