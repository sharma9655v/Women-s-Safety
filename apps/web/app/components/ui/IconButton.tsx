import type { ButtonHTMLAttributes, ReactNode } from "react";

export function IconButton({
  children,
  label,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      className={`flex size-9 cursor-pointer items-center justify-center rounded-xl border border-border bg-surface text-text-secondary transition-all duration-200 hover:border-border-glow hover:bg-surface-hover hover:text-foreground active:scale-95 ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
