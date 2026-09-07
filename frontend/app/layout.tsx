import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/AuthProvider";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Neva",
  description:
    "Türkçe bilişsel davranışçı terapi tabanlı destek asistanı. Terapist ya da acil servis yerine geçmez.",
};

// Inline script — applies theme class BEFORE first paint to avoid FOUC (flash).
const themeInitScript = `
(function() {
  try {
    var stored = localStorage.getItem('cbt_theme');
    var systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = stored === 'dark' || stored === 'light' ? stored : (systemDark ? 'dark' : 'light');
    if (theme === 'dark') document.documentElement.classList.add('dark');
  } catch(_) {}
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-full bg-cbt-bg text-cbt-text dark:bg-cbt-dark-bg dark:text-cbt-dark-text font-sans transition-colors">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
