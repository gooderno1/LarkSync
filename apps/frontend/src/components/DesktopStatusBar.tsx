import { useDesktopStatus } from "../hooks/useDesktopStatus";
import { formatShortTime } from "../lib/formatters";
import { IconClock, IconDatabase } from "./Icons";
import { StatusPill } from "./StatusPill";

const backendPort = import.meta.env.VITE_LARKSYNC_BACKEND_PORT ?? "8000";

export function DesktopStatusBar() {
  const { status } = useDesktopStatus();
  const backendProcessLabel = status.runtime.packaged
    ? "LarkSync.Backend.exe"
    : "LarkSync.Backend.dev";

  return (
    <footer className="flex h-[78px] flex-none items-center justify-between border-t border-[#d7e6ff] bg-[#fdfdfd] pl-9 pr-8 text-xs text-[#52657A]">
      <div className="flex min-w-0 items-center gap-4">
        <span className="inline-flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${status.runtime.backend_running ? "bg-[#10B981]" : "bg-[#F43F5E]"}`} />
          后端进程
        </span>
        <span className="whitespace-nowrap font-medium text-[#52657a]">{backendProcessLabel}</span>
        <StatusPill
          label={status.runtime.backend_running ? "运行中" : "失败"}
          tone={status.runtime.backend_running ? "success" : "danger"}
        />
        <span className="h-4 w-px bg-[#d7e6ff]" aria-hidden="true" />
        <span className="inline-flex items-center gap-2 whitespace-nowrap">
          <span>端口</span>
          <span className="font-medium text-[#3370ff]">{backendPort}</span>
        </span>
        <span className="h-4 w-px bg-[#d7e6ff]" aria-hidden="true" />
        <span className="inline-flex items-center gap-2 whitespace-nowrap">
          <span>WebSocket</span>
          <span className="h-2 w-2 rounded-full bg-[#3370ff]" aria-hidden="true" />
          <span className="font-medium text-[#3370ff]">已连接</span>
        </span>
        <span className="h-4 w-px bg-[#d7e6ff]" aria-hidden="true" />
        <span className="inline-flex items-center gap-2 whitespace-nowrap">
          <IconDatabase className="h-3.5 w-3.5 text-[#3370FF]" />
          数据库
          <span className="font-medium text-[#52657a]">SQLite 3</span>
        </span>
        <span className="h-4 w-px bg-[#d7e6ff]" aria-hidden="true" />
        <span className="whitespace-nowrap">版本 {status.update.current_version}</span>
      </div>

      <div className="flex items-center gap-3 whitespace-nowrap">
        <IconClock className="h-4 w-4 text-[#52657a]" />
        <span>最近同步：&nbsp;{status.tasks.last_sync_time ? formatShortTime(status.tasks.last_sync_time) : "暂无"}</span>
      </div>
    </footer>
  );
}
