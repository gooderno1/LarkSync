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
    <circle cx="6" cy="4.5" r="1.7" />
    <circle cx="18" cy="8" r="1.7" />
    <circle cx="6" cy="19.5" r="1.7" />
    <path d="M6 6.2v11.6" />
    <path d="M16.3 8H14a8 8 0 0 0-8 8" />
  </svg>
);

export const IconHome = (p: P) => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...p}>
    <path d="m3.2 10.2 8.8-7 8.8 7v9.1a1.5 1.5 0 0 1-1.5 1.5h-5.1v-6.2H9.8v6.2H4.7a1.5 1.5 0 0 1-1.5-1.5v-9.1Z" />
  </svg>
);

export const IconSyncCircle = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <path d="M20 8.5A8.5 8.5 0 0 0 5.2 6" />
    <path d="M5 2.8V6h3.2" />
    <path d="M4 15.5A8.5 8.5 0 0 0 18.8 18" />
    <path d="M19 21.2V18h-3.2" />
  </svg>
);

export const IconActivityList = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <circle cx="5" cy="6" r="1" fill="currentColor" />
    <circle cx="5" cy="12" r="1" fill="currentColor" />
    <circle cx="5" cy="18" r="1" fill="currentColor" />
    <path d="M9 6h10" />
    <path d="M9 12h10" />
    <path d="M9 18h10" />
  </svg>
);

export const IconDownloadTray = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <path d="M12 3v11" />
    <path d="m8 10 4 4 4-4" />
    <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
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

export const IconSearch = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M16 16l4 4" />
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

export const IconMoreHorizontal = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" />
    <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
    <circle cx="19" cy="12" r="1" fill="currentColor" stroke="none" />
  </svg>
);

export const IconPauseCircle = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M9.5 9v6" />
    <path d="M14.5 9v6" />
  </svg>
);

export const IconShieldCheck = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...p}>
    <path
      d="M12 3.2 19.2 6.1v5.35c0 4.35-2.85 8.05-7.2 9.35-4.35-1.3-7.2-5-7.2-9.35V6.1L12 3.2Z"
      fill="currentColor"
    />
    <path
      d="m8.6 12.15 2.15 2.15 4.75-5.05"
      stroke="#fff"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2.05}
    />
  </svg>
);

export const IconPulseCircle = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M5.8 12h2.4l1.3-3.4 3.1 7.1 1.8-4.3h3.8" />
  </svg>
);

export const IconClock = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5v5l3.2 2" />
  </svg>
);

export const IconAlertCircle = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.8v5.2" />
    <path d="M12 16.5h.01" />
  </svg>
);

export const IconAlertTriangle = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <path d="M10.3 4.5 2.9 17.2A2 2 0 0 0 4.6 20h14.8a2 2 0 0 0 1.7-2.8L13.7 4.5a2 2 0 0 0-3.4 0Z" fill="currentColor" />
    <path d="M12 9v4.2" stroke="#fff" strokeWidth="1.8" />
    <path d="M12 16.8h.01" stroke="#fff" strokeWidth="2.2" />
  </svg>
);

export const IconCircleCheck = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="m8.2 12.1 2.4 2.4 5.3-5.4" />
  </svg>
);

export const IconFileText = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <path d="M6 3.5h8l4 4V20a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 5 20V5a1.5 1.5 0 0 1 1-1.5Z" />
    <path d="M14 3.8V8h4" />
    <path d="M8.5 12h7" />
    <path d="M8.5 15.5h7" />
  </svg>
);

export const IconFileSearch = (p: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    <path d="M6 3.5h8l4 4v5.2" />
    <path d="M14 3.8V8h4" />
    <path d="M11.5 20.5h-5A1.5 1.5 0 0 1 5 19V5a1.5 1.5 0 0 1 1-1.5" />
    <circle cx="16.5" cy="16.5" r="3" />
    <path d="m18.7 18.7 2 2" />
  </svg>
);

export const IconGlobe = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M3.5 12h17" />
    <path d="M12 3.5a13 13 0 0 1 0 17" />
    <path d="M12 3.5a13 13 0 0 0 0 17" />
  </svg>
);

export const IconMaintenance = (p: P) => (
  <svg {...base} {...p}>
    <path d="M14.7 6.3a4 4 0 0 0-5 5L4 17l3 3 5.7-5.7a4 4 0 0 0 5-5l-2.8 2.8-3-3 2.8-2.8z" />
  </svg>
);

export const IconDatabase = (p: P) => (
  <svg {...base} {...p}>
    <ellipse cx="12" cy="5" rx="7" ry="3" />
    <path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5" />
    <path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
  </svg>
);

export const IconBrowser = (p: P) => (
  <svg {...base} {...p}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M3 8h18" />
    <path d="M7 6h.01M10 6h.01" />
    <path d="M8 14h8" />
  </svg>
);

export const IconLogout = (p: P) => (
  <svg {...base} {...p}>
    <path d="M10 17l5-5-5-5" />
    <path d="M15 12H3" />
    <path d="M21 3v18" />
  </svg>
);

/** 根据同步模式渲染图标 */
export function ModeIcon({ mode, className }: { mode: string; className?: string }) {
  const cls = className || "h-4 w-4";
  if (mode === "download_only") return <IconArrowDown className={cls} />;
  if (mode === "upload_only") return <IconArrowUp className={cls} />;
  return <IconArrowRightLeft className={cls} />;
}
