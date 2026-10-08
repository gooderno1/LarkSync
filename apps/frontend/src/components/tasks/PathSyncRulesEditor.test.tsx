// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { PathSyncRulesEditor } from "./PathSyncRulesEditor";
import type { PathSyncRule, SyncTask } from "../../types";

const task = { id: "t", local_path: "D:/Docs", sync_mode: "bidirectional" } as SyncTask;

function Editor() {
  const [rules, setRules] = useState<PathSyncRule[]>([]);
  return <><PathSyncRulesEditor task={task} rules={rules} onChange={setRules} /><output data-testid="rules">{JSON.stringify(rules)}</output></>;
}

afterEach(cleanup);

describe("PathSyncRulesEditor", () => {
  it("adds a fixed document, changes its direction and restores inheritance", () => {
    render(<Editor />);
    fireEvent.change(screen.getByLabelText("规则相对路径"), { target: { value: "归档/设计.md" } });
    fireEvent.change(screen.getByLabelText("新规则同步方式"), { target: { value: "download_only" } });
    fireEvent.click(screen.getByRole("button", { name: "添加规则" }));
    expect(screen.getByTestId("rules").textContent).toContain('"sync_mode":"download_only"');
    fireEvent.change(screen.getByLabelText("归档/设计.md 的同步方式"), { target: { value: "upload_only" } });
    expect(screen.getByTestId("rules").textContent).toContain('"sync_mode":"upload_only"');
    fireEvent.click(screen.getByRole("button", { name: "归档/设计.md 恢复继承" }));
    expect(screen.getByTestId("rules").textContent).toBe("[]");
  });
  it("rejects paths outside the task and duplicate targets", () => {
    render(<Editor />);
    fireEvent.change(screen.getByLabelText("规则相对路径"), { target: { value: "../outside.md" } });
    fireEvent.click(screen.getByRole("button", { name: "添加规则" }));
    expect(screen.getByRole("alert").textContent).toContain("相对路径");
    expect(screen.getByTestId("rules").textContent).toBe("[]");
    fireEvent.change(screen.getByLabelText("规则相对路径"), { target: { value: "one.md" } });
    fireEvent.click(screen.getByRole("button", { name: "添加规则" }));
    fireEvent.change(screen.getByLabelText("规则相对路径"), { target: { value: "one.md" } });
    fireEvent.click(screen.getByRole("button", { name: "添加规则" }));
    expect(screen.getByRole("alert").textContent).toContain("已有规则");
  });
});
