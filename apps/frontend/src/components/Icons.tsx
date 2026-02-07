/* ------------------------------------------------------------------ */
/*  SVG 图标集 - 统一管理，后续可替换为 lucide-react                     */
/* ------------------------------------------------------------------ */

import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;

const base: P = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export const IconDashboard = (p: P) => (
  <svg {...base} {...p}>
    <rect x="3" y="3" width="8" height="8" rx="1.6" />
    <rect x="13" y="3" width="8" height="5" rx="1.6" />
    <rect x="13" y="10" width="8" height="11" rx="1.6" />
    <rect x="3" y="13" width="8" height="8" rx="1.6" />
  </svg>
);

export const IconTasks = (p: P) => (
  <svg {...base} {...p}>
    <path d="M3 7.5h6l2 2h10v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-10a2 2 0 0 1 2-2z" />
  </svg>
);

export const IconConflicts = (p: P) => (
  <svg {...base} {...p}>
    <path d="M12 3l9 16H3z" />
    <path d="M12 9v4" />
    <path d="M12 17h.01" />
  </svg>
);

export const IconSettings = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="3.5" />
    <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.7l.1.1a2 2 0 0 1-1.4 3.4h-.2a1.6 1.6 0 0 0-1.6 1.1l-.1.2a2 2 0 0 1-3.6 0l-.1-.2a1.6 1.6 0 0 0-1.6-1.1H9.8a2 2 0 0 1-1.4-3.4l.1-.1a1.6 1.6 0 0 0 .3-1.7 1.6 1.6 0 0 0-1.3-1.1l-.2-.1a2 2 0 0 1 0-3.6l.2-.1a1.6 1.6 0 0 0 1.3-1.1 1.6 1.6 0 0 0-.3-1.7l-.1-.1A2 2 0 0 1 9.8 3h.2a1.6 1.6 0 0 0 1.6-1.1l.1-.2a2 2 0 0 1 3.6 0l.1.2A1.6 1.6 0 0 0 17 3h.2a2 2 0 0 1 1.4 3.4l-.1.1a1.6 1.6 0 0 0-.3 1.7 1.6 1.6 0 0 0 1.3 1.1l.2.1a2 2 0 0 1 0 3.6l-.2.1a1.6 1.6 0 0 0-1.3 1.1z" />
  </svg>
);

export const IconPlus = (p: P) => (
  <svg {...base} strokeWidth={1.8} {...p}>
    <path d="M12 5v14" />
    <path d="M5 12h14" />
  </svg>
);

export const IconRefresh = (p: P) => (
  <svg {...base} {...p}>
    <path d="M20 12a8 8 0 1 1-2.3-5.6" />
    <path d="M20 4v6h-6" />
  </svg>
);

export const IconPlay = (p: P) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...p}>
    <path d="M8 5.5v13l10-6.5-10-6.5z" />
  </svg>
);

export const IconPause = (p: P) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...p}>
    <path d="M7 5h4v14H7zM13 5h4v14h-4z" />
  </svg>
);

export const IconTrash = (p: P) => (
  <svg {...base} {...p}>
    <path d="M3 6h18" />
    <path d="M8 6V4h8v2" />
    <path d="M6 6l1 14h10l1-14" />
  </svg>
);

export const IconArrowRightLeft = (p: P) => (
  <svg {...base} {...p}>
    <path d="M7 7h12l-3-3" />
    <path d="M17 17H5l3 3" />
  </svg>
);

export const IconArrowDown = (p: P) => (
  <svg {...base} {...p}>
    <path d="M12 4v12" />
    <path d="M8 12l4 4 4-4" />
  </svg>
);

export const IconArrowUp = (p: P) => (
  <svg {...base} {...p}>
    <path d="M12 20V8" />
    <path d="M8 12l4-4 4 4" />
  </svg>
);

export const IconFolder = (p: P) => (
  <svg {...base} {...p}>
    <path d="M3 7.5h6l2 2h10v8.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-10a2 2 0 0 1 2-2z" />
  </svg>
);

export const IconCloud = (p: P) => (
  <svg {...base} {...p}>
    <path d="M7 18a4 4 0 0 1 .5-8 6 6 0 0 1 11.2 1.7A3.5 3.5 0 1 1 18 18H7z" />
  </svg>
);

export const IconChevronDown = (p: P) => (
  <svg {...base} {...p}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);

export const IconChevronRight = (p: P) => (
  <svg {...base} {...p}>
    <path d="M9 6l6 6-6 6" />
  </svg>
);

export const IconChevronLeft = (p: P) => (
  <svg {...base} {...p}>
    <path d="M15 6l-6 6 6 6" />
  </svg>
);

export const IconExternalLink = (p: P) => (
  <svg {...base} {...p}>
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <path d="M15 3h6v6" />
    <path d="M10 14L21 3" />
  </svg>
);

export const IconCopy = (p: P) => (
  <svg {...base} {...p}>
    <rect x="9" y="9" width="13" height="13" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

export const IconSun = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
  </svg>
);

export const IconMoon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
);

export const IconActivity = (p: P) => (
  <svg {...base} {...p}>
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
  </svg>
);

/** 根据同步模式渲染图标 */
export function ModeIcon({ mode, className }: { mode: string; className?: string }) {
  const cls = className || "h-4 w-4";
  if (mode === "download_only") return <IconArrowDown className={cls} />;
  if (mode === "upload_only") return <IconArrowUp className={cls} />;
  return <IconArrowRightLeft className={cls} />;
}
