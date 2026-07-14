import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { NewTaskCloudStep } from "./NewTaskCloudStep";
import { NewTaskLocalStep } from "./NewTaskLocalStep";
import { NewTaskStrategyStep } from "./NewTaskStrategyStep";
import { NewTaskWizardStepIndicator } from "./NewTaskWizardStepIndicator";
import type { DriveNode } from "../../types";

const inputCls = "input";

const tree: DriveNode = {
  token: "root",
  name: "根目录",
  type: "folder",
  children: [],
};

describe("new task wizard panels smoke", () => {
  it("renders wizard step indicator and local/cloud steps", () => {
    const html = renderToStaticMarkup(
      <>
        <NewTaskWizardStepIndicator
          step={2}
          taskLocalPath="C:/docs"
          taskCloudToken="folder"
          maxAccessibleStep={5}
          onSelectStep={vi.fn()}
        />
        <NewTaskLocalStep
          inputCls={inputCls}
          taskName="任务"
          taskLocalPath="C:/docs"
          taskBasePath="C:/"
          folderPickLoading={false}
          folderPickError={null}
          onTaskNameChange={vi.fn()}
          onTaskLocalPathChange={vi.fn()}
          onTaskBasePathChange={vi.fn()}
          onPickLocalFolder={vi.fn()}
        />
        <NewTaskCloudStep
          inputCls={inputCls}
          tree={tree}
          treeLoading={false}
          treeError={null}
          taskCloudToken="folder"
          selectedCloud={{ token: "folder", name: "根目录", path: "根目录" }}
          manualCloudInput=""
          manualCloudName=""
          manualCloudError={null}
          onRefreshTree={vi.fn()}
          onSelectCloudFolder={vi.fn()}
          onManualCloudInputChange={vi.fn()}
          onManualCloudNameChange={vi.fn()}
          onApplyManualCloud={vi.fn()}
        />
      </>
    );

    expect(html).toContain("选择本地目录");
    expect(html).toContain("选择飞书云端目录");
    expect(html).toContain("同步模式");
    expect(html).toContain("删除与忽略");
    expect(html).toContain("确认");
    expect(html).toContain("共享链接");
    expect(html).toContain("高级路径设置");
    expect(html).toContain('aria-current="step"');
    expect(html).toContain("bg-[#f8fbff]");
    expect(html).not.toContain("border-zinc-800");
    expect(html).not.toContain("text-zinc-500");
  });

  it("renders strategy step summary", () => {
    const html = renderToStaticMarkup(
      <NewTaskStrategyStep
        inputCls={inputCls}
        taskName="任务"
        taskLocalPath="C:/docs"
        selectedCloud={{ token: "folder", name: "根目录", path: "根目录" }}
        taskSyncMode="bidirectional"
        taskUpdateMode="auto"
        taskMdSyncMode="enhanced"
        taskDeletePolicy="safe"
        taskDeleteGraceMinutes="30"
        taskEnabled
        error={null}
        onTaskSyncModeChange={vi.fn()}
        onTaskUpdateModeChange={vi.fn()}
        onTaskMdSyncModeChange={vi.fn()}
        onTaskDeletePolicyChange={vi.fn()}
        onTaskDeleteGraceMinutesChange={vi.fn()}
        onTaskEnabledChange={vi.fn()}
      />
    );

    expect(html).toContain("同步模式");
    expect(html).toContain("任务摘要");
    expect(html).toContain("增强 MD 上传");
    expect(html).toContain("关闭联动");
    expect(html).toContain("安全删除");
    expect(html).toContain("严格删除");
    expect(html).toContain('role="switch"');
    expect(html).toContain('aria-checked="true"');
    expect(html).toContain("border-[#d7e4f5]");
    expect(html).not.toContain("bg-zinc-950/50");
  });

  it("renders updated permission guidance for cloud tree errors", () => {
    const html = renderToStaticMarkup(
      <NewTaskCloudStep
        inputCls={inputCls}
        tree={null}
        treeLoading={false}
        treeError="权限不足"
        taskCloudToken=""
        selectedCloud={null}
        manualCloudInput=""
        manualCloudName=""
        manualCloudError={null}
        onRefreshTree={vi.fn()}
        onSelectCloudFolder={vi.fn()}
        onManualCloudInputChange={vi.fn()}
        onManualCloudNameChange={vi.fn()}
        onApplyManualCloud={vi.fn()}
      />,
    );

    expect(html).toContain("docx:document");
    expect(html).toContain("docx:document.block:convert");
  });

  it("disables inaccessible future steps", () => {
    const html = renderToStaticMarkup(
      <NewTaskWizardStepIndicator
        step={1}
        taskLocalPath=""
        taskCloudToken=""
        maxAccessibleStep={1}
        onSelectStep={vi.fn()}
      />,
    );

    expect((html.match(/disabled=""/g) || [])).toHaveLength(4);
  });
});
