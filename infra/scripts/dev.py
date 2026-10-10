"""Start every implemented local service with seeded storage and clean shutdown."""

import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PORTS = {
    "api": 8000,
    "ingestion": 8001,
    "rules": 8002,
    "agent": 8003,
    "voice": 8004,
    "email": 8005,
    "browser": 8006,
}


def implemented_services():
    """New services join local dev once both package config and entrypoint exist."""
    return sorted(
        path.name
        for path in (ROOT / "services").iterdir()
        if path.name != "admin-panel"
        and (path / "app/main.py").exists()
        and (path / "pyproject.toml").exists()
    )


def environment():
    env = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            key, separator, value = line.partition("=")
            if not separator or not key.replace("_", "").isalnum():
                raise ValueError(f".env:{number}: expected NAME=value")
            pieces = shlex.split(value, comments=True)
            env.setdefault(key, " ".join(pieces))
    env.setdefault("PROPADMIN_MODE", "local")
    if env["PROPADMIN_MODE"] != "local":
        raise ValueError("make dev requires PROPADMIN_MODE=local")
    data = Path(env.get("PROPADMIN_DATA_PATH", ".data/state.json"))
    env["PROPADMIN_DATA_PATH"] = str(data if data.is_absolute() else ROOT / data)
    env.setdefault("ADMIN_PASSWORD", "propadmin-local")
    env.setdefault("TOKEN_SECRET", "local-development-signing-key")
    env.setdefault("INTERNAL_SERVICE_TOKEN", "local-internal-token")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def check_ports(ports):
    for label, port in ports.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.settimeout(0.2)
            listening = listener.connect_ex(("127.0.0.1", port)) == 0
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.settimeout(0.2)
            try:
                # macOS may allow binding a specific address beside a wildcard listener.
                if listening:
                    raise OSError("A local listener already accepts connections")
                probe.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(
                    f"{label} port {port} is occupied. Stop that process or set "
                    f"{label.upper().replace('-', '_')}_PORT in .env."
                ) from exc


def allocate_ports(defaults, env):
    ports = {
        name: int(env.get(f"{name.upper().replace('-', '_')}_PORT", str(default)))
        for name, default in defaults.items()
    }
    if not all(1 <= port <= 65535 for port in ports.values()):
        raise ValueError("Service ports must be between 1 and 65535")
    if len(set(ports.values())) != len(ports):
        raise ValueError("Service ports must be distinct")
    reserved = set(ports.values())
    for name, port in list(ports.items()):
        try:
            check_ports({name: port})
        except RuntimeError:
            if f"{name.upper().replace('-', '_')}_PORT" in env:
                raise
            candidate = max(8007, port + 1)
            while candidate <= 65535:
                if candidate not in reserved:
                    try:
                        check_ports({name: candidate})
                        break
                    except RuntimeError:
                        pass
                candidate += 1
            else:
                raise RuntimeError(f"No available local port for {name}") from None
            reserved.add(candidate)
            ports[name] = candidate
            print(f"{name}: default port {port} is occupied; using {candidate}.", flush=True)
    return ports


def stop(children):
    for _, child in children:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 5
    for _, child in children:
        try:
            child.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()


def wait_ready(children, ports, timeout=60):
    pending = set(ports)
    deadline = time.monotonic() + timeout
    while pending:
        for name, child in children:
            if child.poll() is not None:
                raise RuntimeError(
                    f"{name} exited with code {child.returncode} before startup completed"
                )
        for name in list(pending):
            path = "/api/session" if name == "admin" else "/healthz"
            url = f"http://127.0.0.1:{ports[name]}{path}"
            try:
                with urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        pending.remove(name)
            except (URLError, OSError):
                pass
        if time.monotonic() >= deadline:
            missing = ", ".join(f"{name} on port {ports[name]}" for name in sorted(pending))
            raise RuntimeError(f"Startup timed out waiting for {missing}; stopping all services")
        if pending:
            time.sleep(0.1)


def main():
    children = []
    try:
        env = environment()
        services = implemented_services()
        if "api" not in services:
            raise RuntimeError("services/api needs pyproject.toml and app/main.py")
        defaults = {
            name: DEFAULT_PORTS.get(name, 8010 + index) for index, name in enumerate(services)
        }
        defaults["admin"] = 3000
        defaults["landing"] = 3001
        ports = allocate_ports(defaults, env)
        check_ports(ports)
        subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=ROOT, env=env, check=True)
        # Run seed with the same environment and path used by both backends.
        subprocess.run([sys.executable, "-m", "db.seed.load"], cwd=ROOT, env=env, check=True)
        env["API_URL"] = f"http://127.0.0.1:{ports['api']}"
        env["API_BASE_URL"] = env["API_URL"]
        for name in services:
            env.setdefault(f"{name.upper()}_SERVICE_URL", f"http://127.0.0.1:{ports[name]}")
        for name in services:
            command = [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(ports[name]),
            ]
            children.append(
                (
                    name,
                    subprocess.Popen(
                        command, cwd=ROOT / "services" / name, env=env, start_new_session=True
                    ),
                )
            )
        command = [
            "pnpm",
            "--dir",
            str(ROOT / "services/admin-panel"),
            "dev",
            "--hostname",
            "127.0.0.1",
            "--port",
            str(ports["admin"]),
        ]
        children.append(
            ("admin", subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=True))
        )
        command = ["node", str(ROOT / "landing/server.mjs")]
        landing_env = {**env, "PORT": str(ports["landing"])}
        children.append(
            (
                "landing",
                subprocess.Popen(command, cwd=ROOT, env=landing_env, start_new_session=True),
            )
        )
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        wait_ready(children, ports)
        print("All local services are ready.", flush=True)
        for name, port in ports.items():
            print(f"{name.title()}: http://127.0.0.1:{port}", flush=True)
        if env["ADMIN_PASSWORD"] == "propadmin-local":
            print("Login password: propadmin-local (local default).", flush=True)
        else:
            print("Login password: configured in .env or environment.", flush=True)
        print(
            "Shared data: " + env["PROPADMIN_DATA_PATH"] + " | Ctrl-C stops all services.",
            flush=True,
        )
        while True:
            for name, child in children:
                if child.poll() is not None:
                    raise RuntimeError(
                        f"{name} exited with code {child.returncode}; stopping stack"
                    )
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopping local services.", flush=True)
        return 0
    except (ValueError, RuntimeError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"make dev: {exc}", file=sys.stderr)
        return 1
    finally:
        stop(children)


if __name__ == "__main__":
    raise SystemExit(main())
