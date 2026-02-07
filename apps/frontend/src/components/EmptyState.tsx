/* ------------------------------------------------------------------ */
/*  空状态引导组件                                                      */
/* ------------------------------------------------------------------ */

import type { ReactNode } from "react";

type EmptyStateProps = {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/50 text-zinc-600">
        {icon}
      </div>
      <h3 className="mt-4 text-base font-semibold text-zinc-300">{title}</h3>
      {description ? (
        <p className="mx-auto mt-2 max-w-sm text-sm text-zinc-500">{description}</p>
      ) : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  );
}
