import type { RuntimeView } from "../../lib/syncRuntime";
import { RuntimeProgress } from "./RuntimeProgress";

export function RuntimeSummary({ view }: { view: RuntimeView }) {
  return (
    <div data-runtime-summary="true" className="min-w-0 space-y-1.5">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        <strong className="text-[#334762]">{view.phaseLabel}</strong>
        <span className="text-[#52657a]">已用时间 {view.elapsedLabel}{view.stale ? "（上次记录）" : ""}</span>
      </div>
      {view.waitLabel && <p role="status" className="text-xs text-[#b45309]">{view.waitLabel}</p>}
      {view.currentItem && <p className="truncate text-xs text-[#52657a]" title={view.currentItem}>{view.operationLabel || "当前处理"} · {view.currentItem}</p>}
      <RuntimeProgress view={view} />
    </div>
  );
}
