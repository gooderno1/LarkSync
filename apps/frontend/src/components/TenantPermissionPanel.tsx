import { useCallback, useEffect, useRef, useState } from "react";
import * as QRCode from "qrcode";

import { apiFetch } from "../lib/api";
import { IconCircleCheck } from "./Icons";

type TenantMetadataResult = {
  status?: "ready" | "permission_required" | "unavailable" | "failed";
  message?: string;
  permission_url?: string;
  tenant_name?: string | null;
};

type TenantPermissionPanelProps = {
  accountId: string;
  organizationName: string;
  permissionUrl: string;
  onClose: () => void;
  onResolved: () => Promise<void> | void;
};

export function TenantPermissionPanel({
  accountId,
  organizationName,
  permissionUrl,
  onClose,
  onResolved,
}: TenantPermissionPanelProps) {
  const [qrData, setQrData] = useState("");
  const [checking, setChecking] = useState(false);
  const [state, setState] = useState<"waiting" | "success" | "expired" | "error">("waiting");
  const [message, setMessage] = useState("");
  const startedAt = useRef(Date.now());

  useEffect(() => {
    let active = true;
    QRCode.toDataURL(permissionUrl, { width: 520, margin: 2, errorCorrectionLevel: "M" })
      .then((value) => active && setQrData(value))
      .catch(() => {
        if (active) {
          setState("error");
          setMessage("二维码生成失败，可点击“在浏览器中打开”继续。 ");
        }
      });
    return () => { active = false; };
  }, [permissionUrl]);

  const checkPermission = useCallback(async () => {
    if (checking || state === "success") return;
    setChecking(true);
    try {
      const result = await apiFetch<TenantMetadataResult>(`/accounts/${accountId}/tenant-metadata/refresh`, { method: "POST" });
      if (result.status === "ready") {
        setState("success");
        setMessage("权限已开通，组织信息已更新");
        await onResolved();
      } else if (result.status === "permission_required") {
        setState("waiting");
        setMessage("尚未检测到权限，请在飞书中完成开通后再试。");
      } else {
        setState("error");
        setMessage(result.message || "暂时无法确认权限状态，请稍后重试。");
      }
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "权限检查失败，请稍后重试。");
    } finally {
      setChecking(false);
    }
  }, [accountId, checking, onResolved, state]);

  useEffect(() => {
    if (state !== "waiting") return;
    const timer = window.setInterval(() => {
      if (Date.now() - startedAt.current >= 3 * 60 * 1000) {
        setState("expired");
        setMessage("自动检查已暂停。完成开通后仍可点击立即检查。");
        return;
      }
      if (document.visibilityState === "visible") void checkPermission();
    }, 5_000);
    return () => window.clearInterval(timer);
  }, [checkPermission, state]);

  return (
    <div className="fixed inset-0 z-[80] grid place-items-center overflow-y-auto bg-[#102033]/30 p-5 backdrop-blur-[2px]" onMouseDown={onClose}>
      <section data-tenant-permission-panel="true" className="w-full max-w-[720px] overflow-hidden rounded-2xl border border-[#cfe0f5] bg-white shadow-2xl" onMouseDown={(event) => event.stopPropagation()}>
        <header className="flex items-start justify-between border-b border-[#e2ebf6] px-6 py-5">
          <div>
            <p className="text-xs font-semibold text-[#3370ff]">组织信息权限</p>
            <h2 className="mt-1 text-xl font-semibold text-[#102033]">扫码开通组织信息权限</h2>
            <p className="mt-1 text-xs text-[#71869d]">{organizationName} · 仅补全组织名称与 Logo，不影响现有账号和同步任务。</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-[#52657a] hover:bg-[#eef5ff]">关闭</button>
        </header>

        {state === "success" ? (
          <div className="px-6 py-10 text-center">
            <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-[#dcfce7] text-[#059669]"><IconCircleCheck className="h-8 w-8" /></span>
            <p className="mt-4 text-lg font-semibold text-[#102033]">权限已开通，组织信息已更新</p>
            <p className="mt-2 text-sm text-[#52657a]">侧边栏和账号管理会显示最新的官方组织信息。</p>
            <button type="button" onClick={onClose} className="mt-5 rounded-xl bg-[#3370ff] px-6 py-2.5 text-sm font-semibold text-white">完成</button>
          </div>
        ) : (
          <div className="grid gap-6 px-6 py-6 sm:grid-cols-[220px_minmax(0,1fr)]">
            <div className="grid aspect-square place-items-center rounded-2xl border border-[#d7e4f5] bg-[#f7faff] p-3">
              {qrData ? <img data-testid="tenant-permission-qr" src={qrData} alt="飞书组织信息权限开通二维码" className="h-full w-full" /> : <span className="text-xs text-[#71869d]">正在生成二维码…</span>}
            </div>
            <div className="flex flex-col justify-center">
              <span className="w-fit rounded-full bg-[#eaf3ff] px-2.5 py-1 text-[10px] font-semibold text-[#3370ff]">这不是账号重新登录</span>
              <ol className="mt-4 space-y-3 text-sm leading-6 text-[#52657a]">
                <li><strong className="text-[#102033]">1.</strong> 使用飞书扫码，打开当前应用的官方权限管理页。</li>
                <li><strong className="text-[#102033]">2.</strong> 开通“组织信息只读”权限；如有审批，需由管理员完成。</li>
                <li><strong className="text-[#102033]">3.</strong> 返回本页，LarkSync 每 5 秒自动检查一次。</li>
              </ol>
              {message ? <p className={`mt-4 rounded-lg px-3 py-2 text-xs leading-5 ${state === "error" ? "bg-[#fff1f2] text-[#be123c]" : "bg-[#fff8df] text-[#8a5a00]"}`}>{message}</p> : null}
              <div className="mt-5 flex flex-wrap gap-2">
                <button type="button" disabled={checking} onClick={() => void checkPermission()} className="rounded-lg bg-[#3370ff] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50">{checking ? "检查中…" : "我已开通，立即检查"}</button>
                <button type="button" onClick={() => window.open(permissionUrl, "_blank", "noopener,noreferrer")} className="rounded-lg border border-[#b9cce2] px-4 py-2 text-xs font-semibold text-[#52657a] hover:bg-[#eef5ff]">在浏览器中打开</button>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export type { TenantMetadataResult };
