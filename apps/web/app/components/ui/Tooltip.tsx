"use client";

import { type ReactNode, useState } from "react";

export function Tooltip({ children, content }: { children: ReactNode; content: string }) {
  const [show, setShow] = useState(false);

  return (
    <span
      className="relative inline-flex"
      role="note"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show ? (
        <span
          role="tooltip"
          className="glass-strong absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-xs text-foreground shadow-xl"
        >
          {content}
        </span>
      ) : null}
    </span>
  );
}
