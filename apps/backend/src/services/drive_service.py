from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.services.feishu_client import FeishuClient


class ShortcutInfo(BaseModel):
    target_token: str
    target_type: str

    model_config = ConfigDict(extra="ignore")


class DriveFile(BaseModel):
    token: str
    name: str
    type: str
    parent_token: str | None = None
    url: str | None = None
    created_time: str | None = None
    modified_time: str | None = None
    owner_id: str | None = None
    shortcut_info: ShortcutInfo | None = None

    model_config = ConfigDict(extra="ignore")


class DriveFileList(BaseModel):
    files: list[DriveFile] = Field(default_factory=list)
    has_more: bool = False
    next_page_token: str | None = None

    model_config = ConfigDict(extra="ignore")


class DriveMeta(BaseModel):
    doc_token: str | None = None
    doc_type: str | None = None
    url: str | None = None

    model_config = ConfigDict(extra="ignore")


class RootFolderMeta(BaseModel):
    token: str
    id: str
    user_id: str

    model_config = ConfigDict(extra="ignore")


class DriveNode(BaseModel):
    token: str
    name: str
    type: str
    children: list["DriveNode"] = Field(default_factory=list)
    parent_token: str | None = None
    url: str | None = None
    created_time: str | None = None
    modified_time: str | None = None
    owner_id: str | None = None
    shortcut_info: ShortcutInfo | None = None

    model_config = ConfigDict(extra="ignore")


class DriveService:
    def __init__(
        self,
        client: FeishuClient | None = None,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self._client = client or FeishuClient()
        self._base_url = base_url.rstrip("/")

    async def get_root_folder_meta(
        self, root_folder_type: str | None = None
    ) -> RootFolderMeta:
        url = f"{self._base_url}/open-apis/drive/explorer/v2/root_folder/meta"
        request_kwargs: dict[str, object] = {}
        if root_folder_type:
            request_kwargs["params"] = {"root_folder_type": root_folder_type}
        response = await self._client.request("GET", url, **request_kwargs)
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"获取根目录失败: {payload.get('msg')}")
        return RootFolderMeta.model_validate(payload.get("data") or {})

    async def list_files(
        self,
        folder_token: str,
        page_token: str | None = None,
        page_size: int = 200,
    ) -> DriveFileList:
        url = f"{self._base_url}/open-apis/drive/v1/files"
        params = {"folder_token": folder_token, "page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        response = await self._client.request("GET", url, params=params)
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"获取文件清单失败: {payload.get('msg')}")
        data = payload.get("data") or {}
        return DriveFileList.model_validate(data)

    async def batch_query_metas(
        self,
        docs: list[tuple[str, str]],
        *,
        with_url: bool = True,
    ) -> dict[str, DriveMeta]:
        if not docs:
            return {}
        url = f"{self._base_url}/open-apis/drive/v1/metas/batch_query"
        request_docs = [
            {"doc_token": token, "doc_type": doc_type} for token, doc_type in docs
        ]
        payload = {"request_docs": request_docs, "with_url": bool(with_url)}
        response = await self._client.request("POST", url, json=payload)
        body = response.json()
        if body.get("code") != 0:
            raise RuntimeError(f"批量获取元数据失败: {body.get('msg')}")
        data = body.get("data") or {}
        metas = data.get("metas") or []
        results: dict[str, DriveMeta] = {}
        for meta in metas:
            item = DriveMeta.model_validate(meta)
            if item.doc_token:
                results[item.doc_token] = item
        return results

    async def create_folder(self, parent_token: str, name: str) -> str:
        """在指定父文件夹中创建子文件夹，返回新文件夹的 token。"""
        url = f"{self._base_url}/open-apis/drive/v1/files/create_folder"
        body = {"name": name, "folder_token": parent_token}
        response = await self._client.request("POST", url, json=body)
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(
                f"创建云端文件夹失败: {payload.get('msg')} (name={name})"
            )
        data = payload.get("data") or {}
        token = data.get("token")
        if not token:
            raise RuntimeError(f"创建文件夹未返回 token: {data}")
        return token

    async def scan_root(
        self, root_folder_type: str = "explorer", name: str | None = None
    ) -> DriveNode:
        meta = await self.get_root_folder_meta(root_folder_type=root_folder_type)
        if name is None:
            name = "我的空间" if root_folder_type == "explorer" else "共享文件夹"
        return await self.scan_folder(meta.token, name=name)

    async def scan_roots(self) -> DriveNode:
        children: list[DriveNode] = []
        my_space = await self.scan_root("explorer", name="我的空间")
        children.append(my_space)
        try:
            shared_space = await self.scan_root("share", name="共享文件夹")
        except RuntimeError:
            shared_space = None
        if shared_space is not None:
            children.append(shared_space)
        return DriveNode(
            token="root",
            name="云空间",
            type="root",
            children=children,
        )

    async def scan_folder(
        self,
        folder_token: str,
        name: str | None = None,
        parent_token: str | None = None,
        visited: set[str] | None = None,
    ) -> DriveNode:
        visited = visited or set()
        if folder_token in visited:
            return DriveNode(
                token=folder_token,
                name=name or folder_token,
                type="folder",
                parent_token=parent_token,
                children=[],
            )
        visited.add(folder_token)

        node = DriveNode(
            token=folder_token,
            name=name or folder_token,
            type="folder",
            parent_token=parent_token,
            children=[],
        )

        page_token: str | None = None
        while True:
            file_list = await self.list_files(folder_token, page_token=page_token)
            for item in file_list.files:
                child = await self._build_node(item, visited)
                node.children.append(child)

            if not file_list.has_more:
                break
            if not file_list.next_page_token:
                break
            page_token = file_list.next_page_token
        return node

    async def _build_node(self, item: DriveFile, visited: set[str]) -> DriveNode:
        if item.type == "shortcut" and item.shortcut_info:
            target_token = item.shortcut_info.target_token or item.token
            target_type = item.shortcut_info.target_type or item.type
            if target_type == "folder":
                return await self.scan_folder(
                    target_token,
                    name=item.name,
                    parent_token=item.parent_token,
                    visited=visited,
                )
            return DriveNode(
                token=target_token,
                name=item.name,
                type=target_type,
                parent_token=item.parent_token,
                url=item.url,
                created_time=item.created_time,
                modified_time=item.modified_time,
                owner_id=item.owner_id,
                shortcut_info=item.shortcut_info,
                children=[],
            )
        if item.type == "folder":
            return await self.scan_folder(
                item.token,
                name=item.name,
                parent_token=item.parent_token,
                visited=visited,
            )

        return DriveNode(
            token=item.token,
            name=item.name,
            type=item.type,
            parent_token=item.parent_token,
            url=item.url,
            created_time=item.created_time,
            modified_time=item.modified_time,
            owner_id=item.owner_id,
            shortcut_info=item.shortcut_info,
            children=[],
        )

    async def close(self) -> None:
        await self._client.close()


__all__ = [
    "DriveFile",
    "DriveFileList",
    "DriveMeta",
    "DriveNode",
    "DriveService",
    "RootFolderMeta",
    "ShortcutInfo",
]
