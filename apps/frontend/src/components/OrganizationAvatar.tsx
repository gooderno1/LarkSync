import { useEffect, useState } from "react";

import { apiUrl } from "../lib/api";
import type { AccountSummary } from "../types";

export function organizationDisplayName(account?: AccountSummary | null): string {
  if (!account) return "飞书组织";
  return account.account_alias || account.tenant_name || (account.tenant_tag === 2 ? "个人空间" : `飞书组织 · ${account.id.slice(0, 6)}`);
}

export function OrganizationAvatar({
  account,
  className,
  fallbackClassName,
}: {
  account?: AccountSummary | null;
  className: string;
  fallbackClassName: string;
}) {
  const source = account?.tenant_avatar_cache_path
    ? apiUrl(`/accounts/${account.id}/tenant-avatar?v=${Math.round(account.tenant_metadata_updated_at || 0)}`)
    : account?.tenant_avatar_url || "";
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [source]);

  if (!source || failed) {
    return <span data-organization-avatar-fallback="true" className={fallbackClassName}>{organizationDisplayName(account).slice(0, 1)}</span>;
  }
  return <img data-organization-avatar="true" src={source} alt="" className={className} onError={() => setFailed(true)} />;
}
