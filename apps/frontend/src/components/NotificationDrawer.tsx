import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAccounts } from "../hooks/useAccounts";
import { apiFetchForAccount } from "../lib/api";
import type { AccountNotification } from "../types";

export function NotificationDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { activeAccountId } = useAccounts();
  const queryClient = useQueryClient();
  const query = useQuery<AccountNotification[]>({
    queryKey: ["notifications", activeAccountId],
    queryFn: ({ signal }) => apiFetchForAccount<AccountNotification[]>(`/notifications?account_id=${encodeURIComponent(activeAccountId || "")}`, activeAccountId || "", { signal }),
    enabled: open && Boolean(activeAccountId),
  });
  const readMutation = useMutation({
    mutationFn: (id: string) => apiFetchForAccount(`/notifications/${id}/read`, activeAccountId || "", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ read: true }),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications", activeAccountId] });
      queryClient.invalidateQueries({ queryKey: ["accounts-summary"] });
    },
  });
  const readAllMutation = useMutation({
    mutationFn: (accountId: string) => apiFetchForAccount<{ updated: number }>(`/notifications/read-all?account_id=${encodeURIComponent(accountId)}`, accountId, { method: "POST" }),
    onSuccess: async (_result, accountId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["notifications", accountId] }),
        queryClient.invalidateQueries({ queryKey: ["accounts-summary"] }),
      ]);
    },
  });

  const openAction = (item: AccountNotification) => {
    const prefix = "account:reauthorize:";
    if (!item.action_target?.startsWith(prefix)) return;
    const accountId = item.action_target.slice(prefix.length).trim();
    if (!accountId) return;
    window.localStorage.setItem("larksync.reauthorize-account-id", accountId);
    if (!item.read_at) readMutation.mutate(item.id);
    window.location.hash = "#settings";
    onClose();
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[80] flex justify-end bg-[#102033]/20 backdrop-blur-[2px]" onMouseDown={onClose}>
      <aside className="h-full w-full max-w-[420px] overflow-y-auto border-l border-[#cbd9ea] bg-[#f8fbff] p-5 shadow-2xl" onMouseDown={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div><h2 className="text-xl font-semibold text-[#102033]">通知</h2><p className="mt-1 text-xs text-[#71869d]">当前账户的消息与同步错误</p></div>
          <button type="button" onClick={onClose} className="rounded-lg border border-[#cbd9ea] px-3 py-1.5 text-sm text-[#52657a]">关闭</button>
        </div>
        <button type="button" disabled={!activeAccountId || readAllMutation.isPending} onClick={() => activeAccountId && readAllMutation.mutate(activeAccountId)} className="mt-5 text-sm font-semibold text-[#3370ff] disabled:opacity-50">{readAllMutation.isPending ? "正在标记…" : "全部标为已读"}</button>
        {readAllMutation.variables === activeAccountId && readAllMutation.isSuccess ? <p role="status" className="mt-2 text-xs text-[#22835f]">{readAllMutation.data.updated > 0 ? `已将 ${readAllMutation.data.updated} 条通知标为已读` : "当前没有未读通知"}</p> : null}
        {readAllMutation.variables === activeAccountId && readAllMutation.isError ? <p role="alert" className="mt-2 text-xs text-[#be123c]">标记已读失败：{readAllMutation.error.message}</p> : null}
        <div className="mt-4 grid gap-3">
          {query.isLoading ? <p className="py-10 text-center text-sm text-[#71869d]">正在读取通知…</p> : null}
          {query.data?.map((item) => (
            <article key={item.id} onClick={() => !item.read_at && readMutation.mutate(item.id)} className={`rounded-2xl border p-4 text-left shadow-sm ${item.read_at ? "border-[#dce6f2] bg-white/70" : "border-[#bcd2f0] bg-white"}`}>
              <div className="flex items-center justify-between gap-3"><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${item.category === "sync_error" ? "bg-[#fff1f2] text-[#be123c]" : "bg-[#eaf3ff] text-[#3370ff]"}`}>{item.category === "sync_error" ? "同步错误" : "消息"}</span><span className="text-[11px] text-[#8ca0b6]">{new Date(item.created_at * 1000).toLocaleString()}</span></div>
              <h3 className="mt-3 text-sm font-semibold text-[#102033]">{item.title}</h3>
              <p className="mt-1 text-xs leading-5 text-[#52657a]">{item.body}</p>
              <p className={`mt-2 text-[11px] ${item.read_at ? "text-[#8ca0b6]" : "font-semibold text-[#3370ff]"}`}>{item.read_at ? "已读" : "未读"}</p>
              {item.action_target?.startsWith("account:reauthorize:") ? <button type="button" onClick={(event) => { event.stopPropagation(); openAction(item); }} className="mt-3 rounded-lg bg-[#3370ff] px-3 py-2 text-xs font-semibold text-white hover:bg-[#2563eb]">立即重新授权</button> : null}
            </article>
          ))}
          {!query.isLoading && !query.data?.length ? <p className="rounded-2xl border border-dashed border-[#cbd9ea] bg-white p-8 text-center text-sm text-[#71869d]">当前没有通知</p> : null}
        </div>
      </aside>
    </div>
  );
}
