import { describe, expect, it } from "vitest";
import { effectivePathSyncMode, normalizeRulePath, rulesEqual } from "./pathSyncRules";
import type { PathSyncRule } from "../types";

describe("pathSyncRules", () => {
  const rules: PathSyncRule[] = [
    { path: "归档/草稿.md", kind: "file", sync_mode: "upload_only" },
    { path: "归档", kind: "folder", sync_mode: "download_only" },
  ];
  it("previews file, folder and default inheritance", () => {
    expect(effectivePathSyncMode("bidirectional", rules, "归档/草稿.md")).toBe("upload_only");
    expect(effectivePathSyncMode("bidirectional", rules, "归档/新文档.md")).toBe("download_only");
    expect(effectivePathSyncMode("bidirectional", rules, "归档副本/新文档.md")).toBe("bidirectional");
    expect(rulesEqual(rules, [...rules].reverse())).toBe(true);
    expect(rulesEqual(rules, [])).toBe(false);
  });
  it("normalizes fixed relative paths and rejects escapes", () => {
    expect(normalizeRulePath("归档\\./草稿.md/")).toBe("归档/草稿.md");
    for (const path of ["../one.md", "/root", "C:/docs", "\\\\server\\share", ".", "*.md"]) {
      expect(() => normalizeRulePath(path)).toThrow();
    }
  });
});
