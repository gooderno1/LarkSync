import { IconPlus, IconSearch } from "../Icons";

type TasksPageHeaderProps = {
  onCreate: () => void;
  searchQuery?: string;
  onSearchQueryChange?: (value: string) => void;
  stateFilter?: string;
  onStateFilterChange?: (value: string) => void;
  syncModeFilter?: string;
  onSyncModeFilterChange?: (value: string) => void;
  healthFilter?: string;
  onHealthFilterChange?: (value: string) => void;
};

export function TasksPageHeader({
  onCreate,
  searchQuery = "",
  onSearchQueryChange,
  stateFilter = "all",
  onStateFilterChange,
  syncModeFilter = "all",
  onSyncModeFilterChange,
  healthFilter = "all",
  onHealthFilterChange,
}: TasksPageHeaderProps) {
  return (
    <header className="min-w-0">
      <h1 className="text-xl font-semibold text-[#102033]">同步任务</h1>

      <div
        className="mt-4 flex min-w-0 flex-wrap items-center justify-between gap-4"
        data-task-filter-toolbar="true"
      >
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
          <label className="relative block h-9 w-[230px] shrink-0">
            <span className="sr-only">搜索任务</span>
            <IconSearch className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#6b7f96]" />
            <input
              className="h-9 w-full rounded-lg border border-[#c9d8ec] bg-white pl-9 pr-3 text-sm text-[#102033] outline-none placeholder:text-[#8fa1b7] focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/15"
              placeholder="搜索任务"
              value={searchQuery}
              onChange={(event) => onSearchQueryChange?.(event.target.value)}
            />
          </label>
          <select
            className="h-9 min-w-[132px] rounded-lg border border-[#c9d8ec] bg-white px-3 text-sm text-[#334762] outline-none focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/15"
            value={stateFilter}
            onChange={(event) => onStateFilterChange?.(event.target.value)}
          >
            <option value="all">全部状态</option>
            <option value="running">同步中</option>
            <option value="idle">空闲</option>
            <option value="failed">失败</option>
            <option value="paused">已停用</option>
          </select>
          <select
            className="h-9 min-w-[132px] rounded-lg border border-[#c9d8ec] bg-white px-3 text-sm text-[#334762] outline-none focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/15"
            value={syncModeFilter}
            onChange={(event) => onSyncModeFilterChange?.(event.target.value)}
          >
            <option value="all">全部模式</option>
            <option value="bidirectional">双向同步</option>
            <option value="upload_only">仅上传</option>
            <option value="download_only">仅下载</option>
          </select>
          <select
            className="h-9 min-w-[132px] rounded-lg border border-[#c9d8ec] bg-white px-3 text-sm text-[#334762] outline-none focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/15"
            value={healthFilter}
            onChange={(event) => onHealthFilterChange?.(event.target.value)}
          >
            <option value="all">全部健康</option>
            <option value="healthy">健康</option>
            <option value="attention">待处理</option>
            <option value="error">错误</option>
          </select>
        </div>
        <div className="flex shrink-0 items-center">
          <button
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#3370ff] px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.2)] hover:bg-[#1d4ed8]"
            data-task-primary-action="true"
            onClick={onCreate}
            type="button"
          >
            <IconPlus className="h-3.5 w-3.5" /> 新建任务
          </button>
        </div>
      </div>
    </header>
  );
}
