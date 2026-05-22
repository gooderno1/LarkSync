import { IconPlus, IconRefresh } from "../Icons";
import { ThemeToggle } from "../ThemeToggle";

type TasksPageHeaderProps = {
  showTestToggle: boolean;
  hideTestTasks: boolean;
  onToggleTestTasks: () => void;
  onRefresh: () => void;
  onCreate: () => void;
};

export function TasksPageHeader({
  showTestToggle,
  hideTestTasks,
  onToggleTestTasks,
  onRefresh,
  onCreate,
}: TasksPageHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
      <div>
        <h2 className="text-lg font-semibold text-zinc-50">同步任务</h2>
        <p className="mt-1 text-xs text-zinc-400">管理任务的同步模式、更新策略与执行状态。</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {showTestToggle ? (
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
            onClick={onToggleTestTasks}
            type="button"
          >
            {hideTestTasks ? "显示测试任务" : "隐藏测试任务"}
          </button>
        ) : null}
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
          onClick={onRefresh}
          type="button"
        >
          <IconRefresh className="h-3.5 w-3.5" /> 刷新
        </button>
        <button
          className="inline-flex items-center gap-2 rounded-lg bg-[#3370FF] px-4 py-2 text-xs font-semibold text-white hover:bg-[#3370FF]/80"
          onClick={onCreate}
          type="button"
        >
          <IconPlus className="h-3.5 w-3.5" /> 新建任务
        </button>
        <ThemeToggle />
      </div>
    </div>
  );
}
