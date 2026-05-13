import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Банкротство.AI — Списание долгов с помощью AI",
    template: "%s — Банкротство.AI",
  },
  description:
    "Банкротство физических лиц — законная процедура списания долгов. AI-скоринг за 2 минуты, от заявки до суда за 5 дней.",
  metadataBase: new URL("https://bankruptcy.ai"),
  openGraph: {
    type: "website",
    locale: "ru_RU",
    siteName: "Банкротство.AI",
  },
  robots: { index: true, follow: true },
  manifest: '/manifest.json',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="antialiased">
        {children}
        <script dangerouslySetInnerHTML={{ __html: `if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').then(function(r){console.log('SW:',r.scope)}).catch(function(e){console.log('SW err:',e)})})}` }} />
      </body>
    </html>
  );
}
