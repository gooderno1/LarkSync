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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-zinc-400">选择飞书云端目录</label>
        <button
          className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          onClick={onRefreshTree}
          type="button"
        >
          <IconRefresh className="h-3 w-3" /> 刷新
        </button>
      </div>
      <div className="max-h-[320px] overflow-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4">
        {treeLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-6 animate-pulse rounded bg-zinc-800/50" />
            ))}
          </div>
        ) : treeError ? (
          <div className="space-y-2">
            <p className="text-sm text-rose-400">{treeError}</p>
            {(treeError.includes("Unauthorized") ||
              treeError.includes("权限") ||
              treeError.includes("permission")) && (
              <div className="space-y-1.5 rounded-lg border border-amber-500/40 bg-amber-500/20 p-3 text-xs">
                <p className="font-semibold text-amber-300">权限不足，请按以下步骤操作：</p>
                <ol className="list-decimal list-inside space-y-1 text-zinc-200">
                  <li>
                    在飞书开发者后台确认已添加{" "}
                    <code className="bg-zinc-800 px-1 rounded">drive:drive</code>、{" "}
                    <code className="bg-zinc-800 px-1 rounded">docx:document</code>、{" "}
                    <code className="bg-zinc-800 px-1 rounded">docx:document.block:convert</code>{" "}
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
                  className="mt-1 inline-block font-medium text-amber-300 underline hover:text-amber-200"
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
            <IconCloud className="mx-auto h-8 w-8 text-zinc-700" />
            <p className="mt-2 text-sm text-zinc-500">暂无目录数据，请先刷新。</p>
          </div>
        )}
      </div>
      <div className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
        <div>
          <p className="text-xs font-medium text-zinc-400">共享链接 / Token</p>
          <p className="mt-1 text-[11px] text-zinc-600">
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
            className="rounded-lg bg-zinc-800 px-4 py-2 text-xs font-medium text-zinc-200 hover:bg-zinc-700"
            onClick={onApplyManualCloud}
            type="button"
          >
            使用链接
          </button>
          {manualCloudError ? <span className="text-xs text-rose-400">{manualCloudError}</span> : null}
        </div>
      </div>
      {selectedCloud ? (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2.5 text-xs text-emerald-300">
          <IconCloud className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{selectedCloud.path}</span>
        </div>
      ) : null}
    </div>
  );
}
