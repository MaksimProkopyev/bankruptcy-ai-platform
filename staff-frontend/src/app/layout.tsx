import type { Metadata } from "next";
import "./globals.css";
import LayoutWrapper from "@/components/layout-wrapper";

export const metadata: Metadata = {
  title: 'НССБ «Максимум» — Портал сотрудников',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>
        <LayoutWrapper>{children}</LayoutWrapper>
      </body>
    </html>
  );
}
