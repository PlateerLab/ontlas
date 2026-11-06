"""Every live server, one at a time: start it, run what reads its address, remove it. Nothing else is touched.

    python tools/run_live.py                 # all of them
    python tools/run_live.py pgvector qdrant # some of them

Needs Docker. Containers are named xspace-live-<name>, take an unusual port, have a memory limit and are always removed.
The run stops before starting a server when free memory is under the floor.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOOR_GB = float(os.environ.get("XSPACE_LIVE_FLOOR_GB", "6"))
PW = "xspace-Live-1"


def free_gb() -> float:
    if os.name != "nt":
        return 99.0
    out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
                         capture_output=True, text=True)
    return int(out.stdout.strip() or 0) / 1048576


def run(*cmd: str, quiet: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=quiet, text=True, encoding="utf-8", errors="replace")


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait(check, seconds: int = 180) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            if check():
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def logs_have(name: str, text: str) -> bool:
    out = run("docker", "logs", name)
    return text in (out.stdout or "") + (out.stderr or "")


def _fuseki_ready(name: str, port: int) -> bool:
    if not port_open(port):
        return False
    req = urllib.request.Request(f"http://127.0.0.1:{port}/$/datasets", data=b"dbName=ds&dbType=mem", method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "Authorization": "Basic " + __import__("base64").b64encode(f"admin:{PW}".encode()).decode()})
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as e:
        return e.code == 409  # made by the attempt before
    return True


def _mssql_setup(name: str) -> None:
    base = ["docker", "exec", name, "/opt/mssql-tools18/bin/sqlcmd", "-C", "-S", "localhost", "-U", "sa", "-P", PW, "-Q"]
    run(*base, f"CREATE DATABASE xspace; CREATE LOGIN xspace WITH PASSWORD = '{PW}', CHECK_POLICY = OFF;")
    run(*base, "USE xspace; CREATE USER xspace FOR LOGIN xspace; ALTER ROLE db_owner ADD MEMBER xspace;")  # USE needs the database made


SERVERS = {
    "postgres": {"image": "postgres:16-alpine", "port": (15432, 5432), "mem": "512m", "env": {"POSTGRES_PASSWORD": PW, "POSTGRES_DB": "xspace"},
                 "ready": lambda n, p: logs_have(n, "database system is ready to accept connections") and port_open(p),
                 "vars": {"XSPACE_LIVE_PG": f"postgresql://postgres:{PW}@127.0.0.1:15432/xspace"}, "tests": ["tests/test_live.py", "tests/test_ports.py"]},
    "mysql": {"image": "mysql:8.4", "port": (13306, 3306), "mem": "768m", "env": {"MYSQL_ROOT_PASSWORD": PW, "MYSQL_DATABASE": "xspace"},
              "ready": lambda n, p: logs_have(n, "ready for connections. Version") and port_open(p),
              "vars": {"XSPACE_LIVE_MYSQL": f"mysql://root:{PW}@127.0.0.1:13306/xspace"}, "tests": ["tests/test_live.py"]},
    "fuseki": {"image": "stain/jena-fuseki", "port": (13030, 3030), "mem": "768m", "env": {"ADMIN_PASSWORD": PW},
               "ready": lambda n, p: _fuseki_ready(n, p),
               "vars": {"XSPACE_LIVE_FUSEKI": "http://127.0.0.1:13030/ds", "XSPACE_LIVE_FUSEKI_AUTH": f"admin:{PW}"}, "tests": ["tests/test_live.py"]},
    "neo4j": {"image": "neo4j:5.26", "port": (17687, 7687), "mem": "1500m", "env": {"NEO4J_AUTH": f"neo4j/{PW}"},
              "ready": lambda n, p: logs_have(n, "Started.") and port_open(p),
              "vars": {"XSPACE_LIVE_NEO4J": "bolt://127.0.0.1:17687", "XSPACE_LIVE_NEO4J_AUTH": f"neo4j:{PW}"}, "tests": ["tests/test_live.py"]},
    "gremlin": {"image": "tinkerpop/gremlin-server:3.8.2", "port": (18182, 8182), "mem": "1g", "env": {},
                "ready": lambda n, p: logs_have(n, "Channel started at port 8182") and port_open(p),
                "vars": {"XSPACE_LIVE_GREMLIN": "ws://127.0.0.1:18182/gremlin"}, "tests": ["tests/test_live.py"]},
    "oracle": {"image": "gvenzl/oracle-free:23-slim", "port": (15210, 1521), "mem": "2g",
               "env": {"ORACLE_PASSWORD": PW, "APP_USER": "xspace", "APP_USER_PASSWORD": PW},
               "ready": lambda n, p: logs_have(n, "DATABASE IS READY TO USE"), "wait": 300,
               "vars": {"XSPACE_LIVE_ORACLE": f"oracle://xspace:{PW}@127.0.0.1:15210/FREEPDB1"}, "tests": ["tests/test_live.py"]},
    "mssql": {"image": "mcr.microsoft.com/mssql/server:2022-latest", "port": (14330, 1433), "mem": "2g",
              "env": {"ACCEPT_EULA": "Y", "MSSQL_SA_PASSWORD": PW, "MSSQL_PID": "Developer"},
              "ready": lambda n, p: logs_have(n, "SQL Server is now ready for client connections") and port_open(p), "wait": 240, "setup": _mssql_setup,
              "vars": {"XSPACE_LIVE_MSSQL": f"mssql://xspace:{PW}@127.0.0.1:14330/xspace"}, "tests": ["tests/test_live.py"]},
    "qdrant": {"image": "qdrant/qdrant:v1.15.5", "port": (16333, 6333), "mem": "512m", "env": {},
               "ready": lambda n, p: port_open(p), "vars": {"XSPACE_LIVE_QDRANT": "http://127.0.0.1:16333"}, "tests": ["tests/test_vectors.py"]},
    "pgvector": {"image": "pgvector/pgvector:pg16", "port": (15433, 5432), "mem": "512m", "env": {"POSTGRES_PASSWORD": PW, "POSTGRES_DB": "xspace"},
                 "ready": lambda n, p: logs_have(n, "database system is ready to accept connections") and port_open(p),
                 "vars": {"XSPACE_LIVE_PGVECTOR": f"postgresql://postgres:{PW}@127.0.0.1:15433/xspace"}, "tests": ["tests/test_vectors.py"]},
}


def one(key: str, s: dict) -> dict:
    name = f"xspace-live-{key}"
    if free_gb() < FLOOR_GB:
        return {"server": key, "skipped": f"free memory {free_gb():.1f} GB is under {FLOOR_GB} GB"}
    run("docker", "rm", "-f", name)
    host, inner = s["port"]
    cmd = ["docker", "run", "-d", "--name", name, "--memory", s["mem"], "-p", f"127.0.0.1:{host}:{inner}"]
    for k, v in s["env"].items():
        cmd += ["-e", f"{k}={v}"]
    started = run(*cmd, s["image"])
    if started.returncode:
        return {"server": key, "failed": (started.stderr or "")[-200:]}
    try:
        if not wait(lambda: s["ready"](name, host), s.get("wait", 120)):
            return {"server": key, "failed": "never became ready", "log": (run("docker", "logs", "--tail", "5", name).stdout or "")[-300:]}
        time.sleep(3)
        if s.get("setup"):
            s["setup"](name)
        env = {**os.environ, **s["vars"], "PYTHONUTF8": "1"}
        out = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short", *s["tests"], "-k", "live or Live or " + key],
                             cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = [x for x in out.stdout.splitlines() if x.strip()][-6:]
        return {"server": key, "exit": out.returncode, "result": tail[-1] if tail else "", "failures": [x[:170] for x in out.stdout.splitlines() if x.startswith("FAILED")],
                "errors": sorted({x[:220] for x in out.stdout.splitlines() if x.startswith("E   ") and "Error" in x})[:6]}
    finally:
        run("docker", "rm", "-f", name)


def main() -> int:
    wanted = sys.argv[1:] or list(SERVERS)
    results = []
    for key in wanted:
        r = one(key, SERVERS[key])
        results.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)
    return 0 if all(r.get("exit") == 0 for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
