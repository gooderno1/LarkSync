import type { RuntimeView } from "../../lib/syncRuntime";

export function RuntimeProgress({ view }: { view: RuntimeView }) {
  return (
    <div className="min-w-0 space-y-1.5" data-runtime-progress="true">
      <p className="text-xs leading-5 text-[#52657a]">{view.countLabel}</p>
      {view.progress !== null && (
        <div
          role="progressbar" aria-label="本阶段处理进度"
          aria-valuemin={0} aria-valuemax={100} aria-valuenow={view.progress}
          aria-valuetext={view.countLabel}
          className="h-1.5 w-full overflow-hidden rounded-full bg-[#dce8f8]"
        >
          <div className={`h-full rounded-full ${view.stale ? "bg-[#94a3b8]" : "bg-[#3370ff]"}`} style={{ width: `${view.progress}%` }} />
        </div>
      )}
    </div>
  );
}
