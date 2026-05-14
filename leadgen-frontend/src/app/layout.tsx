"use client";

import "./globals.css";
import { usePathname } from "next/navigation";
import LeadgenSidebar from "@/components/layout/LeadgenSidebar";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  return (
    <html lang="ru">
      <body>
        {isLogin ? (
          children
        ) : (
          <div className="flex min-h-screen">
            <LeadgenSidebar />
            <main className="flex-1 bg-gray-50 p-8">{children}</main>
          </div>
        )}
      </body>
    </html>
  );
}
