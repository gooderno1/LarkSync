import { TreeNode } from "../TreeNode";
import { IconCloud, IconRefresh } from "../Icons";
import type { CloudSelection, DriveNode } from "../../types";

type NewTaskCloudStepProps = {
  inputCls: string;
  tree: DriveNode | null | undefined;
  treeLoading: boolean;
  treeError: string | null;
  taskCloudToken: string;
  selectedCloud: CloudSelection | null;
  manualCloudInput: string;
  manualCloudName: string;
  manualCloudError: string | null;
  onRefreshTree: () => void;
  onSelectCloudFolder: (selection: CloudSelection) => void;
  onManualCloudInputChange: (value: string) => void;
  onManualCloudNameChange: (value: string) => void;
  onApplyManualCloud: () => void;
};

export function NewTaskCloudStep({
  inputCls,
  tree,
  treeLoading,
  treeError,
  taskCloudToken,
  selectedCloud,
  manualCloudInput,
  manualCloudName,
  manualCloudError,
  onRefreshTree,
  onSelectCloudFolder,
  onManualCloudInputChange,
  onManualCloudNameChange,
  onApplyManualCloud,
}: NewTaskCloudStepProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-[#52657a]">选择飞书云端目录</label>
        <button
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8ec] bg-white px-3 py-1.5 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
          onClick={onRefreshTree}
          type="button"
        >
          <IconRefresh className="h-3 w-3" /> 刷新
        </button>
      </div>
      <div className="max-h-[260px] overflow-auto rounded-lg border border-[#d7e4f5] bg-white p-2.5">
        {treeLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-6 animate-pulse rounded bg-[#eaf2ff]" />
            ))}
          </div>
        ) : treeError ? (
          <div className="space-y-2">
            <p className="text-sm text-[#be123c]">{treeError}</p>
            {(treeError.includes("Unauthorized") ||
              treeError.includes("权限") ||
              treeError.includes("permission")) && (
              <div className="space-y-1.5 rounded-lg border border-[#f59e0b]/35 bg-[#fffbeb] p-3 text-xs">
                <p className="font-semibold text-[#92400e]">权限不足，请按以下步骤操作：</p>
                <ol className="list-inside list-decimal space-y-1 text-[#334762]">
                  <li>
                    在飞书开发者后台确认已添加{" "}
                    <code className="rounded bg-white px-1 text-[#102033]">drive:drive</code>、{" "}
                    <code className="rounded bg-white px-1 text-[#102033]">docx:document</code>、{" "}
                    <code className="rounded bg-white px-1 text-[#102033]">docx:document.block:convert</code>{" "}
                    等权限
                  </li>
                  <li>进入「版本管理与发布」→ 创建版本并发布应用</li>
                  <li>回到 LarkSync → 点击「退出登录」清除旧令牌</li>
                  <li>重新点击「飞书授权登录」完成授权</li>
                </ol>
                <a
                  href="https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-resolve-error-99991679"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-block font-medium text-[#b45309] underline hover:text-[#92400e]"
                >
                  查看飞书官方排查指南 →
                </a>
              </div>
            )}
          </div>
        ) : tree ? (
          <ul className="space-y-3">
            <TreeNode node={tree} selectable selectedToken={taskCloudToken} onSelect={onSelectCloudFolder} />
          </ul>
        ) : (
          <div className="py-6 text-center">
            <IconCloud className="mx-auto h-8 w-8 text-[#9fb2c8]" />
            <p className="mt-2 text-sm text-[#6b7f96]">暂无目录数据，请先刷新。</p>
          </div>
        )}
      </div>
      <details className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
        <summary className="cursor-pointer text-xs font-semibold text-[#3370ff]">使用共享链接或 Token</summary>
        <div className="mt-3 space-y-2">
        <div>
          <p className="text-xs font-medium text-[#52657a]">共享链接 / Token</p>
          <p className="mt-1 text-[11px] text-[#7a8da3]">
            非所有者的共享文件夹可能不会出现在目录树中，请使用分享链接或 Token 创建同步。
          </p>
        </div>
        <input
          className={inputCls}
          placeholder="例如：https://.../drive/folder/xxxxxxxx 或 Token"
          value={manualCloudInput}
          onChange={(e) => onManualCloudInputChange(e.target.value)}
        />
        <input
          className={inputCls}
          placeholder="云端目录显示名称（可选）"
          value={manualCloudName}
          onChange={(e) => onManualCloudNameChange(e.target.value)}
        />
        <div className="flex items-center gap-3">
          <button
            className="rounded-lg border border-[#c9d8ec] bg-white px-4 py-2 text-xs font-medium text-[#3370ff] hover:bg-[#eef5ff]"
            onClick={onApplyManualCloud}
            type="button"
          >
            使用链接
          </button>
          {manualCloudError ? <span className="text-xs text-[#be123c]">{manualCloudError}</span> : null}
        </div>
        </div>
      </details>
      {selectedCloud ? (
        <div className="flex items-center gap-2 rounded-lg border border-[#10b981]/25 bg-[#ecfdf5] px-3 py-2.5 text-xs text-[#047857]">
          <IconCloud className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{selectedCloud.path}</span>
        </div>
      ) : null}
    </div>
  );
}
