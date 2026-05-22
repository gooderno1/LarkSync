import { Pagination } from "../Pagination";
import { IconConflicts, IconRefresh } from "../Icons";
import { cn } from "../../lib/utils";

type FileLogEntry = {
  timestamp: string;
  level: string;
  message: string;
};

type FileLogsQueryState = {
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
};

function levelColor(level: string) {
  switch (level) {
    case "ERROR": return "text-rose-400";
    case "WARNING": return "text-amber-400";
    case "INFO": return "text-zinc-400";
    case "DEBUG": return "text-zinc-600";
    default: return "text-zinc-400";
  }
}

type SystemLogPanelProps = {
  query: FileLogsQueryState;
  fileLogs: FileLogEntry[];
  fileLogTotal: number;
  fileLogSearch: string;
  setFileLogSearch: (value: string) => void;
  fileLogLevel: string;
  setFileLogLevel: (value: string) => void;
  fileLogOrder: "asc" | "desc";
  setFileLogOrder: (value: "asc" | "desc") => void;
  fileLogPage: number;
  setFileLogPage: (page: number) => void;
  fileLogPageSize: number;
  setFileLogPageSize: (size: number) => void;
  resetFileLogPage: () => void;
};

export function SystemLogPanel({
  query,
  fileLogs,
  fileLogTotal,
  fileLogSearch,
  setFileLogSearch,
  fileLogLevel,
  setFileLogLevel,
  fileLogOrder,
  setFileLogOrder,
  fileLogPage,
  setFileLogPage,
  fileLogPageSize,
  setFileLogPageSize,
  resetFileLogPage,
}: SystemLogPanelProps) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-zinc-50">系统日志</h3>
          <p className="mt-1 text-xs text-zinc-400">来自 loguru 日志文件，适合查看底层异常和 API 调用错误。</p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={query.refetch} type="button">
          <IconRefresh className="h-3.5 w-3.5" /> 刷新
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-[1.2fr_0.5fr_0.6fr_0.6fr]">
        <input
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
          placeholder="搜索日志内容（如 error、token、频率限制）"
          value={fileLogSearch}
          onChange={(event) => {
            setFileLogSearch(event.target.value);
            resetFileLogPage();
          }}
        />
        <select
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none"
          value={fileLogOrder}
          onChange={(event) => {
            setFileLogOrder(event.target.value as "asc" | "desc");
            resetFileLogPage();
          }}
        >
          <option value="desc">最新优先</option>
          <option value="asc">最早优先</option>
        </select>
        <select
          className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none"
          value={fileLogLevel}
          onChange={(event) => {
            setFileLogLevel(event.target.value);
            resetFileLogPage();
          }}
        >
          <option value="">全部级别</option>
          <option value="ERROR">ERROR</option>
          <option value="WARNING">WARNING</option>
          <option value="INFO">INFO</option>
        </select>
        <button
          className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800"
          onClick={() => {
            setFileLogLevel("");
            setFileLogSearch("");
            setFileLogOrder("desc");
            resetFileLogPage();
          }}
          type="button"
        >
          重置
        </button>
      </div>

      {query.error ? (
        <div className="mt-4 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-xs text-rose-200">
          系统日志加载失败：{query.error.message}
        </div>
      ) : null}
      <div className="mt-5 max-h-[620px] space-y-2 overflow-auto pr-1 log-scroll-area">
        {query.isLoading ? (
          [1, 2, 3, 4, 5].map((item) => <div key={item} className="h-10 animate-pulse rounded-lg bg-zinc-800/50" />)
        ) : fileLogs.length === 0 ? (
          <div className="py-8 text-center">
            <IconConflicts className="mx-auto h-10 w-10 text-zinc-700" />
            <p className="mt-3 text-sm text-zinc-500">暂无匹配的系统日志。</p>
          </div>
        ) : (
          fileLogs.map((entry, index) => (
            <div key={`${entry.timestamp}-${index}`} className="rounded-lg border border-zinc-800 bg-zinc-950/50 px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="shrink-0 text-[11px] font-mono text-zinc-500">{entry.timestamp}</span>
                <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold", levelColor(entry.level),
                  entry.level === "ERROR" ? "bg-rose-500/15" : entry.level === "WARNING" ? "bg-amber-500/15" : "bg-zinc-800/50"
                )}>
                  {entry.level}
                </span>
              </div>
              <p className="mt-1 whitespace-pre-wrap break-all font-mono text-xs text-zinc-300">{entry.message}</p>
            </div>
          ))
        )}
      </div>

      {(fileLogTotal > 0 || fileLogs.length > 0) ? (
        <div className="mt-4 border-t border-zinc-800 pt-4">
          <Pagination
            page={fileLogPage}
            pageSize={fileLogPageSize}
            total={fileLogTotal}
            onPageChange={setFileLogPage}
            onPageSizeChange={(size) => {
              setFileLogPageSize(size);
              resetFileLogPage();
            }}
            pageSizeOptions={[20, 50, 100, 200]}
          />
        </div>
      ) : null}
    </div>
  );
}
