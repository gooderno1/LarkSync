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

export function SettingsAppProfilesPanel({ profiles, activeProfileId, onEdit }: Props) {
  return (
    <section data-settings-app-profiles="true" className="rounded-xl border border-[#d7e4f5] bg-white p-4 shadow-[0_10px_28px_rgba(51,112,255,0.05)]">
      <div>
        <h2 className="text-base font-semibold text-[#102033]">应用配置</h2>
        <p className="mt-1 text-[11px] leading-4 text-[#7e91a8]">名称仅用于本机辨识，不会修改飞书后台应用名称。</p>
      </div>
      <div className="mt-3 grid gap-2">
        {profiles.map((profile) => (
          <article key={profile.id} className={`rounded-xl border px-3 py-3 ${profile.id === activeProfileId ? "border-[#b9cfee] bg-[#f7faff]" : "border-[#e0e9f4] bg-white"}`}>
            <div className="flex min-w-0 items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex min-w-0 items-center gap-2">
                  <h3 className="truncate text-sm font-semibold text-[#102033]">{profile.display_name || "未命名应用"}</h3>
                  {profile.id === activeProfileId ? <span className="shrink-0 rounded-full bg-[#eaf3ff] px-2 py-0.5 text-[10px] font-semibold text-[#3370ff]">当前绑定</span> : null}
                </div>
                <p className="mt-1 font-mono text-[11px] text-[#71869d]">cli_••••{profile.app_id.slice(-4).toUpperCase()}</p>
              </div>
              <button type="button" onClick={() => onEdit(profile)} className="shrink-0 rounded-lg border border-[#c9d8eb] px-2.5 py-1.5 text-[11px] font-semibold text-[#3370ff] hover:bg-[#eef5ff]">改名</button>
            </div>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-[#8a9bb0]">
              <span>{sourceLabel(profile.source)}</span>
              <span>创建于 {new Date(profile.created_at * 1000).toLocaleDateString()}</span>
              <span>已绑定 {profile.linked_account_count} 个账号</span>
              {profile.recoverable_account_count > 0 ? <span className="font-semibold text-[#b45309]">可恢复 {profile.recoverable_account_count} 个</span> : null}
            </div>
          </article>
        ))}
        {!profiles.length ? <p className="rounded-xl border border-dashed border-[#c9d8eb] px-3 py-4 text-center text-xs text-[#71869d]">登录账号后将在这里显示应用配置。</p> : null}
      </div>
    </section>
  );
}
