import type { SyncTask } from "../../types";

type SettingsMaintenancePanelProps = {
  tasks: SyncTask[];
  resettingLinks: boolean;
  onResetTask: (task: SyncTask) => Promise<void>;
};

export function SettingsMaintenancePanel({
  tasks,
  resettingLinks,
  onResetTask,
}: SettingsMaintenancePanelProps) {
  return (
    <div className="mt-6 border-t border-zinc-800/80 pt-4">
      <h3 className="text-sm font-medium text-zinc-200">维护工具</h3>
      <p className="mt-1 text-[11px] text-zinc-500">
        当同步映射出现异常时，可重置指定任务的同步映射（SyncLink）。重置后下次同步将重新建立映射关系。
      </p>
      <div className="mt-3 space-y-2">
        {tasks.length === 0 ? (
          <p className="text-xs text-zinc-500">暂无同步任务。</p>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-zinc-200">{task.name || "未命名任务"}</p>
                <p className="truncate text-[11px] text-zinc-500">{task.local_path}</p>
              </div>
              <button
                className="ml-3 shrink-0 rounded-lg border border-amber-700/50 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-300 transition hover:bg-amber-500/20 disabled:opacity-50"
                disabled={resettingLinks}
                onClick={() => void onResetTask(task)}
                type="button"
              >
                重置映射
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
