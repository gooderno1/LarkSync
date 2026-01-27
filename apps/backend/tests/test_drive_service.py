import httpx
import pytest

from src.services.drive_service import DriveService


class FakeClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self.requests: list[tuple[str, str, dict]] = []

    async def request(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        payload = self._responses.pop(0)
        return httpx.Response(200, json=payload)

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_get_root_folder_meta_parses_response() -> None:
    client = FakeClient(
        [
            {
                "code": 0,
                "data": {"token": "root-token", "id": "root-id", "user_id": "user"},
            }
        ]
    )
    service = DriveService(client=client)
    meta = await service.get_root_folder_meta()
    assert meta.token == "root-token"
    assert meta.id == "root-id"
    assert meta.user_id == "user"


@pytest.mark.asyncio
async def test_scan_folder_builds_tree_with_pagination_and_recursion() -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "files": [
                    {
                        "token": "folder-1",
                        "name": "子文件夹",
                        "type": "folder",
                        "parent_token": "root",
                    },
                    {
                        "token": "file-1",
                        "name": "说明.md",
                        "type": "file",
                        "parent_token": "root",
                    },
                ],
                "has_more": True,
                "next_page_token": "next-page",
            },
        },
        {
            "code": 0,
            "data": {
                "files": [
                    {
                        "token": "file-2",
                        "name": "子文档",
                        "type": "docx",
                        "parent_token": "folder-1",
                    }
                ],
                "has_more": False,
            },
        },
        {
            "code": 0,
            "data": {
                "files": [
                    {
                        "token": "file-3",
                        "name": "日志.txt",
                        "type": "file",
                        "parent_token": "root",
                    }
                ],
                "has_more": False,
            },
        },
    ]
    client = FakeClient(responses)
    service = DriveService(client=client)

    tree = await service.scan_folder("root", name="我的空间")
    assert tree.name == "我的空间"
    assert len(tree.children) == 3
    assert tree.children[0].name == "子文件夹"
    assert tree.children[1].name == "说明.md"
    assert tree.children[2].name == "日志.txt"
    assert tree.children[0].children[0].name == "子文档"

    request_params = client.requests[2][2]["params"]
    assert request_params["page_token"] == "next-page"
