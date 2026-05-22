import { IconFolder } from "../Icons";
import type { SyncTask } from "../../types";

type SettingsIgnoredDirectoriesPanelProps = {
  tasks: SyncTask[];
  showIgnoredDirectorySettings: boolean;
  toggleIgnoredDirectorySettings: () => void;
  ignoredSubpathsMap: Record<string, string[]>;
  ignoredPathDrafts: Record<string, string>;
  setIgnoredPathDrafts: (updater: (prev: Record<string, string>) => Record<string, string>) => void;
  updatingIgnoredSubpaths: boolean;
  handleSaveIgnoredSubpaths: (taskId: string) => Promise<void>;
  removeIgnoredSubpath: (taskId: string, target: string) => void;
  addIgnoredSubpath: (taskId: string, rawValue: string) => void;
  pickingIgnoredTaskId: string | null;
  handlePickIgnoredSubpath: (taskId: string, localPath: string) => Promise<void>;
};

export function SettingsIgnoredDirectoriesPanel({
  tasks,
  showIgnoredDirectorySettings,
  toggleIgnoredDirectorySettings,
  ignoredSubpathsMap,
  ignoredPathDrafts,
  setIgnoredPathDrafts,
  updatingIgnoredSubpaths,
  handleSaveIgnoredSubpaths,
  removeIgnoredSubpath,
  addIgnoredSubpath,
  pickingIgnoredTaskId,
  handlePickIgnoredSubpath,
}: SettingsIgnoredDirectoriesPanelProps) {
  return (
    <div className="mt-6 border-t border-zinc-800/80 pt-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-zinc-200">本地忽略目录</h3>
          <p className="mt-1 text-[11px] text-zinc-500">
            为指定任务配置双向忽略的子目录。加入后，该目录及其内容不会再参与上传、下载和删除联动。适合 `node_modules`、`.git`、构建产物或缓存目录。
          </p>
        </div>
        <button
          className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200"
          onClick={toggleIgnoredDirectorySettings}
          type="button"
        >
          {showIgnoredDirectorySettings ? "收起配置" : "展开配置"}
        </button>
      </div>

      {showIgnoredDirectorySettings ? (
        <div className="mt-3 space-y-3">
          {tasks.length === 0 ? (
            <p className="text-xs text-zinc-500">暂无同步任务。</p>
          ) : (
            tasks.map((task) => {
              const ignoredSubpaths = ignoredSubpathsMap[task.id] ?? task.ignored_subpaths ?? [];
              return (
                <div
                  key={`${task.id}-ignored-subpaths`}
                  className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-zinc-200">{task.name || "未命名任务"}</p>
                      <p className="truncate text-[11px] text-zinc-500">{task.local_path}</p>
                    </div>
                    <button
                      className="shrink-0 rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 disabled:opacity-50"
                      disabled={updatingIgnoredSubpaths}
                      onClick={() => void handleSaveIgnoredSubpaths(task.id)}
                      type="button"
                    >
                      {updatingIgnoredSubpaths ? "保存中..." : "应用忽略目录"}
                    </button>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {ignoredSubpaths.length > 0 ? (
                      ignoredSubpaths.map((item) => (
                        <span
                          key={`${task.id}-${item}`}
                          className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-950/70 px-3 py-1 text-xs text-zinc-300"
                        >
                          <span>{item}</span>
                          <button
                            className="rounded-full px-1.5 py-0.5 text-rose-400 transition hover:bg-rose-500/10 hover:text-rose-300"
                            onClick={() => removeIgnoredSubpath(task.id, item)}
                            type="button"
                          >
                            移除
                          </button>
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-zinc-500">暂无忽略目录</span>
                    )}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <input
                      className="min-w-[260px] flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 outline-none focus:border-[#3370FF]"
                      placeholder="输入相对路径，例如：POC/GENESIS/node_modules"
                      value={ignoredPathDrafts[task.id] ?? ""}
                      onChange={(e) =>
                        setIgnoredPathDrafts((prev) => ({
                          ...prev,
                          [task.id]: e.target.value,
                        }))
                      }
                    />
                    <button
                      className="rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800"
                      onClick={() => addIgnoredSubpath(task.id, ignoredPathDrafts[task.id] ?? "")}
                      type="button"
                    >
                      添加路径
                    </button>
                    <button
                      className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 disabled:opacity-50"
                      disabled={pickingIgnoredTaskId === task.id}
                      onClick={() => void handlePickIgnoredSubpath(task.id, task.local_path)}
                      type="button"
                    >
                      <IconFolder className="h-3.5 w-3.5" />
                      {pickingIgnoredTaskId === task.id ? "选择中..." : "选择子目录"}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : null}
    </div>
  );
}
