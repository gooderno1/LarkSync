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
    <div className="space-y-3">
      <div>
        <label className="mb-1.5 block text-xs font-medium text-[#52657a]">
          任务名称 <span className="text-[#9fb2c8]">（可选）</span>
        </label>
        <input
          className={inputCls}
          placeholder="例如：笔记同步"
          value={taskName}
          onChange={(e) => onTaskNameChange(e.target.value)}
        />
      </div>
      <div>
        <label className="mb-1.5 block text-xs font-medium text-[#52657a]">本地同步目录</label>
        <div className="flex gap-2">
          <input
            className={`flex-1 ${inputCls}`}
            placeholder="点击右侧按钮选择目录"
            value={taskLocalPath}
            onChange={(e) => onTaskLocalPathChange(e.target.value)}
          />
          <button
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8ec] bg-[#eef5ff] px-2.5 py-2 text-xs font-semibold text-[#3370ff] transition hover:bg-[#dbeafe]"
            onClick={onPickLocalFolder}
            type="button"
          >
            <IconFolder className="h-3.5 w-3.5" />
            {folderPickLoading ? "选择中..." : "浏览"}
          </button>
        </div>
        {folderPickError ? <p className="mt-1.5 text-xs text-[#be123c]">{folderPickError}</p> : null}
        {taskLocalPath ? (
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-[#10b981]/25 bg-[#ecfdf5] px-3 py-2 text-xs text-[#047857]">
            <IconFolder className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{taskLocalPath}</span>
          </div>
        ) : null}
      </div>
      <div>
        <label className="mb-1.5 block text-xs font-medium text-[#52657a]">
          Base Path <span className="text-[#9fb2c8]">（可选，默认同本地目录）</span>
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
