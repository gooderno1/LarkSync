import { IconPlus } from "../Icons";

type TasksEmptyStateProps = {
  hasAnyTasks: boolean;
  hideTestTasks: boolean;
  testTaskCount: number;
};

export function TasksEmptyState({
  hasAnyTasks,
  hideTestTasks,
  testTaskCount,
}: TasksEmptyStateProps) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 py-16 text-center">
      <IconPlus className="mx-auto h-12 w-12 text-zinc-700" />
      <p className="mt-4 text-sm text-zinc-500">
        {hasAnyTasks
          ? hideTestTasks && testTaskCount > 0
            ? "当前已隐藏测试任务，可点击「显示测试任务」查看。"
            : "暂无符合当前筛选条件的任务。"
          : "暂无同步任务，请点击「新建任务」。"}
      </p>
    </div>
  );
}
