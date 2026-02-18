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
    assert "params" not in client.requests[0][2]


@pytest.mark.asyncio
async def test_get_root_folder_meta_supports_root_type() -> None:
    client = FakeClient(
        [
            {
                "code": 0,
                "data": {"token": "share-token", "id": "share-id", "user_id": "user"},
            }
        ]
    )
    service = DriveService(client=client)
    meta = await service.get_root_folder_meta(root_folder_type="share")
    assert meta.token == "share-token"
    assert client.requests[0][2]["params"] == {"root_folder_type": "share"}


@pytest.mark.asyncio
async def test_scan_roots_combines_my_space_and_shared() -> None:
    responses = [
        {
            "code": 0,
            "data": {"token": "root-my", "id": "root-id", "user_id": "user"},
        },
        {"code": 0, "data": {"files": [], "has_more": False}},
        {
            "code": 0,
            "data": {"token": "root-share", "id": "share-id", "user_id": "user"},
        },
        {"code": 0, "data": {"files": [], "has_more": False}},
    ]
    client = FakeClient(responses)
    service = DriveService(client=client)

    tree = await service.scan_roots()

    assert tree.type == "root"
    assert [child.name for child in tree.children] == ["我的空间", "共享文件夹"]
    assert tree.children[0].token == "root-my"
    assert tree.children[1].token == "root-share"

    assert client.requests[0][2]["params"] == {"root_folder_type": "explorer"}
    assert client.requests[2][2]["params"] == {"root_folder_type": "share"}


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


@pytest.mark.asyncio
async def test_scan_folder_expands_shortcut_folder() -> None:
    responses = [
        {
            "code": 0,
            "data": {
                "files": [
                    {
                        "token": "shortcut-1",
                        "name": "共享文件夹",
                        "type": "shortcut",
                        "parent_token": "root",
                        "shortcut_info": {
                            "target_token": "shared-folder",
                            "target_type": "folder",
                        },
                    }
                ],
                "has_more": False,
            },
        },
        {"code": 0, "data": {"files": [], "has_more": False}},
    ]
    client = FakeClient(responses)
    service = DriveService(client=client)

    tree = await service.scan_folder("root", name="我的空间")
    assert len(tree.children) == 1
    assert tree.children[0].name == "共享文件夹"
    assert tree.children[0].token == "shared-folder"
    assert tree.children[0].type == "folder"


@pytest.mark.asyncio
async def test_delete_file_passes_type_param() -> None:
    client = FakeClient([{"code": 0}])
    service = DriveService(client=client)

    await service.delete_file("doc-token", "docx")

    method, url, kwargs = client.requests[0]
    assert method == "DELETE"
    assert url.endswith("/open-apis/drive/v1/files/doc-token")
    assert kwargs["params"] == {"type": "docx"}


@pytest.mark.asyncio
async def test_delete_file_without_type() -> None:
    client = FakeClient([{"code": 0}])
    service = DriveService(client=client)

    await service.delete_file("file-token")

    _, _, kwargs = client.requests[0]
    assert "params" not in kwargs


@pytest.mark.asyncio
async def test_delete_file_raises_with_detail() -> None:
    client = FakeClient([{"code": 1001, "msg": "field validation failed"}])
    service = DriveService(client=client)

    with pytest.raises(RuntimeError) as exc:
        await service.delete_file("bad-token", "docx")

    assert "field validation failed" in str(exc.value)
    assert "bad-token" in str(exc.value)
    assert "docx" in str(exc.value)
