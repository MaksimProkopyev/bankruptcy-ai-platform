import SiteNavbar from "@/components/layout/SiteNavbar";
import SiteFooter from "@/components/layout/SiteFooter";
import QualificationChatbot from "@/components/chat/QualificationChatbot";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteNavbar />
      <main className="min-h-[70vh]">{children}</main>
      <SiteFooter />
      <QualificationChatbot />
    </>
  );
}
