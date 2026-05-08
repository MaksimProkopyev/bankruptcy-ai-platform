import Sidebar from "@/components/layout/Sidebar";
export default function Layout({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-screen"><Sidebar /><main className="flex-1 bg-gray-50 p-8">{children}</main></div>;
}
