/* ------------------------------------------------------------------ */
/*  配置 Hook：OAuth + 同步策略                                         */
/* ------------------------------------------------------------------ */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../lib/api";
import { isTimeValue } from "../lib/formatters";

type ConfigData = {
  auth_authorize_url?: string;
  auth_token_url?: string;
  auth_client_id?: string;
  auth_redirect_uri?: string;
  sync_mode?: string;
  token_store?: string;
  upload_interval_value?: number;
  upload_interval_unit?: string;
  upload_daily_time?: string;
  download_interval_value?: number;
  download_interval_unit?: string;
  download_daily_time?: string;
};

export function useConfig() {
  const qc = useQueryClient();

  const configQuery = useQuery<ConfigData>({
    queryKey: ["config"],
    queryFn: () => apiFetch<ConfigData>("/config"),
    staleTime: 60_000,
    placeholderData: {},
  });

  const saveMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => {
      // client-side validation
      const uv = body.upload_interval_value as number | null;
      if (uv !== null && uv !== undefined && (Number.isNaN(uv) || uv <= 0)) {
        throw new Error("本地上行间隔必须是大于 0 的数值。");
      }
      const dv = body.download_interval_value as number | null;
      if (dv !== null && dv !== undefined && (Number.isNaN(dv) || dv <= 0)) {
        throw new Error("云端下行间隔必须是大于 0 的数值。");
      }
      if (
        body.upload_interval_unit === "days" &&
        !isTimeValue((body.upload_daily_time as string) || "")
      ) {
        throw new Error("本地上行设置为按天时必须填写有效时间（HH:MM）。");
      }
      if (
        body.download_interval_unit === "days" &&
        !isTimeValue((body.download_daily_time as string) || "")
      ) {
        throw new Error("云端下行设置为按天时必须填写有效时间（HH:MM）。");
      }
      return apiFetch("/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config"] });
    },
  });

  return {
    config: configQuery.data || {},
    configLoading: configQuery.isLoading,
    configError: configQuery.error?.message ?? null,
    saveConfig: saveMutation.mutateAsync,
    saving: saveMutation.isPending,
    saveError: saveMutation.error?.message ?? null,
  };
}
