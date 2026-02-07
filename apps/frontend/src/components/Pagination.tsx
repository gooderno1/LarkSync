/* ------------------------------------------------------------------ */
/*  通用分页组件 — 页码导航 + 每页条数选择器                              */
/* ------------------------------------------------------------------ */

import { useMemo } from "react";
import { IconChevronLeft, IconChevronRight } from "./Icons";
import { cn } from "../lib/utils";

type PaginationProps = {
  /** 当前页码 (1-based) */
  page: number;
  /** 每页条数 */
  pageSize: number;
  /** 总条数 */
  total: number;
  /** 页码改变回调 */
  onPageChange: (page: number) => void;
  /** 每页条数改变回调 */
  onPageSizeChange?: (size: number) => void;
  /** 可选的每页条数选项 */
  pageSizeOptions?: number[];
  /** 是否显示总数摘要 */
  showTotal?: boolean;
  /** 是否显示每页条数选择器 */
  showSizeChanger?: boolean;
};

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [20, 50, 100],
  showTotal = true,
  showSizeChanger = true,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // 生成要显示的页码范围
  const pageNumbers = useMemo(() => {
    const pages: (number | "...")[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible + 2) {
      // 总页数少，全部显示
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      // 始终显示第一页
      pages.push(1);

      let start = Math.max(2, page - 1);
      let end = Math.min(totalPages - 1, page + 1);

      // 确保至少显示 maxVisible-2 个中间页
      if (end - start < maxVisible - 3) {
        if (start === 2) {
          end = Math.min(totalPages - 1, start + maxVisible - 3);
        } else {
          start = Math.max(2, end - (maxVisible - 3));
        }
      }

      if (start > 2) pages.push("...");
      for (let i = start; i <= end; i++) pages.push(i);
      if (end < totalPages - 1) pages.push("...");

      // 始终显示最后一页
      pages.push(totalPages);
    }

    return pages;
  }, [page, totalPages]);

  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  const btnBase =
    "inline-flex items-center justify-center rounded-md border text-xs font-medium transition min-w-[32px] h-8";
  const btnNormal =
    "border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100";
  const btnActive =
    "border-[#3370FF]/50 bg-[#3370FF]/15 text-[#3370FF]";
  const btnDisabled =
    "border-zinc-800 text-zinc-600 cursor-not-allowed";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
      {/* 左侧：总数信息 */}
      {showTotal ? (
        <p className="text-xs text-zinc-500">
          共 <span className="font-medium text-zinc-300">{total}</span> 条
          {total > 0 ? (
            <span className="ml-1">
              ，当前 {startItem}-{endItem}
            </span>
          ) : null}
        </p>
      ) : (
        <div />
      )}

      {/* 右侧：分页控件 */}
      <div className="flex items-center gap-1.5">
        {/* 每页条数 */}
        {showSizeChanger && onPageSizeChange ? (
          <select
            className="mr-2 h-8 rounded-md border border-zinc-700 bg-zinc-950 px-2 text-xs text-zinc-300 outline-none"
            value={pageSize}
            onChange={(e) => {
              onPageSizeChange(Number(e.target.value));
              onPageChange(1); // 切换条数后回到第一页
            }}
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} 条/页
              </option>
            ))}
          </select>
        ) : null}

        {/* 上一页 */}
        <button
          className={cn(btnBase, "px-2", page <= 1 ? btnDisabled : btnNormal)}
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          type="button"
          title="上一页"
        >
          <IconChevronLeft className="h-3.5 w-3.5" />
        </button>

        {/* 页码 */}
        {pageNumbers.map((p, i) =>
          p === "..." ? (
            <span key={`ellipsis-${i}`} className="px-1 text-xs text-zinc-600">
              …
            </span>
          ) : (
            <button
              key={p}
              className={cn(btnBase, "px-2", p === page ? btnActive : btnNormal)}
              onClick={() => onPageChange(p)}
              type="button"
            >
              {p}
            </button>
          )
        )}

        {/* 下一页 */}
        <button
          className={cn(btnBase, "px-2", page >= totalPages ? btnDisabled : btnNormal)}
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          type="button"
          title="下一页"
        >
          <IconChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
