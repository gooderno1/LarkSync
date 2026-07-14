import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  IconActivity,
  IconAlertTriangle,
  IconArrowDown,
  IconArrowRightLeft,
  IconCircleCheck,
  IconCloud,
  IconCopy,
  IconDatabase,
  IconFileText,
  IconFolder,
  IconMaintenance,
  IconPlay,
  IconRefresh,
  IconShieldCheck,
} from "../Icons";
import { cn } from "../../lib/utils";

type Tone = "blue" | "green" | "amber" | "red" | "gray";

const toneClasses: Record<Tone, string> = {
  blue: "border-[#3370ff]/25 bg-[#eef5ff] text-[#2456d6]",
  green: "border-[#10b981]/25 bg-[#ecfdf5] text-[#047857]",
  amber: "border-[#f59e0b]/30 bg-[#fffbeb] text-[#b45309]",
  red: "border-[#f43f5e]/25 bg-[#fff1f2] text-[#be123c]",
  gray: "border-[#d7e4f5] bg-[#f7faff] text-[#52657a]",
};

function DemoBadge() {
  return (
    <span className="inline-flex h-7 items-center gap-1.5 rounded-full border border-[#9ec2ff] bg-[#eef5ff] px-3 text-[11px] font-semibold text-[#2456d6]">
      <span className="h-1.5 w-1.5 rounded-full bg-[#3370ff]" />
      前端演示数据
    </span>
  );
}

function Pill({ children, tone = "gray" }: { children: ReactNode; tone?: Tone }) {
  return <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold", toneClasses[tone])}>{children}</span>;
}

function PageHeader({ title, description, action }: { title: string; description: string; action: ReactNode }) {
  return (
    <header className="flex min-w-0 items-end justify-between gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-[#102033]">{title}</h1>
          <DemoBadge />
        </div>
        <p className="mt-1 text-sm text-[#52657a]">{description}</p>
      </div>
      {action}
    </header>
  );
}

function PanelHeading({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex min-w-0 items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-[#102033]">{title}</h2>
        {hint ? <p className="mt-1 text-xs leading-5 text-[#6b7f96]">{hint}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

const activityTasks = [
  { id: "market", name: "市场资料备份", path: "D:/Work/Marketing", state: "同步中", tone: "blue" as Tone },
  { id: "knowledge", name: "个人知识库", path: "D:/Notes/Knowledge", state: "2 个问题", tone: "red" as Tone },
  { id: "project", name: "产品项目资料", path: "D:/Projects/LarkSync", state: "已同步", tone: "green" as Tone },
  { id: "archive", name: "历史资料归档", path: "D:/Archive/2025", state: "待删除", tone: "amber" as Tone },
];

const activityRuns = [
  { id: "run-0714-1741", time: "今天 17:41", state: "存在问题", tone: "red" as Tone, stats: "上 12 · 下 8 · 失败 2" },
  { id: "run-0714-1620", time: "今天 16:20", state: "已完成", tone: "green" as Tone, stats: "上 6 · 下 14 · 失败 0" },
  { id: "run-0714-1432", time: "今天 14:32", state: "已完成", tone: "green" as Tone, stats: "上 4 · 下 3 · 失败 0" },
  { id: "run-0714-1105", time: "今天 11:05", state: "已取消", tone: "gray" as Tone, stats: "上 1 · 下 0 · 取消 1" },
  { id: "run-0713-2318", time: "昨天 23:18", state: "存在冲突", tone: "amber" as Tone, stats: "上 18 · 下 21 · 冲突 1" },
  { id: "run-0713-2012", time: "昨天 20:12", state: "已完成", tone: "green" as Tone, stats: "上 9 · 下 11 · 失败 0" },
  { id: "run-0713-1745", time: "昨天 17:45", state: "已完成", tone: "green" as Tone, stats: "上 3 · 下 7 · 失败 0" },
];

const activityEvents = [
  { id: "evt-1", time: "17:41:26", title: "季度方案.md", path: "市场活动/2026/季度方案.md", label: "文档写入失败", tone: "red" as Tone, summary: "飞书文档写入权限不足，当前文件尚未同步到云端。", cause: "应用缺少 docx:document 写入权限，或当前文档未授权给应用。", action: "检查飞书应用权限并重新授权，然后重试当前任务。" },
  { id: "evt-2", time: "17:41:10", title: "品牌手册.md", path: "品牌资产/品牌手册.md", label: "本地与云端冲突", tone: "amber" as Tone, summary: "本地和云端在上次同步后均发生修改。", cause: "两个版本的内容哈希均偏离上次同步基线。", action: "进入冲突处理，对比两侧版本后选择保留内容。" },
  { id: "evt-3", time: "17:40:52", title: "旧版海报.png", path: "市场活动/素材/旧版海报.png", label: "待删除", tone: "amber" as Tone, summary: "文件进入安全删除宽限期，尚未执行删除。", cause: "任务启用了安全删除策略，删除动作延迟 24 小时。", action: "确认文件不再需要；若为误删，可在宽限期内恢复。" },
  { id: "evt-4", time: "17:40:31", title: "活动预算.xlsx", path: "市场活动/预算/活动预算.xlsx", label: "文件被占用", tone: "red" as Tone, summary: "本地文件正被 WPS 占用，无法写入最新云端版本。", cause: "Windows 返回共享冲突，写入重试已达到上限。", action: "关闭占用文件的应用后，重新运行同步任务。" },
  { id: "evt-5", time: "17:39:48", title: "发布排期.md", path: "市场活动/计划/发布排期.md", label: "任务已取消", tone: "gray" as Tone, summary: "用户在扫描阶段暂停了任务，本次运行已安全结束。", cause: "任务收到手动停止信号。", action: "确认本地文件状态后，按需重新启动任务。" },
  { id: "evt-6", time: "17:39:22", title: "合作方清单.md", path: "市场活动/合作/合作方清单.md", label: "云端目标失效", tone: "red" as Tone, summary: "原云端文档已被移动或删除，现有映射无法继续使用。", cause: "飞书接口返回目标不存在。", action: "确认云端位置；必要时重置该任务的同步映射。" },
  { id: "evt-7", time: "17:38:57", title: "新品发布会.md", path: "市场活动/发布/新品发布会.md", label: "镜像目录无权限", tone: "red" as Tone, summary: "增强 Markdown 镜像目录无法创建，文档回写已暂停。", cause: "应用对目标云端目录没有创建子目录的权限。", action: "向应用开放目标目录编辑权限，或改用仅下载模式。" },
  { id: "evt-8", time: "17:38:16", title: "媒体名单.csv", path: "市场活动/媒体/媒体名单.csv", label: "格式待确认", tone: "blue" as Tone, summary: "非 Markdown 文件准备走上传覆盖流程，等待确认目标映射。", cause: "历史映射缺少最新云端版本标识。", action: "确认目标文件后重新建立映射，再继续上传。" },
];

export function ActivityIssuesShowcasePage() {
  const [selectedTask, setSelectedTask] = useState(activityTasks[0].id);
  const [selectedRun, setSelectedRun] = useState(activityRuns[0].id);
  const [selectedEvent, setSelectedEvent] = useState(activityEvents[0].id);
  const event = activityEvents.find((item) => item.id === selectedEvent) ?? activityEvents[0];

  return (
    <section data-showcase-page="activity" className="grid h-full min-h-[760px] grid-rows-[auto_minmax(0,1fr)] gap-4 animate-fade-up">
      <PageHeader
        title="活动与问题"
        description="从任务运行到具体文件，集中诊断同步异常并完成处理。"
        action={<button className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#bfd3ee] bg-white px-4 text-xs font-semibold text-[#3370ff]"><IconRefresh className="h-3.5 w-3.5" />刷新诊断</button>}
      />

      <div data-workspace-fill="true" className="grid min-h-0 grid-rows-[68px_minmax(0,1fr)] overflow-hidden rounded-xl border border-[#cdddf0] bg-white shadow-[0_16px_40px_rgba(51,112,255,0.08)]">
        <div className="grid grid-cols-[176px_minmax(0,1fr)_auto] items-center gap-4 border-b border-[#dce7f4] bg-[#fbfdff] px-4">
          <div>
            <p className="text-sm font-semibold text-[#102033]">任务上下文</p>
            <p className="mt-1 text-xs text-[#6b7f96]">4 个任务 · 2 个需关注</p>
          </div>
          <div className="flex min-w-0 gap-2 overflow-x-auto py-2">
            {activityTasks.map((task) => (
              <button key={task.id} onClick={() => setSelectedTask(task.id)} className={cn("flex h-10 min-w-[180px] items-center justify-between rounded-lg border px-3 text-left", selectedTask === task.id ? "border-[#7ba7ff] bg-[#eef5ff]" : "border-[#d7e4f5] bg-white")}>
                <span className="truncate text-xs font-semibold text-[#102033]">{task.name}</span><Pill tone={task.tone}>{task.state}</Pill>
              </button>
            ))}
          </div>
          <span className="truncate font-mono text-xs text-[#52657a]">{activityTasks.find((task) => task.id === selectedTask)?.path}</span>
        </div>

        <div className="grid min-h-0 grid-cols-[272px_minmax(0,1fr)_336px]">
          <aside className="min-h-0 overflow-y-auto border-r border-[#dce7f4] bg-[#fbfdff] p-4">
            <PanelHeading title="运行历史" hint="最近 24 小时共运行 5 次" />
            <div className="mt-4 grid gap-2 overflow-y-auto">
              {activityRuns.map((run) => (
                <button key={run.id} onClick={() => setSelectedRun(run.id)} className={cn("rounded-lg border p-3 text-left", selectedRun === run.id ? "border-[#7ba7ff] bg-[#eef5ff]" : "border-[#d7e4f5] bg-white")}>
                  <div className="flex items-start justify-between gap-2"><div><p className="font-mono text-xs font-semibold text-[#102033]">{run.id}</p><p className="mt-1 text-[11px] text-[#6b7f96]">{run.time}</p></div><Pill tone={run.tone}>{run.state}</Pill></div>
                  <p className="mt-2 text-[11px] text-[#52657a]">{run.stats}</p>
                </button>
              ))}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 border-t border-[#dce7f4] pt-3 text-center">
              {[['20', '传输'], ['2', '失败'], ['1', '冲突']].map(([value, label]) => <div key={label}><p className="text-sm font-semibold text-[#102033]">{value}</p><p className="text-[10px] text-[#6b7f96]">{label}</p></div>)}
            </div>
          </aside>

          <main className="grid min-h-0 grid-rows-[150px_minmax(0,1fr)] border-r border-[#dce7f4]">
            <section className="border-b border-[#dce7f4] p-4">
              <PanelHeading title="问题概览" hint="运行 run-0714-1741 · 6 个问题事件" />
              <div className="mt-3 grid grid-cols-4 gap-3">
                {[['2', '同步失败', 'red'], ['1', '版本冲突', 'amber'], ['1', '待删除', 'amber'], ['2', '需人工检查', 'blue']].map(([value, label, tone]) => (
                  <div key={label} className={cn("rounded-lg border p-3", toneClasses[tone as Tone])}><p className="text-xl font-semibold">{value}</p><p className="mt-1 text-xs font-semibold">{label}</p></div>
                ))}
              </div>
            </section>
            <section className="min-h-0 p-4">
              <PanelHeading title="事件时间线" hint="按发生时间显示需要关注的文件事件" action={<span className="text-xs font-medium text-[#3370ff]">6 条事件</span>} />
              <div className="mt-3 h-[calc(100%-52px)] space-y-2 overflow-y-auto pr-1">
                {activityEvents.map((item) => (
                  <button data-demo-event={item.id} key={item.id} onClick={() => setSelectedEvent(item.id)} className={cn("grid w-full grid-cols-[58px_minmax(0,1fr)_auto] items-start gap-3 rounded-lg border px-3 py-2.5 text-left", selectedEvent === item.id ? "border-[#7ba7ff] bg-[#eef5ff]" : "border-[#d7e4f5] bg-white")}>
                    <span className="font-mono text-[11px] text-[#6b7f96]">{item.time}</span>
                    <span className="min-w-0"><span className="block truncate text-xs font-semibold text-[#102033]">{item.title}</span><span className="mt-1 block truncate text-[11px] text-[#6b7f96]">{item.path}</span></span>
                    <Pill tone={item.tone}>{item.label}</Pill>
                  </button>
                ))}
              </div>
            </section>
          </main>

          <aside className="min-h-0 overflow-y-auto bg-[#fbfdff] p-4">
            <PanelHeading title="事件诊断" hint={`${event.time} · ${event.title}`} />
            <div className="mt-4"><Pill tone={event.tone}>{event.label}</Pill><h3 className="mt-3 text-base font-semibold text-[#102033]">{event.summary}</h3></div>
            <div className="mt-4 space-y-3">
              <div className="rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#52657a]">原因</p><p className="mt-2 text-xs leading-5 text-[#334762]">{event.cause}</p></div>
              <div className="rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#52657a]">建议动作</p><p className="mt-2 text-xs leading-5 text-[#334762]">{event.action}</p></div>
              <div className="rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#52657a]">原始路径</p><p className="mt-2 break-all font-mono text-[11px] leading-5 text-[#52657a]">D:/Work/Marketing/{event.path}</p></div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2"><button className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-[#3370ff] text-xs font-semibold text-white"><IconPlay className="h-3.5 w-3.5" />重试任务</button><button className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-[#bfd3ee] bg-white text-xs font-semibold text-[#3370ff]"><IconCopy className="h-3.5 w-3.5" />复制详情</button></div>
            <div className="mt-4 rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#102033]">关联运行</p><dl className="mt-3 grid grid-cols-2 gap-y-2 text-[11px]"><dt className="text-[#6b7f96]">运行 ID</dt><dd className="text-right font-mono text-[#334762]">run-0714-1741</dd><dt className="text-[#6b7f96]">同步模式</dt><dd className="text-right font-semibold text-[#334762]">双向同步</dd><dt className="text-[#6b7f96]">删除策略</dt><dd className="text-right font-semibold text-[#334762]">安全删除</dd><dt className="text-[#6b7f96]">处理优先级</dt><dd className="text-right font-semibold text-[#be123c]">高</dd></dl></div>
          </aside>
        </div>
      </div>
    </section>
  );
}

const conflicts = [
  { id: "c1", name: "产品路线图.md", path: "产品规划/产品路线图.md", time: "今天 17:36", local: "新增桌面端离线队列和冲突保护策略。", cloud: "新增移动端离线访问和共享权限策略。", localMeta: "本地 17:31 · 18.6 KB", cloudMeta: "云端 17:34 · 19.2 KB" },
  { id: "c2", name: "品牌手册.md", path: "品牌资产/品牌手册.md", time: "今天 16:48", local: "主色更新为科技蓝，补充深色背景规范。", cloud: "主色沿用品牌蓝，补充印刷色值规范。", localMeta: "本地 16:42 · 8.4 MB", cloudMeta: "云端 16:47 · 8.1 MB" },
  { id: "c3", name: "客户访谈纪要.md", path: "用户研究/客户访谈纪要.md", time: "今天 14:22", local: "补充客户 A 的本地知识库使用反馈。", cloud: "补充客户 B 的团队协同使用反馈。", localMeta: "本地 14:16 · 32.1 KB", cloudMeta: "云端 14:19 · 31.8 KB" },
  { id: "c4", name: "发布排期.md", path: "市场活动/发布排期.md", time: "昨天 23:07", local: "发布日调整到 7 月 28 日。", cloud: "发布日调整到 7 月 30 日。", localMeta: "本地 昨天 22:58 · 12.4 KB", cloudMeta: "云端 昨天 23:04 · 12.5 KB" },
];

export function ConflictResolutionShowcasePage() {
  const [selectedId, setSelectedId] = useState(conflicts[0].id);
  const selected = conflicts.find((item) => item.id === selectedId) ?? conflicts[0];
  return (
    <section data-showcase-page="conflicts" className="grid h-full min-h-[760px] grid-rows-[auto_minmax(0,1fr)] gap-4 animate-fade-up">
      <PageHeader title="冲突处理" description="对比本地与云端修改，明确覆盖影响后选择保留版本。" action={<button className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#bfd3ee] bg-white px-4 text-xs font-semibold text-[#3370ff]"><IconRefresh className="h-3.5 w-3.5" />刷新队列</button>} />
      <div data-workspace-fill="true" className="grid min-h-0 grid-cols-[260px_minmax(0,1fr)_300px] overflow-hidden rounded-xl border border-[#cdddf0] bg-white shadow-[0_16px_40px_rgba(51,112,255,0.08)]">
        <aside className="min-h-0 border-r border-[#dce7f4] bg-[#fbfdff] p-4">
          <PanelHeading title="冲突队列" hint="4 个文件等待人工决策" action={<Pill tone="amber">需处理</Pill>} />
          <div className="mt-4 space-y-2 overflow-y-auto">
            {conflicts.map((conflict) => <button data-demo-conflict={conflict.id} key={conflict.id} onClick={() => setSelectedId(conflict.id)} className={cn("w-full rounded-lg border p-3 text-left", selectedId === conflict.id ? "border-[#7ba7ff] bg-[#eef5ff]" : "border-[#d7e4f5] bg-white")}><div className="flex items-start gap-2"><IconFileText className="mt-0.5 h-4 w-4 shrink-0 text-[#3370ff]" /><div className="min-w-0"><p className="truncate text-xs font-semibold text-[#102033]">{conflict.name}</p><p className="mt-1 truncate text-[11px] text-[#6b7f96]">{conflict.path}</p></div></div><div className="mt-3 flex items-center justify-between text-[10px] text-[#6b7f96]"><span>{conflict.time}</span><span>本地 + 云端均修改</span></div></button>)}
          </div>
          <div className="mt-4 rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#102033]">处理原则</p><p className="mt-2 text-[11px] leading-5 text-[#52657a]">任何选择都会先保全另一侧版本，避免因为覆盖导致内容丢失。</p></div>
          <div className="mt-3 grid grid-cols-2 gap-2"><div className="rounded-lg border border-[#d7e4f5] bg-white p-3 text-center"><p className="text-lg font-semibold text-[#102033]">4</p><p className="text-[10px] text-[#6b7f96]">待处理</p></div><div className="rounded-lg border border-[#d7e4f5] bg-white p-3 text-center"><p className="text-lg font-semibold text-[#047857]">12</p><p className="text-[10px] text-[#6b7f96]">今日已解决</p></div></div>
          <div className="mt-3 rounded-lg border border-[#b9e8d8] bg-[#f2fbf8] p-3"><p className="text-xs font-semibold text-[#047857]">最近一次处理</p><p className="mt-2 text-[11px] leading-5 text-[#52657a]">17:28 · 采用云端版本 · 合同模板.md</p></div>
        </aside>
        <main className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] border-r border-[#dce7f4]">
          <section className="border-b border-[#dce7f4] p-4"><PanelHeading title="版本对比" hint={selected.path} action={<Pill tone="red">内容冲突</Pill>} /><div className="mt-4 grid grid-cols-2 gap-3"><div className="rounded-lg border border-[#8fb2ee] bg-[#f5f9ff] p-3"><div className="flex items-center justify-between"><span className="text-xs font-semibold text-[#2456d6]">本地版本</span><span className="text-[10px] text-[#6b7f96]">{selected.localMeta}</span></div><p className="mt-3 text-sm leading-6 text-[#243b55]">{selected.local}</p></div><div className="rounded-lg border border-[#8fd7bf] bg-[#f2fbf8] p-3"><div className="flex items-center justify-between"><span className="text-xs font-semibold text-[#047857]">云端版本</span><span className="text-[10px] text-[#6b7f96]">{selected.cloudMeta}</span></div><p className="mt-3 text-sm leading-6 text-[#243b55]">{selected.cloud}</p></div></div></section>
          <section className="min-h-0 p-4"><PanelHeading title="差异内容" hint="以段落为单位标记两侧独立修改" /><div className="mt-3 h-[calc(100%-44px)] overflow-y-auto rounded-lg border border-[#d7e4f5] bg-[#fbfdff] p-4 font-mono text-xs leading-7"><p className="text-[#6b7f96]">@@ 第 18 行至第 24 行 @@</p><p className="mt-3 rounded bg-[#fff1f2] px-3 text-[#be123c]">- {selected.cloud}</p><p className="mt-2 rounded bg-[#ecfdf5] px-3 text-[#047857]">+ {selected.local}</p><p className="mt-4 text-[#52657a]">后续章节结构一致，标题、负责人和里程碑日期未发生变化。</p></div></section>
          <section className="grid grid-cols-4 gap-3 border-t border-[#dce7f4] bg-[#fbfdff] p-4 text-xs"><div><p className="text-[#6b7f96]">同步任务</p><p className="mt-1 font-semibold text-[#102033]">产品项目资料</p></div><div><p className="text-[#6b7f96]">文件类型</p><p className="mt-1 font-semibold text-[#102033]">Markdown</p></div><div><p className="text-[#6b7f96]">基线版本</p><p className="mt-1 font-semibold text-[#102033]">v184</p></div><div><p className="text-[#6b7f96]">保护方式</p><p className="mt-1 font-semibold text-[#102033]">创建冲突副本</p></div></section>
        </main>
        <aside className="min-h-0 overflow-y-auto bg-[#fbfdff] p-4"><PanelHeading title="决策与影响" hint="选择前确认内容流向" /><div className="mt-4 rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#102033]">处理进度</p><div className="mt-3 space-y-3">{[['1', '检测到双向修改', true], ['2', '人工选择保留版本', false], ['3', '写回并重建基线', false]].map(([index, label, done]) => <div key={label as string} className="flex items-center gap-3"><span className={cn("grid h-6 w-6 place-items-center rounded-full text-[10px] font-semibold", done ? "bg-[#ecfdf5] text-[#047857]" : "bg-[#eef5ff] text-[#2456d6]")}>{index as string}</span><span className="text-xs text-[#52657a]">{label as string}</span></div>)}</div></div><div className="mt-4 rounded-lg border border-[#f5d28f] bg-[#fffbeb] p-3"><div className="flex items-center gap-2"><IconAlertTriangle className="h-4 w-4 text-[#b45309]" /><p className="text-xs font-semibold text-[#92400e]">覆盖影响</p></div><p className="mt-2 text-xs leading-5 text-[#78350f]">使用本地将更新当前飞书文档；使用云端将覆盖本地主文件。未选择的一侧会保存为冲突副本。</p></div><div className="mt-4 space-y-3"><button className="w-full rounded-lg bg-[#3370ff] px-4 py-3 text-left text-white"><span className="flex items-center gap-2 text-sm font-semibold"><IconCloud className="h-4 w-4" />使用云端版本</span><span className="mt-1 block text-[11px] text-white/75">云端覆盖本地，保留本地冲突副本</span></button><button className="w-full rounded-lg border border-[#7ba7ff] bg-white px-4 py-3 text-left text-[#2456d6]"><span className="flex items-center gap-2 text-sm font-semibold"><IconFolder className="h-4 w-4" />使用本地版本</span><span className="mt-1 block text-[11px] text-[#6b7f96]">本地写回云端，保留云端历史版本</span></button></div><button className="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-[#c9d8ec] bg-white text-xs font-semibold text-[#52657a]"><IconCopy className="h-3.5 w-3.5" />复制冲突详情</button><div className="mt-4 rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#102033]">安全机制</p><ul className="mt-2 space-y-2 text-[11px] leading-5 text-[#52657a]"><li>· 未选版本不会写入任何一侧</li><li>· 覆盖前创建带时间戳的冲突副本</li><li>· 完成后重新记录双方内容哈希</li></ul></div></aside>
      </div>
    </section>
  );
}

const settingRules = [
  { id: "r1", task: "市场资料备份", path: "node_modules", type: "双向忽略" },
  { id: "r2", task: "产品项目资料", path: ".git / dist / build", type: "本地忽略" },
  { id: "r3", task: "个人知识库", path: "assets/cache", type: "双向忽略" },
];

export function SettingsShowcasePage() {
  const [mode, setMode] = useState("bidirectional");
  const [saved, setSaved] = useState(false);
  return (
    <section data-showcase-page="settings" className="grid h-full min-h-[760px] grid-rows-[auto_minmax(0,1fr)] gap-4 animate-fade-up">
      <PageHeader title="设置" description="统一管理账号、设备、默认同步策略与数据保护规则。" action={<button onClick={() => setSaved(true)} className="h-9 rounded-lg bg-[#3370ff] px-4 text-xs font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.22)]">{saved ? "设置已保存" : "保存设置"}</button>} />
      <div data-workspace-fill="true" className="grid min-h-0 grid-cols-[minmax(0,1.16fr)_minmax(390px,0.84fr)] overflow-hidden rounded-xl border border-[#cdddf0] bg-white shadow-[0_16px_40px_rgba(51,112,255,0.08)]">
        <main className="min-h-0 overflow-y-auto border-r border-[#dce7f4] p-5">
          <section><PanelHeading title="账号与当前设备" hint="账号授权和设备归属共同决定本机可见任务" action={<Pill tone="green">连接正常</Pill>} /><div className="mt-4 grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] overflow-hidden rounded-lg border border-[#d7e4f5]"><div className="flex items-center gap-4 border-r border-[#d7e4f5] bg-[#fbfdff] p-4"><span className="grid h-11 w-11 place-items-center rounded-full bg-[#ecfdf5] text-[#047857]"><IconCircleCheck className="h-6 w-6" /></span><div><p className="text-sm font-semibold text-[#102033]">飞书已连接</p><p className="mt-1 text-xs text-[#52657a]">聂玮奇 · 云空间权限正常</p></div></div><div className="p-4"><div className="grid grid-cols-[92px_minmax(0,1fr)] gap-y-2 text-xs"><span className="text-[#6b7f96]">设备名称</span><span className="font-semibold text-[#102033]">PC_XH · Windows 桌面端</span><span className="text-[#6b7f96]">设备 ID</span><span className="truncate font-mono text-[#52657a]">dev-52eaeb7d1d28d1747df4e1</span><span className="text-[#6b7f96]">隔离规则</span><span className="text-[#52657a]">任务按设备 ID 隔离</span></div></div></div></section>
          <section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="默认同步策略" hint="新建任务时使用，任务仍可单独调整" /><div className="mt-4 grid grid-cols-3 gap-3">{[{id:'bidirectional', icon:<IconArrowRightLeft className="h-5 w-5" />, title:'双向同步', desc:'本地与云端双向更新'}, {id:'download', icon:<IconArrowDown className="h-5 w-5" />, title:'仅下载', desc:'仅从云端拉取到本地'}, {id:'upload', icon:<IconCloud className="h-5 w-5" />, title:'仅上传', desc:'仅从本地推送到云端'}].map((item) => <button key={item.id} onClick={() => setMode(item.id)} className={cn("rounded-lg border p-4 text-left", mode === item.id ? "border-[#7ba7ff] bg-[#eef5ff] text-[#2456d6]" : "border-[#d7e4f5] bg-white text-[#52657a]")}><span className="flex items-center gap-2 text-sm font-semibold">{item.icon}{item.title}</span><span className="mt-2 block text-[11px] leading-5 text-[#6b7f96]">{item.desc}</span></button>)}</div><div className="mt-4 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_180px] gap-3 rounded-lg border border-[#d7e4f5] bg-[#fbfdff] p-4 text-xs"><div><p className="text-[#6b7f96]">上行计划</p><p className="mt-1 font-semibold text-[#102033]">文件变更后 60 秒</p></div><div><p className="text-[#6b7f96]">下行计划</p><p className="mt-1 font-semibold text-[#102033]">每天 01:00</p></div><div><p className="text-[#6b7f96]">删除策略</p><p className="mt-1 font-semibold text-[#102033]">安全删除 · 宽限 24h</p></div></div></section>
          <section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="高级 OAuth" hint="仅在更换应用凭证或授权端点时修改" action={<button className="text-xs font-semibold text-[#3370ff]">查看配置教程 ↗</button>} /><div className="mt-4 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.1fr)] gap-3"><label className="text-xs font-medium text-[#52657a]">App ID<input className="mt-1 h-9 w-full rounded-lg border border-[#bfd3ee] px-3 text-sm text-[#102033]" value="cli_a9f0b2be1d38dcb0" readOnly /></label><label className="text-xs font-medium text-[#52657a]">App Secret<input className="mt-1 h-9 w-full rounded-lg border border-[#bfd3ee] px-3 text-sm text-[#8a9bb0]" value="保存后自动清空" readOnly /></label><label className="text-xs font-medium text-[#52657a]">Redirect URI<input className="mt-1 h-9 w-full rounded-lg border border-[#bfd3ee] px-3 text-sm text-[#102033]" value="http://localhost:13666/auth/callback" readOnly /></label></div></section>
          <section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="本地目录与缓存" hint="本机运行文件位置，仅影响当前设备" /><div className="mt-3 grid grid-cols-3 gap-3">{[['工作目录', 'D:/LarkSync/Data'], ['图片缓存', 'D:/LarkSync/Cache/assets'], ['系统日志', 'D:/LarkSync/Logs']].map(([label,path]) => <div key={label} className="rounded-lg border border-[#d7e4f5] bg-[#fbfdff] p-3"><div className="flex items-center gap-2"><IconFolder className="h-4 w-4 text-[#3370ff]" /><p className="text-xs font-semibold text-[#102033]">{label}</p></div><p className="mt-2 truncate font-mono text-[11px] text-[#52657a]">{path}</p><button className="mt-2 text-[11px] font-semibold text-[#3370ff]">打开目录</button></div>)}</div></section>
        </main>
        <aside className="min-h-0 overflow-y-auto bg-[#fbfdff] p-5"><PanelHeading title="配置状态" hint="当前设备的安全与同步配置摘要" /><div className="mt-4 grid grid-cols-2 gap-3">{[[<IconShieldCheck className="h-5 w-5" />, '凭证存储', '系统 Keyring', 'green'], [<IconDatabase className="h-5 w-5" />, '状态数据库', 'SQLite 正常', 'green'], [<IconActivity className="h-5 w-5" />, '同步任务', '4 个已启用', 'blue'], [<IconRefresh className="h-5 w-5" />, '默认策略', '双向同步', 'blue']].map(([icon,label,value,tone]) => <div key={label as string} className={cn("rounded-lg border p-3", toneClasses[tone as Tone])}><div className="flex items-center gap-2">{icon as ReactNode}<span className="text-xs font-semibold">{label as string}</span></div><p className="mt-2 text-sm font-semibold text-[#102033]">{value as string}</p></div>)}</div><section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="忽略规则" hint="3 条任务级规则正在生效" action={<button className="text-xs font-semibold text-[#3370ff]">管理规则</button>} /><div className="mt-3 space-y-2">{settingRules.map((rule) => <div data-demo-rule={rule.id} key={rule.id} className="rounded-lg border border-[#d7e4f5] bg-white p-3"><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold text-[#102033]">{rule.task}</span><Pill tone="gray">{rule.type}</Pill></div><p className="mt-2 truncate font-mono text-[11px] text-[#52657a]">{rule.path}</p></div>)}</div></section><section className="mt-5 rounded-lg border border-[#b9e8d8] bg-[#f2fbf8] p-4"><div className="flex items-center gap-2 text-[#047857]"><IconShieldCheck className="h-5 w-5" /><p className="text-sm font-semibold">数据保护已启用</p></div><ul className="mt-3 space-y-2 text-xs leading-5 text-[#52657a]"><li>· OAuth Token 仅存储于系统凭证库</li><li>· 云端始终作为冲突判定事实来源</li><li>· 覆盖前自动创建冲突副本</li></ul></section><section className="mt-4 rounded-lg border border-[#d7e4f5] bg-white p-3"><div className="flex items-center justify-between"><p className="text-xs font-semibold text-[#102033]">最近保存</p><Pill tone="green">已同步</Pill></div><p className="mt-2 text-[11px] leading-5 text-[#52657a]">今天 17:38 · 默认策略与 3 条忽略规则已写入当前设备配置。</p></section></aside>
      </div>
    </section>
  );
}

const maintenanceTasks = ["市场资料备份", "产品项目资料", "历史资料归档"];

export function MaintenanceShowcasePage() {
  const [showTasks, setShowTasks] = useState(false);
  const [checking, setChecking] = useState(false);
  const stepStates = useMemo(() => ["校验通过", "等待确认", "等待 helper", "等待安装", "等待重启"], []);
  return (
    <section data-showcase-page="maintenance" className="grid h-full min-h-[760px] grid-rows-[auto_minmax(0,1fr)] gap-4 animate-fade-up">
      <PageHeader title="更新与维护" description="查看版本状态、安装交接、运行环境和维护工具。" action={<button onClick={() => setChecking((value) => !value)} className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#3370ff] px-4 text-xs font-semibold text-white shadow-[0_10px_24px_rgba(51,112,255,0.22)]"><IconRefresh className={cn("h-3.5 w-3.5", checking && "animate-spin")} />{checking ? "正在检查" : "检查更新"}</button>} />
      <div data-workspace-fill="true" className="grid min-h-0 grid-cols-[minmax(0,1fr)_360px] overflow-hidden rounded-xl border border-[#cdddf0] bg-white shadow-[0_16px_40px_rgba(51,112,255,0.08)]">
        <main className="min-h-0 overflow-y-auto border-r border-[#dce7f4] p-5"><PanelHeading title="版本与安装" hint="检测到可用更新，安装前可查看版本内容和交接状态" action={<Pill tone="amber">发现新版本</Pill>} /><div className="mt-4 grid grid-cols-2 gap-4"><div className="rounded-lg border border-[#d7e4f5] bg-[#fbfdff] p-4"><p className="text-xs text-[#6b7f96]">当前版本</p><p className="mt-2 text-2xl font-semibold text-[#102033]">v0.8.0-dev.24</p><p className="mt-2 text-xs text-[#52657a]">上次检查：今天 17:42</p></div><div className="rounded-lg border border-[#f5d28f] bg-[#fffbeb] p-4"><p className="text-xs text-[#92400e]">可用版本</p><p className="mt-2 text-2xl font-semibold text-[#78350f]">v0.8.0-dev.25</p><p className="mt-2 text-xs text-[#92400e]">LarkSync-Setup-v0.8.0-dev.25.exe</p></div></div><div className="mt-4 rounded-lg border border-[#d7e4f5] p-4"><div className="grid grid-cols-[120px_minmax(0,1fr)_120px] gap-4 text-xs"><div><p className="text-[#6b7f96]">安装包大小</p><p className="mt-1 font-semibold text-[#102033]">18.2 MB</p></div><div><p className="text-[#6b7f96]">下载位置</p><p className="mt-1 truncate font-mono text-[#102033]">D:/Downloads/LarkSync-Setup-v0.8.0-dev.25.exe</p></div><div><p className="text-[#6b7f96]">校验状态</p><p className="mt-1 font-semibold text-[#047857]">SHA256 通过</p></div></div><div className="mt-4 flex gap-2"><button className="h-9 rounded-lg bg-[#3370ff] px-4 text-xs font-semibold text-white">下载更新</button><button className="h-9 rounded-lg border border-[#bfd3ee] px-4 text-xs font-semibold text-[#3370ff]">打开安装包目录</button><button className="h-9 rounded-lg border border-[#8fd7bf] bg-[#f2fbf8] px-4 text-xs font-semibold text-[#047857]">静默安装</button></div></div><section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="安装与交接" hint="桌面端退出后由托盘 helper 接管，完成后自动重启" /><div className="mt-4 grid grid-cols-5 gap-3">{stepStates.map((state,index) => <div key={state} className={cn("rounded-lg border p-3 text-center", index === 0 ? toneClasses.green : toneClasses.gray)}><span className="mx-auto grid h-7 w-7 place-items-center rounded-full bg-white text-xs font-semibold">{index + 1}</span><p className="mt-2 text-xs font-semibold">{['校验更新', '托盘接管', 'helper 启动', '静默安装', '自动重启'][index]}</p><p className="mt-1 text-[10px] opacity-80">{state}</p></div>)}</div></section><section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="版本说明" hint="v0.8.0-dev.25 · 设计预览" /><div className="mt-3 grid grid-cols-2 gap-3">{[['四页满画布设计', '活动、冲突、设置和维护页使用完整工作区高度。'], ['演示数据模式', '开发环境可在无后端数据时验证典型状态。'], ['诊断信息增强', '补充问题原因、覆盖影响和处理建议。'], ['危险操作收敛', '重置映射任务继续默认收起。']].map(([title,desc]) => <div key={title} className="rounded-lg border border-[#d7e4f5] bg-[#fbfdff] p-3"><p className="text-xs font-semibold text-[#102033]">{title}</p><p className="mt-2 text-[11px] leading-5 text-[#52657a]">{desc}</p></div>)}</div></section><section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="安装前检查" hint="开始安装前自动核对本机条件" /><div className="mt-3 grid grid-cols-4 gap-3">{[['磁盘空间', '可用 82.4 GB'], ['后台任务', '当前空闲'], ['配置备份', '已完成'], ['重启策略', '安装后自动重启']].map(([label,value]) => <div key={label} className="rounded-lg border border-[#b9e8d8] bg-[#f2fbf8] p-3"><p className="text-[11px] text-[#52657a]">{label}</p><p className="mt-1 text-xs font-semibold text-[#047857]">{value}</p></div>)}</div></section></main>
        <aside className="min-h-0 overflow-y-auto bg-[#fbfdff] p-5"><PanelHeading title="维护设置" hint="日志、更新与本机运行环境" /><div className="mt-4 grid gap-3"><label className="text-xs font-medium text-[#52657a]">同步日志保留天数<input className="mt-1 h-9 w-full rounded-lg border border-[#bfd3ee] px-3 text-sm text-[#102033]" value="30" readOnly /></label><label className="text-xs font-medium text-[#52657a]">系统日志保留天数<input className="mt-1 h-9 w-full rounded-lg border border-[#bfd3ee] px-3 text-sm text-[#102033]" value="14" readOnly /></label><label className="text-xs font-medium text-[#52657a]">日志提醒阈值（MB）<input className="mt-1 h-9 w-full rounded-lg border border-[#bfd3ee] px-3 text-sm text-[#102033]" value="200" readOnly /></label><div className="flex h-10 items-center justify-between rounded-lg border border-[#d7e4f5] bg-white px-3 text-xs text-[#52657a]"><span>自动更新 · 每 24 小时</span><span className="relative h-5 w-9 rounded-full bg-[#3370ff]"><span className="absolute right-0.5 top-0.5 h-4 w-4 rounded-full bg-white" /></span></div><button className="h-9 rounded-lg bg-[#3370ff] text-xs font-semibold text-white">保存维护设置</button></div><section className="mt-5 border-t border-[#dce7f4] pt-5"><PanelHeading title="运行环境" hint="本机核心组件状态" /><div className="mt-3 space-y-2">{[[<IconCircleCheck className="h-4 w-4" />, '后端服务', '127.0.0.1:18000', 'green'], [<IconActivity className="h-4 w-4" />, 'WebSocket', '实时连接', 'green'], [<IconDatabase className="h-4 w-4" />, '状态数据库', 'SQLite 3', 'green']].map(([icon,label,value,tone]) => <div key={label as string} className="flex items-center justify-between rounded-lg border border-[#d7e4f5] bg-white px-3 py-2.5"><span className="flex items-center gap-2 text-xs font-semibold text-[#102033]">{icon as ReactNode}{label as string}</span><Pill tone={tone as Tone}>{value as string}</Pill></div>)}</div></section><section className="mt-5 rounded-lg border border-[#fecdd3] bg-[#fff8f9] p-4"><div className="flex items-center gap-2 text-[#be123c]"><IconMaintenance className="h-5 w-5" /><p className="text-sm font-semibold">重置同步映射</p></div><p className="mt-2 text-xs leading-5 text-[#52657a]">只清除映射关系，不删除本地或飞书文件。</p><button aria-expanded={showTasks} onClick={() => setShowTasks((value) => !value)} className="mt-3 h-9 w-full rounded-lg border border-[#f43f5e]/35 bg-white text-xs font-semibold text-[#e11d48]">{showTasks ? "收起任务列表" : "选择任务重置"}</button>{showTasks ? <div className="mt-3 space-y-2">{maintenanceTasks.map((task) => <div key={task} className="flex items-center justify-between rounded-lg border border-[#fecdd3] bg-white px-3 py-2"><span className="text-xs font-semibold text-[#102033]">{task}</span><button className="text-[11px] font-semibold text-[#e11d48]">重置映射</button></div>)}</div> : null}</section><section className="mt-4 rounded-lg border border-[#d7e4f5] bg-white p-3"><p className="text-xs font-semibold text-[#102033]">最近维护记录</p><div className="mt-2 space-y-2 text-[11px] text-[#52657a]"><p>今天 17:42 · 完成更新检查</p><p>今天 02:00 · 清理 38.6 MB 过期日志</p><p>昨天 18:15 · 完成配置自动备份</p></div></section></aside>
      </div>
    </section>
  );
}
