import { useState } from "react";

import type { AppProfile } from "../../types";

type Props = {
  profiles: AppProfile[];
  activeProfileId?: string | null;
  onEdit: (profile: AppProfile) => void;
};

function sourceLabel(source: string) {
  if (source === "official_registration") return "自动创建";
  if (source === "legacy") return "升级迁移";
  return "手动配置";
}

function appManagementUrl(profile: AppProfile) {
  const host = profile.brand === "lark" ? "https://open.larksuite.com" : "https://open.feishu.cn";
  return `${host}/app/${encodeURIComponent(profile.app_id)}`;
}

function profileSummary(profiles: AppProfile[]) {
  if (!profiles.length) return "尚无应用配置";
  const activeCount = profiles.filter((profile) => profile.linked_account_count > 0).length;
  const recoverableCount = profiles.reduce((sum, profile) => sum + profile.recoverable_account_count, 0);
  return `${profiles.length} 个应用 · ${activeCount} 个正在使用 · ${recoverableCount} 个账号可恢复`;
}

export function SettingsAppProfilesPanel({ profiles, activeProfileId, onEdit }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasProfiles = profiles.length > 0;
  const summary = profileSummary(profiles);

  return (
    <section
      data-settings-app-profiles="true"
      data-app-profiles-expanded={expanded ? "true" : "false"}
      className="overflow-hidden rounded-xl border border-[#d7e4f5] bg-white shadow-[0_10px_28px_rgba(51,112,255,0.05)]"
    >
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 p-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-[#102033]">应用配置</h2>
          <p className="mt-1 truncate text-xs font-medium text-[#52677f]" title={summary}>{summary}</p>
          <p className="mt-1 text-[11px] leading-4 text-[#7e91a8]">展开后可改名或前往飞书开发后台管理。</p>
        </div>
        <button
          type="button"
          aria-expanded={expanded}
          aria-label={!hasProfiles ? "暂无应用配置" : expanded ? "收起应用配置" : "展开应用配置"}
          disabled={!hasProfiles}
          onClick={() => setExpanded((value) => !value)}
          className="inline-flex h-8 shrink-0 items-center gap-2 rounded-lg border border-[#b9cfee] bg-[#f7faff] px-3 text-xs font-semibold text-[#3370ff] transition hover:bg-[#eef5ff] disabled:cursor-not-allowed disabled:border-[#dce6f2] disabled:bg-[#f8fafc] disabled:text-[#9aabbd]"
        >
          <span>{!hasProfiles ? "暂无应用" : expanded ? "收起应用" : "展开应用"}</span>
          <svg viewBox="0 0 20 20" aria-hidden="true" className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`}>
            <path d="m5 7.5 5 5 5-5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
          </svg>
        </button>
      </div>

      {expanded ? (
        <div className="border-t border-[#e4edf8] bg-[#fbfdff] px-3 py-2">
          {profiles.map((profile) => (
            <article key={profile.id} className="grid min-w-0 gap-2 border-t border-[#e4edf8] px-1 py-3 first:border-t-0 min-[1080px]:grid-cols-[minmax(0,1fr)_auto] min-[1080px]:items-center">
              <div className="min-w-0">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <h3 className="truncate text-sm font-semibold text-[#102033]">{profile.display_name || "未命名应用"}</h3>
                  {profile.id === activeProfileId ? <span className="shrink-0 rounded-full bg-[#eaf3ff] px-2 py-0.5 text-[10px] font-semibold text-[#3370ff]">当前绑定</span> : null}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-[#8a9bb0]">
                  <span className="font-mono">cli_••••{profile.app_id.slice(-4).toUpperCase()}</span>
                  <span>{sourceLabel(profile.source)}</span>
                  <span>创建于 {new Date(profile.created_at * 1000).toLocaleDateString()}</span>
                  <span>已绑定 {profile.linked_account_count} 个账号</span>
                  {profile.recoverable_account_count > 0 ? <span className="font-semibold text-[#b45309]">可恢复 {profile.recoverable_account_count} 个</span> : null}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1 justify-self-start min-[1080px]:justify-self-end">
                <a
                  href={appManagementUrl(profile)}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`应用管理：${profile.display_name || profile.app_id}`}
                  className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-[#3370ff] hover:bg-[#eef5ff]"
                >
                  应用管理 ↗
                </a>
                <button type="button" onClick={() => onEdit(profile)} className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-[#52677f] hover:bg-[#eef5ff] hover:text-[#3370ff]">改名</button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
