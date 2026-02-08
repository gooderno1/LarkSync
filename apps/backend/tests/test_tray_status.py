import importlib
import sys
from pathlib import Path
from typing import Generator

# 确保从任意工作目录运行 pytest 时都能找到 src 包
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from fastapi.testclient import TestClient

from src.core.config import ConfigManager


@pytest.fixture
def tray_client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    """
    独立构建一份使用临时 SQLite 的 app，以免写入真实数据目录。
    """
    monkeypatch.setenv("LARKSYNC_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("LARKSYNC_DB_PATH", str(tmp_path / "test.db"))

    # 确保配置单例与 main 模块按新的环境重载
    ConfigManager.reset()
    if "src.main" in sys.modules:
        main = importlib.reload(sys.modules["src.main"])
    else:
        main = importlib.import_module("src.main")

    with TestClient(main.app) as client:
        yield client

    # 恢复默认配置单例并重载 main，避免影响其他用例
    ConfigManager.reset()
    importlib.reload(main)


def test_tray_status_conflict_count(tray_client: TestClient) -> None:
    # 创建一条冲突记录
    payload = {
        "local_path": "/tmp/demo.md",
        "cloud_token": "doccnTestToken",
        "local_hash": "localhash",
        "db_hash": "dbhash",
        "cloud_version": 2,
        "db_version": 1,
        "local_preview": "local preview",
        "cloud_preview": "cloud preview",
    }
    resp = tray_client.post("/conflicts", json=payload)
    assert resp.status_code == 200
    conflict_id = resp.json()["id"]

    # /tray/status 应返回未解决冲突数量
    status = tray_client.get("/tray/status").json()
    assert status["unresolved_conflicts"] == 1

    # 解决冲突后，数量应变为 0
    resolve = tray_client.post(f"/conflicts/{conflict_id}/resolve", json={"action": "use_cloud"})
    assert resolve.status_code == 200

    status_after = tray_client.get("/tray/status").json()
    assert status_after["unresolved_conflicts"] == 0
