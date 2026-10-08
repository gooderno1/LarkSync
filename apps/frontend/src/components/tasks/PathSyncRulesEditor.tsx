import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiFetchForAccount } from "../../lib/api";
import { modeLabels } from "../../lib/constants";
import { effectivePathSyncMode, normalizeRulePath } from "../../lib/pathSyncRules";
import type { PathSyncRule, SyncTask, SyncTaskEntries, SyncTaskEntry } from "../../types";
import { IconFileText, IconFolder } from "../Icons";

const fieldClass = "h-9 min-w-0 rounded-lg border border-[#c9d8ec] bg-white px-2 text-xs text-[#334762] outline-none focus:border-[#3370ff] disabled:opacity-50";
const buttonClass = "rounded-lg border border-[#c9d8ec] px-3 py-2 text-xs font-medium text-[#334762] hover:bg-[#eef5ff] disabled:opacity-50";

function ModeOptions() {
  return <><option value="bidirectional">双向同步</option><option value="download_only">仅下载</option><option value="upload_only">仅上传</option></>;
}

function TaskEntryBrowser({ task, rules, onSelect }: {
  task: SyncTask; rules: PathSyncRule[]; onSelect: (entry: SyncTaskEntry) => void;
}) {
  const [directory, setDirectory] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const accountId = task.account_id || "";
  const query = useQuery<SyncTaskEntries>({
    queryKey: ["task-entries", accountId, task.id, directory, search, offset],
    queryFn: ({ signal }) => apiFetchForAccount(
      `/sync/tasks/${encodeURIComponent(task.id)}/entries?${new URLSearchParams({ path: directory, search, offset: String(offset), limit: "50" })}`,
      accountId, { signal },
    ),
    staleTime: 10_000,
  });
  const navigate = (path: string) => { setDirectory(path); setSearch(""); setOffset(0); };
  return (
    <div className="mt-3 rounded-lg border border-[#d7e4f5] bg-[#f8fbff] p-3" aria-label="选择任务内文档或文件夹">
      <div className="flex items-center gap-2">
        <button className={buttonClass} onClick={() => navigate("")} type="button">根目录</button>
        <button className={buttonClass} disabled={!directory} onClick={() => navigate(directory.split("/").slice(0, -1).join("/"))} type="button">上一级</button>
        <span className="min-w-0 flex-1 truncate font-mono text-xs text-[#52657a]" title={directory}>{directory || "任务根目录"}</span>
        {directory ? <button className={buttonClass} type="button" onClick={() => onSelect({ path: directory, kind: "folder", sync_mode: "" })}>选择此文件夹</button> : null}
      </div>
      <input aria-label="筛选当前文件夹" className={`${fieldClass} mt-2 w-full`} value={search} onChange={(event) => { setSearch(event.target.value); setOffset(0); }} placeholder="搜索当前层级的名称" />
      {query.isLoading ? <p className="py-4 text-xs text-[#52657a]">正在读取目录…</p> : null}
      {query.error ? <div role="alert" className="py-3 text-xs text-[#be123c]">{query.error.message}<button className="ml-2 underline" type="button" onClick={() => void query.refetch()}>重试</button></div> : null}
      {query.data ? <>
        <div className="mt-2 max-h-52 overflow-y-auto divide-y divide-[#edf3fb]">
          {query.data.items.length === 0 ? <p className="py-4 text-xs text-[#52657a]">暂无可选对象，可直接输入相对路径。</p> : null}
          {query.data.items.map((entry) => {
            const Icon = entry.kind === "folder" ? IconFolder : IconFileText;
            return <div className="flex items-center gap-2 py-2" key={entry.path}>
              <Icon className="h-4 w-4 shrink-0 text-[#3370ff]" />
              <button type="button" className="min-w-0 flex-1 truncate text-left text-xs text-[#334762] hover:text-[#3370ff]" title={entry.path} onClick={() => entry.kind === "folder" ? navigate(entry.path) : onSelect(entry)}>{entry.path.split("/").slice(-1)[0]}</button>
              <span className="shrink-0 text-[11px] text-[#52657a]">{modeLabels[effectivePathSyncMode(task.sync_mode, rules, entry.path)]}</span>
              <button className={buttonClass} aria-label={`选择 ${entry.path}`} type="button" onClick={() => onSelect(entry)}>选择</button>
            </div>;
          })}
        </div>
        <div className="mt-2 flex items-center justify-between text-[11px] text-[#52657a]">
          <span>共 {query.data.total} 项 · 本地及已同步对象</span>
          <div className="flex gap-2"><button type="button" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 50))}>上一页</button><button type="button" disabled={offset + 50 >= query.data.total} onClick={() => setOffset(offset + 50)}>下一页</button></div>
        </div>
      </> : null}
    </div>
  );
}

export function PathSyncRulesEditor({ task, rules, onChange, disabled = false }: {
  task: SyncTask; rules: PathSyncRule[]; onChange: (rules: PathSyncRule[]) => void; disabled?: boolean;
}) {
  const [path, setPath] = useState("");
  const [kind, setKind] = useState<PathSyncRule["kind"]>("file");
  const [mode, setMode] = useState<PathSyncRule["sync_mode"]>("download_only");
  const [browsing, setBrowsing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addRule = () => {
    try {
      const normalized = normalizeRulePath(path);
      if (rules.some((rule) => rule.path === normalized)) throw new Error("此对象已有规则，请直接修改其同步方式。");
      onChange([...rules, { path: normalized, kind, sync_mode: mode }]);
      setPath(""); setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : "无法添加规则"); }
  };
  return (
    <section className="py-3" data-path-sync-rules="true">
      <div className="flex items-center justify-between gap-3"><h4 className="text-sm font-semibold text-[#102033]">文档与文件夹规则（{rules.length}）</h4><button type="button" className={buttonClass} disabled={disabled} aria-expanded={browsing} onClick={() => setBrowsing(!browsing)}>{browsing ? "收起目录" : "浏览选择"}</button></div>
      <p className="mt-1 text-xs leading-5 text-[#52657a]">文件优先于文件夹，子文件夹优先于父文件夹；其余内容沿用任务默认方式。忽略目录仍不参与同步。</p>
      {browsing ? <fieldset disabled={disabled}><TaskEntryBrowser task={task} rules={rules} onSelect={(entry) => { setPath(entry.path); setKind(entry.kind); setBrowsing(false); setError(null); }} /></fieldset> : null}
      <fieldset disabled={disabled} className="mt-3 flex flex-wrap gap-2">
        <select aria-label="规则对象类型" className={fieldClass} value={kind} onChange={(event) => setKind(event.target.value as PathSyncRule["kind"])}><option value="file">文档 / 文件</option><option value="folder">文件夹及子项</option></select>
        <input aria-label="规则相对路径" className={`${fieldClass} w-44 flex-1`} placeholder="例如：归档/设计说明.md" value={path} onChange={(event) => { setPath(event.target.value); setError(null); }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addRule(); } }} />
        <select aria-label="新规则同步方式" className={fieldClass} value={mode} onChange={(event) => setMode(event.target.value as PathSyncRule["sync_mode"])}><ModeOptions /></select>
        <button type="button" className={buttonClass} onClick={addRule}>添加规则</button>
      </fieldset>
      {error ? <p role="alert" className="mt-2 text-xs text-[#be123c]">{error}</p> : null}
      <div className="mt-3 max-h-56 overflow-y-auto divide-y divide-[#edf3fb]">
        {rules.map((rule, index) => {
          const Icon = rule.kind === "folder" ? IconFolder : IconFileText;
          return <div key={rule.path} className="flex items-center gap-2 py-2">
            <Icon className="h-4 w-4 shrink-0 text-[#3370ff]" />
            <div className="min-w-0 flex-1"><p className="truncate font-mono text-xs text-[#334762]" title={rule.path}>{rule.path}</p><p className="mt-0.5 text-[10px] text-[#7e91a8]">{rule.kind === "folder" ? "包含所有子项和后续新增文件" : "仅此文档 / 文件"}</p></div>
            <select className={fieldClass} aria-label={`${rule.path} 的同步方式`} value={rule.sync_mode} disabled={disabled} onChange={(event) => onChange(rules.map((item, itemIndex) => itemIndex === index ? { ...item, sync_mode: event.target.value as PathSyncRule["sync_mode"] } : item))}><ModeOptions /></select>
            <button type="button" className="shrink-0 text-xs text-[#52657a] hover:text-[#3370ff]" disabled={disabled} aria-label={`${rule.path} 恢复继承`} onClick={() => onChange(rules.filter((_, itemIndex) => itemIndex !== index))}>恢复继承</button>
          </div>;
        })}
      </div>
      <p className="mt-2 text-[11px] leading-5 text-[#7e91a8]">规则按任务内相对路径定位，移动或重命名后需调整。添加后统一保存生效。</p>
    </section>
  );
}
