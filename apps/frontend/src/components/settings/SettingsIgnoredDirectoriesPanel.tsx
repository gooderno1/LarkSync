import { IconFolder } from "../Icons";
import { cn } from "../../lib/utils";
import type { SyncTask } from "../../types";

type SettingsIgnoredDirectoriesPanelProps = {
  tasks: SyncTask[];
  showIgnoredDirectorySettings: boolean;
  toggleIgnoredDirectorySettings: () => void;
  ignoreHiddenCachePaths: boolean;
  setIgnoreHiddenCachePaths: (value: boolean | ((prev: boolean) => boolean)) => void;
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
  ignoreHiddenCachePaths,
  setIgnoreHiddenCachePaths,
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
    <div className="rounded-lg border border-[#d7e4f5] bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[#102033]">忽略规则</h2>
          <p className="mt-1 max-w-3xl text-[11px] leading-4 text-[#7e91a8]">
            默认跳过隐藏文件、缓存目录与系统文件；可展开本地忽略目录，为指定任务增加双向忽略子目录。
          </p>
        </div>
        <button
          className="rounded-lg border border-[#c9d8eb] bg-white px-3 py-1.5 text-xs font-medium text-[#52677f] transition hover:border-[#3370FF]/40 hover:bg-[#f2f7ff] hover:text-[#2456d6]"
          onClick={toggleIgnoredDirectorySettings}
          type="button"
        >
          {showIgnoredDirectorySettings ? "收起任务规则" : "管理任务规则"}
        </button>
      </div>

      {showIgnoredDirectorySettings ? (
        <div className="mt-3 space-y-3">
          <div className="rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3">
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
              <div>
                <p className="text-sm font-semibold text-[#102033]">默认忽略隐藏/缓存路径</p>
                <p className="mt-1 text-[11px] leading-5 text-[#7e91a8]">
                  启用后，会默认跳过所有以 `.` 开头的文件或目录，以及 `__pycache__`。关闭后，仅保留任务级忽略目录和系统保留目录规则。
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  className={cn(
                    "relative h-6 w-11 rounded-full transition",
                    ignoreHiddenCachePaths ? "bg-[#3370FF]" : "bg-[#a9bad0]",
                  )}
                  onClick={() => setIgnoreHiddenCachePaths((prev) => !prev)}
                  type="button"
                >
                  <span
                    className={cn(
                      "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition",
                      ignoreHiddenCachePaths ? "left-6" : "left-0.5",
                    )}
                  />
                </button>
                <span className="text-xs text-[#7e91a8]">
                  {ignoreHiddenCachePaths ? "默认启用" : "已关闭"}
                </span>
              </div>
            </div>
          </div>
          {tasks.length === 0 ? (
            <p className="text-xs text-[#7e91a8]">暂无同步任务。</p>
          ) : (
            tasks.map((task) => {
              const ignoredSubpaths = ignoredSubpathsMap[task.id] ?? task.ignored_subpaths ?? [];
              return (
                <div
                  key={`${task.id}-ignored-subpaths`}
                  className="rounded-lg border border-[#d7e4f5] bg-white p-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-[#102033]">{task.name || "未命名任务"}</p>
                      <p className="truncate text-[11px] text-[#7e91a8]">{task.local_path}</p>
                    </div>
                    <button
                      className="shrink-0 rounded-lg border border-[#3370FF]/25 bg-[#edf4ff] px-3 py-1.5 text-xs font-medium text-[#2456d6] transition hover:border-[#3370FF]/45 hover:bg-[#e3eeff] disabled:opacity-50"
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
                          className="inline-flex items-center gap-2 rounded-full border border-[#c9d8eb] bg-[#f8fbff] px-3 py-1 text-xs text-[#34516f]"
                        >
                          <span>{item}</span>
                          <button
                            className="rounded-full px-1.5 py-0.5 text-[#d14343] transition hover:bg-[#fff1f1]"
                            onClick={() => removeIgnoredSubpath(task.id, item)}
                            type="button"
                          >
                            移除
                          </button>
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-[#7e91a8]">暂无忽略目录</span>
                    )}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <input
                      className="min-w-[240px] flex-1 rounded-lg border border-[#c9d8eb] bg-white px-3 py-2 text-xs text-[#1f2d3d] outline-none transition placeholder:text-[#8fa1b7] focus:border-[#3370FF] focus:ring-2 focus:ring-[#3370FF]/15"
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
                      className="rounded-lg border border-[#c9d8eb] bg-white px-3 py-2 text-xs font-medium text-[#52677f] transition hover:border-[#3370FF]/40 hover:bg-[#f2f7ff] hover:text-[#2456d6]"
                      onClick={() => addIgnoredSubpath(task.id, ignoredPathDrafts[task.id] ?? "")}
                      type="button"
                    >
                      添加路径
                    </button>
                    <button
                      className="inline-flex items-center gap-1.5 rounded-lg border border-[#c9d8eb] bg-white px-3 py-2 text-xs font-medium text-[#52677f] transition hover:border-[#3370FF]/40 hover:bg-[#f2f7ff] hover:text-[#2456d6] disabled:opacity-50"
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
