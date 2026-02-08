/* ------------------------------------------------------------------ */
/*  日志中心页面 — 同步日志(内存) + 系统日志(文件) + 冲突管理             */
/* ------------------------------------------------------------------ */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTasks } from "../hooks/useTasks";
import { useConflicts } from "../hooks/useConflicts";
import { formatTimestamp } from "../lib/formatters";
import { statusLabelMap } from "../lib/constants";
import { apiFetch } from "../lib/api";
import { StatusPill } from "../components/StatusPill";
import { Pagination } from "../components/Pagination";
import { IconRefresh, IconConflicts, IconCopy } from "../components/Icons";
import { useToast } from "../components/ui/toast";
import { cn } from "../lib/utils";
import { ThemeToggle } from "../components/ThemeToggle";
import type { SyncLogEntry } from "../types";

/* 文件日志条目类型 */
type FileLogEntry = {
  timestamp: string;
  level: string;
  message: string;
};

/* 文件日志分页响应 */
type FileLogResponse = {
  total: number;
  items: FileLogEntry[];
};

export function LogCenterPage() {
  const { tasks, statusMap, refreshStatus } = useTasks();
  const { conflicts, conflictLoading, conflictError, refreshConflicts, resolveConflict } = useConflicts();
  const { toast } = useToast();

  const [logTab, setLogTab] = useState<"logs" | "file-logs" | "conflicts">("logs");

  // ---- 同步日志 (内存) 状态 ----
  const [logFilterStatus, setLogFilterStatus] = useState("all");
  const [logFilterText, setLogFilterText] = useState("");
  const [logPage, setLogPage] = useState(1);
  const [logPageSize, setLogPageSize] = useState(20);

  // ---- 系统日志 (文件) 状态 ----
  const [fileLogLevel, setFileLogLevel] = useState("");
  const [fileLogSearch, setFileLogSearch] = useState("");
  const [fileLogPage, setFileLogPage] = useState(1);
  const [fileLogPageSize, setFileLogPageSize] = useState(50);
  const [fileLogOrder, setFileLogOrder] = useState<"asc" | "desc">("asc");

  // ---- 同步日志数据 (内存) ----
  const syncLogEntries: SyncLogEntry[] = useMemo(() => {
    return Object.values(statusMap)
      .flatMap((st) =>
        (st.last_files || []).map((f) => ({
          taskId: st.task_id,
          taskName: tasks.find((t) => t.id === st.task_id)?.name || "未命名任务",
          timestamp: f.timestamp ?? st.finished_at ?? st.started_at ?? Math.floor(Date.now() / 1000),
          status: f.status,
          path: f.path,
          message: f.message,
        }))
      )
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 500);
  }, [statusMap, tasks]);

  const filteredLogs = useMemo(() => {
    const text = logFilterText.trim().toLowerCase();
    return syncLogEntries.filter((e) => {
      if (logFilterStatus !== "all" && e.status !== logFilterStatus) return false;
      if (!text) return true;
      return e.path.toLowerCase().includes(text) || e.taskName.toLowerCase().includes(text) || (e.message || "").toLowerCase().includes(text);
    });
  }, [syncLogEntries, logFilterStatus, logFilterText]);

  const logTotalPages = Math.max(1, Math.ceil(filteredLogs.length / logPageSize));
  const paginatedLogs = useMemo(() => {
    const start = (logPage - 1) * logPageSize;
    return filteredLogs.slice(start, start + logPageSize);
  }, [filteredLogs, logPage, logPageSize]);

  // ---- 系统日志数据 (文件 API) ----
  const fileLogsQuery = useQuery<FileLogResponse>({
    queryKey: ["file-logs", fileLogLevel, fileLogSearch, fileLogOrder, fileLogPage, fileLogPageSize],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set("limit", String(fileLogPageSize));
      params.set("offset", String((fileLogPage - 1) * fileLogPageSize));
      if (fileLogLevel) params.set("level", fileLogLevel);
      if (fileLogSearch) params.set("search", fileLogSearch);
      params.set("order", fileLogOrder);
      return apiFetch<FileLogResponse>(`/sync/logs/file?${params.toString()}`);
    },
    enabled: logTab === "file-logs",
    staleTime: 5_000,
    placeholderData: { total: 0, items: [] },
  });

  const fileLogs = fileLogsQuery.data?.items || [];
  const fileLogTotal = fileLogsQuery.data?.total || 0;

  const levelColor = (level: string) => {
    switch (level) {
      case "ERROR": return "text-rose-400";
      case "WARNING": return "text-amber-400";
      case "INFO": return "text-zinc-400";
      case "DEBUG": return "text-zinc-600";
      default: return "text-zinc-400";
    }
  };

  // 筛选器变更时重置页码
  const resetLogPage = () => setLogPage(1);
  const resetFileLogPage = () => setFileLogPage(1);

  return (
    <section className="space-y-6 animate-fade-up">
      {/* Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
        <div>
          <h2 className="text-lg font-semibold text-zinc-50">日志中心</h2>
          <p className="mt-1 text-xs text-zinc-400">同步日志、系统日志与冲突处理统一管理。</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "logs" ? "border-[#3370FF]/50 bg-[#3370FF]/10 text-[#3370FF]" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("logs")}
            type="button"
          >
            同步日志
          </button>
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "file-logs" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("file-logs")}
            type="button"
          >
            系统日志
          </button>
          <button
            className={cn("rounded-lg border px-4 py-2 text-xs font-medium transition", logTab === "conflicts" ? "border-amber-500/40 bg-amber-500/10 text-amber-300" : "border-zinc-700 text-zinc-300 hover:bg-zinc-800")}
            onClick={() => setLogTab("conflicts")}
            type="button"
          >
            冲突管理 {conflicts.filter((c) => !c.resolved).length > 0 ? `(${conflicts.filter((c) => !c.resolved).length})` : ""}
          </button>
          <ThemeToggle />
        </div>
      </div>

      {/* ============ 同步日志 tab (内存) ============ */}
      {logTab === "logs" ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-zinc-50">同步日志流</h3>
              <p className="mt-1 text-xs text-zinc-400">来自当前运行的任务状态（内存中），重启后清空。</p>
            </div>
            <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={refreshStatus} type="button">
              <IconRefresh className="h-3.5 w-3.5" /> 刷新日志
            </button>
          </div>

          {/* 筛选器 */}
          <div className="mt-4 grid gap-3 md:grid-cols-[1.2fr_0.6fr_0.6fr]">
            <input
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
              placeholder="搜索任务名、路径或错误信息"
              value={logFilterText}
              onChange={(e) => { setLogFilterText(e.target.value); resetLogPage(); }}
            />
            <select
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none"
              value={logFilterStatus}
              onChange={(e) => { setLogFilterStatus(e.target.value); resetLogPage(); }}
            >
              <option value="all">全部状态</option>
              <option value="downloaded">下载</option>
              <option value="uploaded">上传</option>
              <option value="success">成功</option>
              <option value="failed">失败</option>
              <option value="skipped">跳过</option>
              <option value="started">开始</option>
            </select>
            <button className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800" onClick={() => { setLogFilterStatus("all"); setLogFilterText(""); resetLogPage(); }} type="button">
              重置
            </button>
          </div>

          {/* 日志列表 */}
          <div className="mt-5 max-h-[520px] space-y-3 overflow-auto pr-1 log-scroll-area">
            {filteredLogs.length === 0 ? (
              <div className="py-8 text-center">
                <IconConflicts className="mx-auto h-10 w-10 text-zinc-700" />
                <p className="mt-3 text-sm text-zinc-500">暂无匹配日志。如需查看完整历史，请切换到「系统日志」标签。</p>
              </div>
            ) : (
              paginatedLogs.map((entry, i) => (
                <div key={`${entry.taskId}-${entry.timestamp}-${i}`} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-xs text-zinc-500">{formatTimestamp(entry.timestamp)}</p>
                      <p className="text-sm font-medium text-zinc-200">{entry.taskName}</p>
                      <p className="break-all text-xs text-zinc-500">{entry.path}</p>
                    </div>
                    <StatusPill label={statusLabelMap[entry.status] || entry.status} tone={entry.status === "failed" ? "danger" : entry.status === "skipped" ? "warning" : "success"} />
                  </div>
                  {entry.message ? <p className="mt-2 text-xs text-zinc-600">{entry.message}</p> : null}
                </div>
              ))
            )}
          </div>

          {/* 分页 */}
          {filteredLogs.length > 0 ? (
            <div className="mt-4 border-t border-zinc-800 pt-4">
              <Pagination
                page={logPage}
                pageSize={logPageSize}
                total={filteredLogs.length}
                onPageChange={setLogPage}
                onPageSizeChange={(size) => { setLogPageSize(size); resetLogPage(); }}
                pageSizeOptions={[20, 50, 100]}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      {/* ============ 系统日志 tab (文件) ============ */}
      {logTab === "file-logs" ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-zinc-50">系统日志</h3>
              <p className="mt-1 text-xs text-zinc-400">来自 loguru 日志文件，包含完整历史记录（含错误详情）。</p>
            </div>
            <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={() => fileLogsQuery.refetch()} type="button">
              <IconRefresh className="h-3.5 w-3.5" /> 刷新
            </button>
          </div>

          {/* 筛选器 */}
          <div className="mt-4 grid gap-3 md:grid-cols-[1.2fr_0.5fr_0.6fr_0.6fr]">
            <input
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none focus:border-[#3370FF]"
              placeholder="搜索日志内容（如 error、token、频率限制）"
              value={fileLogSearch}
              onChange={(e) => { setFileLogSearch(e.target.value); resetFileLogPage(); }}
            />
            <select
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none"
              value={fileLogOrder}
              onChange={(e) => { setFileLogOrder(e.target.value as "asc" | "desc"); resetFileLogPage(); }}
            >
              <option value="asc">最早优先</option>
              <option value="desc">最新优先</option>
            </select>
            <select
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm text-zinc-200 outline-none"
              value={fileLogLevel}
              onChange={(e) => { setFileLogLevel(e.target.value); resetFileLogPage(); }}
            >
              <option value="">全部级别</option>
              <option value="ERROR">ERROR</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
            </select>
            <button className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800" onClick={() => { setFileLogLevel(""); setFileLogSearch(""); setFileLogOrder("asc"); resetFileLogPage(); }} type="button">
              重置
            </button>
          </div>

          {/* 日志列表 */}
          <div className="mt-5 max-h-[520px] space-y-2 overflow-auto pr-1 log-scroll-area">
            {fileLogsQuery.isLoading ? (
              <div className="space-y-2">{[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-10 animate-pulse rounded-lg bg-zinc-800/50" />)}</div>
            ) : fileLogs.length === 0 ? (
              <div className="py-8 text-center">
                <IconConflicts className="mx-auto h-10 w-10 text-zinc-700" />
                <p className="mt-3 text-sm text-zinc-500">暂无匹配的系统日志。</p>
              </div>
            ) : (
              fileLogs.map((entry, i) => (
                <div key={`${entry.timestamp}-${i}`} className="rounded-lg border border-zinc-800 bg-zinc-950/50 px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
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
                  </div>
                </div>
              ))
            )}
          </div>

          {/* 分页 */}
          {(fileLogTotal > 0 || fileLogs.length > 0) ? (
            <div className="mt-4 border-t border-zinc-800 pt-4">
              <Pagination
                page={fileLogPage}
                pageSize={fileLogPageSize}
                total={fileLogTotal}
                onPageChange={setFileLogPage}
                onPageSizeChange={(size) => { setFileLogPageSize(size); resetFileLogPage(); }}
                pageSizeOptions={[20, 50, 100, 200]}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      {/* ============ 冲突管理 tab ============ */}
      {logTab === "conflicts" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
            <div>
              <h3 className="text-lg font-semibold text-zinc-50">冲突管理</h3>
              <p className="mt-1 text-xs text-zinc-400">处理云端与本地同时修改产生的冲突。</p>
            </div>
            <button className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800" onClick={refreshConflicts} disabled={conflictLoading} type="button">
              <IconRefresh className="h-3.5 w-3.5" /> {conflictLoading ? "加载中..." : "刷新"}
            </button>
          </div>
          {conflictError ? <p className="text-sm text-rose-400">加载失败：{conflictError}</p> : null}
          {conflicts.length === 0 ? (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 py-16 text-center">
              <IconConflicts className="mx-auto h-12 w-12 text-zinc-700" />
              <p className="mt-4 text-sm text-zinc-500">暂无冲突记录。</p>
            </div>
          ) : (
            conflicts.map((c) => (
              <div key={c.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-1">
                    <p className="text-xs uppercase tracking-widest text-zinc-500">本地路径</p>
                    <p className="text-sm text-zinc-200">{c.local_path}</p>
                    <p className="text-xs text-zinc-500">云端 token：{c.cloud_token}</p>
                    <p className="text-xs text-zinc-600">哈希：{c.local_hash.slice(0, 8)} / {c.db_hash.slice(0, 8)}</p>
                  </div>
                  <StatusPill label={c.resolved ? "已处理" : "待处理"} tone={c.resolved ? "success" : "warning"} />
                </div>
                {/* Diff preview */}
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-zinc-500">本地版本</p>
                    <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                      {c.local_preview || "暂无本地预览。"}
                    </pre>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-zinc-500">云端版本</p>
                    <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                      {c.cloud_preview || "暂无云端预览。"}
                    </pre>
                  </div>
                </div>
                {/* Resolve buttons */}
                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    className="rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-semibold text-emerald-300 transition hover:bg-emerald-500/30 disabled:opacity-50"
                    disabled={c.resolved}
                    onClick={() => { resolveConflict({ id: c.id, action: "use_local" }); toast("已采用本地版本", "success"); }}
                    type="button"
                  >
                    使用本地
                  </button>
                  <button
                    className="rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 disabled:opacity-50"
                    disabled={c.resolved}
                    onClick={() => { resolveConflict({ id: c.id, action: "use_cloud" }); toast("已采用云端版本", "success"); }}
                    type="button"
                  >
                    使用云端
                  </button>
                  <button
                    className="rounded-lg border border-[#3370FF]/40 bg-[#3370FF]/10 px-4 py-2 text-xs font-medium text-[#3370FF] transition hover:bg-[#3370FF]/20 disabled:opacity-50"
                    disabled={c.resolved}
                    onClick={() => { resolveConflict({ id: c.id, action: "keep_both" }); toast("已保留双方版本", "info"); }}
                    type="button"
                  >
                    <span className="inline-flex items-center gap-1.5"><IconCopy className="h-3 w-3" />保留双方</span>
                  </button>
                  {c.resolved ? (
                    <span className="self-center text-xs text-zinc-500">已处理：{c.resolved_action}</span>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      ) : null}
    </section>
  );
}
