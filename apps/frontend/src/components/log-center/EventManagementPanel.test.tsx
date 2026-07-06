import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { EventManagementPanel } from "./EventManagementPanel";
import type { SyncLogEntry } from "../../types";

const entries: SyncLogEntry[] = [
  {
    taskId: "task-1",
    taskName: "王远雄 - 工作记录",
    timestamp: 100,
    status: "failed",
    path: "D:/Docs/日常记录 - 王远雄.md",
    message: "创建云端文件夹失败: forbidden. (name=_LarkSync_MD_Mirror)",
    runId: "run-1",
  },
  {
    taskId: "task-1",
    taskName: "王远雄 - 工作记录",
    timestamp: 120,
    status: "failed",
    path: "D:/Docs/平台接入工作具体进展.md",
    message: "创建块失败，已中止替换。飞书返回 code=1770032 msg=forBidden",
    runId: "run-1",
  },
];

describe("EventManagementPanel", () => {
  it("renders a task-diagnostics style issue workspace with concrete explanations", () => {
    const html = renderToStaticMarkup(
      <EventManagementPanel
        eventEntries={entries}
        eventTotal={2}
        eventLoading={false}
        eventError={null}
        eventWarning={null}
        showAllEvents={false}
        setShowAllEvents={vi.fn()}
        refreshEvents={vi.fn()}
        conflicts={[]}
        conflictLoading={false}
        conflictError={null}
        refreshConflicts={vi.fn()}
        queueSummary={{ queued: 0, running: 0, waiting: 0, success: 0, failed: 0 }}
        conflictResolutionStates={{}}
        onResolveConflict={vi.fn()}
        conflictActionLabels={{ use_local: "使用本地", use_cloud: "使用云端" }}
      />,
    );

    expect(html).toContain("事件管理");
    expect(html).toContain("当前任务");
    expect(html).toContain("运行进程");
    expect(html).toContain("具体问题");
    expect(html).toContain("2 类 / 2 条");
    expect(html).toContain("2 类问题");
    expect(html).toContain("权限禁止：云文档内容写入失败");
    expect(html).toContain("权限禁止：云端镜像目录创建失败");
    expect(html).toContain("原因");
    expect(html).toContain("建议动作");
    expect(html).toContain("王远雄 - 工作记录");
  });
});
