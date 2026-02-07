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
  const isFolder = node.type === "folder";
  const hasChildren = Boolean(node.children && node.children.length);
  const currentPath = path ? `${path}/${node.name}` : node.name;
  const isSelected = selectedToken === node.token;

  return (
    <li className="space-y-2">
      <div className="flex items-center gap-2">
        {isFolder ? (
          <button
            className="flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700 text-zinc-300 hover:bg-zinc-800"
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
          <span className="ml-2 h-2 w-2 rounded-full bg-zinc-600" />
        )}
        <button
          className={`flex items-center gap-2 text-left text-sm ${
            isSelected ? "font-semibold text-emerald-300" : "text-zinc-200"
          }`}
          disabled={!selectable || !isFolder}
          onClick={() => {
            if (!selectable || !isFolder) return;
            onSelect?.({ token: node.token, name: node.name, path: currentPath });
          }}
          type="button"
        >
          <IconFolder className="h-4 w-4" />
          <span className="truncate">{node.name}</span>
        </button>
        <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-[10px] uppercase tracking-widest text-zinc-500">
          {node.type}
        </span>
        {selectable && isFolder ? (
          <button
            className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
              isSelected
                ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                : "border-zinc-700 text-zinc-400 hover:border-zinc-600"
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
        <ul className="ml-4 space-y-2 border-l border-zinc-800 pl-4">
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
