import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TasksPage } from "./TasksPage";

vi.mock("../hooks/useTasks", () => ({
  useTasks: () => ({
    tasks: [],
    taskLoading: false,
    taskError: null,
    statusMap: {},
    refreshTasks: vi.fn(),
    toggleTask: vi.fn(),
    updateSyncMode: vi.fn(),
    updateMode: vi.fn(),
    updateMdSyncMode: vi.fn(),
    updateDeletePolicy: vi.fn(),
    runTask: vi.fn(),
    deleteTask: vi.fn(),
  }),
}));

vi.mock("../hooks/useConflicts", () => ({
  useConflicts: () => ({
    conflicts: [],
  }),
}));

vi.mock("../components/ui/toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock("../components/ThemeToggle", () => ({
  ThemeToggle: () => <div>Theme Toggle</div>,
}));

vi.mock("../components/NewTaskModal", () => ({
  NewTaskModal: () => null,
}));

describe("TasksPage smoke", () => {
  it("renders task management shell and empty state", () => {
    const html = renderToStaticMarkup(<TasksPage />);

    expect(html).toContain("同步任务");
    expect(html).toContain("暂无同步任务");
  });
});
