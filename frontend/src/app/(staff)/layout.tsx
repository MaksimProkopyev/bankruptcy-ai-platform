import type { Metadata } from "next";
import LayoutWrapper from "@/components/layout-wrapper";

export const metadata: Metadata = {
  title: 'НССБ «Максимум» — Портал сотрудников',
};

export default function StaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <LayoutWrapper>{children}</LayoutWrapper>;
}
