import { createPortal } from "react-dom";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
export default function SidebarContent({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  useEffect(() => { setTarget(document.getElementById("sidebar-conversations")); }, []);
  return target ? createPortal(children, target) : null;
}
