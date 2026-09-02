import { useEffect, useRef } from "react";

type Props = {
  open: boolean;
  title: string;
  description: string;
  label: string;
  value: string;
  saving?: boolean;
  error?: string | null;
  onChange: (value: string) => void;
  onCancel: () => void;
  onSave: () => void;
};

export function NameEditDialog({
  open, title, description, label, value, saving = false, error,
  onChange, onCancel, onSave,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    inputRef.current?.select();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) onCancel();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel, saving]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[95] grid place-items-center bg-[#102033]/30 px-4 backdrop-blur-sm" onMouseDown={() => !saving && onCancel()}>
      <div role="dialog" aria-modal="true" aria-labelledby="name-edit-title" className="w-full max-w-md rounded-2xl border border-[#d7e4f5] bg-white p-6 shadow-[0_28px_90px_rgba(16,32,51,0.22)]" onMouseDown={(event) => event.stopPropagation()}>
        <h3 id="name-edit-title" className="text-lg font-semibold text-[#102033]">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-[#58708d]">{description}</p>
        <label className="mt-5 block text-xs font-semibold text-[#294662]">
          {label}
          <input ref={inputRef} aria-label={label} value={value} maxLength={120} disabled={saving} onChange={(event) => onChange(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") onSave(); }} className="mt-2 h-10 w-full rounded-xl border border-[#b9cfee] bg-white px-3 text-sm text-[#102033] outline-none focus:border-[#3370ff] focus:ring-2 focus:ring-[#3370ff]/15 disabled:opacity-60" />
        </label>
        {error ? <p className="mt-3 rounded-lg border border-[#fecdd3] bg-[#fff1f2] px-3 py-2 text-xs text-[#be123c]">{error}</p> : null}
        <div className="mt-6 flex justify-end gap-3">
          <button type="button" disabled={saving} onClick={onCancel} className="rounded-lg border border-[#c9d8eb] px-4 py-2 text-sm font-medium text-[#52677f] disabled:opacity-50">取消</button>
          <button type="button" disabled={saving || !value.trim()} onClick={onSave} className="rounded-lg bg-[#3370ff] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? "保存中…" : "保存"}</button>
        </div>
      </div>
    </div>
  );
}
