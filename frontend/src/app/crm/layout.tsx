"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";

export default function CrmLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Login page has no sidebar
  if (pathname === "/crm/login") {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 bg-gray-50 p-8">{children}</main>
    </div>
  );
}
