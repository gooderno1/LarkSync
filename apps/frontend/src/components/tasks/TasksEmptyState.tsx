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
    <div className="rounded-xl border border-dashed border-[#c9d8ec] bg-white/70 py-16 text-center">
      <IconPlus className="mx-auto h-12 w-12 text-[#9fb2c8]" />
      <p className="mt-4 text-sm text-[#6b7f96]">
        {hasAnyTasks
          ? hideTestTasks && testTaskCount > 0
            ? "当前已隐藏测试任务，可点击「显示测试任务」查看。"
            : "暂无符合当前筛选条件的任务。"
          : "暂无同步任务，请点击「新建任务」。"}
      </p>
    </div>
  );
}
