"""Small checks for schema drift, migration errors and reproducible lock compaction."""

import json
import os
import tomllib
from pathlib import Path

import httpx
import pytest
import yaml

from db.schema.apply import execute
from db.schema.generate import generate
from infra.scripts.compact_lock import compact as compact_toml
from infra.scripts.compact_yaml_lock import compact as compact_yaml

ROOT = Path(__file__).resolve().parents[2]


def test_registry_schema_is_current():
    assert (ROOT / 'db/schema/001_entities.surql').read_text() == generate()


def test_migration_rejects_statement_errors_even_on_http_success():
    responses = [
        [{'status': 'OK', 'result': None}],
        [{'status': 'OK', 'result': None}, {'status': 'ERR', 'result': 'Transaction failed'}],
    ]
    client = httpx.Client(
        base_url='http://surreal.test',
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=responses.pop(0))),
    )
    assert execute(client, 'DEFINE TABLE example SCHEMAFULL;')[0]['status'] == 'OK'
    with pytest.raises(RuntimeError, match='Transaction failed'):
        execute(client, 'BEGIN TRANSACTION; INVALID; COMMIT;')


def test_generated_locks_keep_all_metadata_and_stay_under_line_cap():
    uv_source = (ROOT / 'uv.lock').read_text()
    pnpm_source = (ROOT / 'pnpm-lock.yaml').read_text()
    assert tomllib.loads(compact_toml(uv_source)) == tomllib.loads(uv_source)
    assert yaml.safe_load(compact_yaml(pnpm_source)) == yaml.safe_load(pnpm_source)
    assert len(uv_source.splitlines()) <= 1000
    assert len(pnpm_source.splitlines()) <= 1000
    workspace = json.loads((ROOT / 'package.json').read_text())
    assert '@propadmin/admin-panel' in workspace['scripts']['build']


def test_dev_environment_shared_path_and_shell_precedence(tmp_path, monkeypatch):
    from infra.scripts import dev

    monkeypatch.setattr(dev, 'ROOT', tmp_path)
    monkeypatch.delenv('PROPADMIN_DATA_PATH', raising=False)
    monkeypatch.setenv('PROPADMIN_MODE', 'local')
    monkeypatch.setenv('API_PORT', '8123')
    (tmp_path / '.env').write_text('API_PORT=8000\nPROPADMIN_DATA_PATH=data/shared.json\n')
    env = dev.environment()
    assert env['API_PORT'] == '8123'
    assert env['PROPADMIN_DATA_PATH'] == str(tmp_path / 'data/shared.json')


def test_dev_environment_puts_repo_root_on_pythonpath(tmp_path, monkeypatch):
    from infra.scripts import dev

    monkeypatch.setattr(dev, 'ROOT', tmp_path)
    monkeypatch.setenv('PROPADMIN_MODE', 'local')
    monkeypatch.setenv('PYTHONPATH', f'/extra{os.pathsep}{tmp_path}')
    paths = dev.environment()['PYTHONPATH'].split(os.pathsep)
    # Services import `services.<name>.app.*`, as the images do with PYTHONPATH=/app.
    assert paths == [str(tmp_path), '/extra']


def test_dev_port_conflicts_and_clean_process_group_shutdown():
    import socket
    import subprocess
    import sys

    from infra.scripts.dev import allocate_ports, check_ports, stop

    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1', 0))
        with pytest.raises(RuntimeError, match='occupied'):
            check_ports({'api': occupied.getsockname()[1]})
        occupied.listen()
        port = occupied.getsockname()[1]
        # Occupied defaults can move; explicit developer configuration must fail clearly.
        assert allocate_ports({'api': port}, {})['api'] != port
        with pytest.raises(RuntimeError, match='occupied'):
            allocate_ports({'api': port}, {'API_PORT': str(port)})
        with pytest.raises(ValueError, match='distinct'):
            allocate_ports({'api': port, 'ingestion': port}, {})
        with pytest.raises(ValueError, match='between'):
            allocate_ports({'api': 65536}, {})
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                             start_new_session=True)
    stop([('test', child)])
    assert child.poll() is not None
