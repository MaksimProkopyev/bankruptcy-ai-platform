import type { Metadata } from "next";
import "./globals.css";
import LayoutWrapper from "@/components/layout-wrapper";

export const metadata: Metadata = {
  title: 'НССБ «Максимум» — Портал сотрудников',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'НССБ Максимум',
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'apple-mobile-web-app-title': 'НССБ Максимум',
    'apple-touch-icon': '/icons/icon-192.png',
    'theme-color': '#1B3A5C',
    'msapplication-TileColor': '#1B3A5C',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
      </head>
      <body>
        <script dangerouslySetInnerHTML={{ __html: `if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').then(function(r){console.log('SW:',r.scope)}).catch(function(e){console.log('SW err:',e)})})}` }} />
        <LayoutWrapper>{children}</LayoutWrapper>
      </body>
    </html>
  );
}
