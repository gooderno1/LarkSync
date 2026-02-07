/* ------------------------------------------------------------------ */
/*  工具函数 - cn 合并类名                                              */
/* ------------------------------------------------------------------ */

/** 简易 cn() 合并 class，替代 clsx + tailwind-merge */
export function cn(...inputs: (string | undefined | null | false)[]): string {
  return inputs.filter(Boolean).join(" ");
}
