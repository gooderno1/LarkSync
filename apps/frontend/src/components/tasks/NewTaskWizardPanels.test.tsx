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
    expect(html).toContain("共享链接");
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
  });
});
