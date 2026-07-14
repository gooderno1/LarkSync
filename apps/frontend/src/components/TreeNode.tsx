/* ------------------------------------------------------------------ */
/*  云端目录树节点                                                      */
/* ------------------------------------------------------------------ */

import { useState } from "react";
import type { DriveNode, CloudSelection } from "../types";
import { IconChevronDown, IconChevronRight, IconFolder } from "./Icons";

type TreeNodeProps = {
  node: DriveNode;
  path?: string;
  selectable?: boolean;
  selectedToken?: string | null;
  onSelect?: (selection: CloudSelection) => void;
};

export function TreeNode({
  node,
  path = "",
  selectable = false,
  selectedToken = null,
  onSelect,
}: TreeNodeProps) {
  const [open, setOpen] = useState(true);
  const isFolder = node.type === "folder" || node.type === "root";
  const canSelect = selectable && node.type === "folder";
  const hasChildren = Boolean(node.children && node.children.length);
  const currentPath = node.type === "root" ? path : (path ? `${path}/${node.name}` : node.name);
  const isSelected = selectedToken === node.token;

  return (
    <li className="space-y-2">
      <div className="flex items-center gap-2">
        {isFolder ? (
          <button
            className="flex h-6 w-6 items-center justify-center rounded-full border border-[#c9d8ec] bg-white text-[#52657a] hover:bg-[#eef5ff] hover:text-[#3370ff]"
            onClick={() => setOpen((prev) => !prev)}
            type="button"
          >
            {open ? (
              <IconChevronDown className="h-3.5 w-3.5" />
            ) : (
              <IconChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        ) : (
          <span className="ml-2 h-2 w-2 rounded-full bg-[#9fb2c8]" />
        )}
        <button
          className={`flex items-center gap-2 text-left text-sm ${
            isSelected ? "font-semibold text-[#047857]" : "text-[#334762]"
          }`}
          disabled={!canSelect}
          onClick={() => {
            if (!canSelect) return;
            onSelect?.({ token: node.token, name: node.name, path: currentPath });
          }}
          type="button"
        >
          <IconFolder className="h-4 w-4" />
          <span className="truncate">{node.name}</span>
        </button>
        <span className="rounded-full border border-[#d7e4f5] bg-[#f8fbff] px-2 py-0.5 text-[10px] uppercase tracking-widest text-[#6b7f96]">
          {node.type}
        </span>
        {canSelect ? (
          <button
            className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
              isSelected
                ? "border-[#10b981]/35 bg-[#ecfdf5] text-[#047857]"
                : "border-[#c9d8ec] bg-white text-[#3370ff] hover:bg-[#eef5ff]"
            }`}
            onClick={() =>
              onSelect?.({ token: node.token, name: node.name, path: currentPath })
            }
            type="button"
          >
            选择
          </button>
        ) : null}
      </div>
      {isFolder && hasChildren && open ? (
        <ul className="ml-4 space-y-2 border-l border-[#d7e4f5] pl-4">
          {node.children?.map((child) => (
            <TreeNode
              key={child.token}
              node={child}
              path={currentPath}
              selectable={selectable}
              selectedToken={selectedToken}
              onSelect={onSelect}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
