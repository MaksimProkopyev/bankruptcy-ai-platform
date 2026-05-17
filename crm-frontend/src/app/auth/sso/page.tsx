"use client";

/**
 * SSO landing page — receives JWT from staff-frontend via URL fragment.
 * Fragment (#...) is never sent to the server, so the token stays client-only.
 * Flow: staff-frontend/login → /auth/sso#<token> → /dashboard
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SSOPage() {
  const router = useRouter();

  useEffect(() => {
    const raw = window.location.hash.slice(1); // strip leading #
    if (!raw) {
      router.replace("/login");
      return;
    }

    try {
      const token = decodeURIComponent(raw);
      const payload = JSON.parse(atob(token.split(".")[1]));

      // Store for crm-frontend's api.ts (localStorage) and middleware (cookie)
      localStorage.setItem("token", token);
      document.cookie = `staff_token=${encodeURIComponent(token)}; path=/; SameSite=Strict`;

      // Populate name/email cookies used by the Sidebar
      const fullName = [payload.first_name, payload.last_name].filter(Boolean).join(" ");
      if (fullName) {
        document.cookie = `staff_name=${encodeURIComponent(fullName)}; path=/; SameSite=Strict`;
      }
      if (payload.email) {
        document.cookie = `staff_email=${encodeURIComponent(payload.email)}; path=/; SameSite=Strict`;
      }
    } catch {
      router.replace("/login");
      return;
    }

    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <p className="text-sm text-gray-400">Переходим в CRM...</p>
    </div>
  );
}
