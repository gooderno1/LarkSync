import { IconFolder } from "../Icons";

type NewTaskLocalStepProps = {
  inputCls: string;
  taskName: string;
  taskLocalPath: string;
  taskBasePath: string;
  folderPickLoading: boolean;
  folderPickError: string | null;
  onTaskNameChange: (value: string) => void;
  onTaskLocalPathChange: (value: string) => void;
  onTaskBasePathChange: (value: string) => void;
  onPickLocalFolder: () => void;
};

export function NewTaskLocalStep({
  inputCls,
  taskName,
  taskLocalPath,
  taskBasePath,
  folderPickLoading,
  folderPickError,
  onTaskNameChange,
  onTaskLocalPathChange,
  onTaskBasePathChange,
  onPickLocalFolder,
}: NewTaskLocalStepProps) {
  return (
    <div className="space-y-5">
      <div>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">
          任务名称 <span className="text-zinc-600">（可选）</span>
        </label>
        <input
          className={inputCls}
          placeholder="例如：笔记同步"
          value={taskName}
          onChange={(e) => onTaskNameChange(e.target.value)}
        />
      </div>
      <div>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">本地同步目录</label>
        <div className="flex gap-2">
          <input
            className={`flex-1 ${inputCls}`}
            placeholder="点击右侧按钮选择目录"
            value={taskLocalPath}
            onChange={(e) => onTaskLocalPathChange(e.target.value)}
          />
          <button
            className="inline-flex items-center gap-1.5 rounded-lg bg-zinc-800 px-4 py-2.5 text-xs font-medium text-zinc-200 transition hover:bg-zinc-700"
            onClick={onPickLocalFolder}
            type="button"
          >
            <IconFolder className="h-3.5 w-3.5" />
            {folderPickLoading ? "选择中..." : "浏览"}
          </button>
        </div>
        {folderPickError ? <p className="mt-1.5 text-xs text-rose-400">{folderPickError}</p> : null}
        {taskLocalPath ? (
          <div className="mt-2 flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
            <IconFolder className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{taskLocalPath}</span>
          </div>
        ) : null}
      </div>
      <div>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">
          Base Path <span className="text-zinc-600">（可选，默认同本地目录）</span>
        </label>
        <input
          className={inputCls}
          placeholder="用于计算相对路径"
          value={taskBasePath}
          onChange={(e) => onTaskBasePathChange(e.target.value)}
        />
      </div>
    </div>
  );
}
