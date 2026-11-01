import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const geist = Geist({
  subsets: ["cyrillic", "latin"],
  variable: "--font-geist",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "ВАРТА — новини України та світу",
    template: "%s — ВАРТА",
  },
  description:
    "Новини українською: Україна, війна, політика, світ. Заголовки та короткі виклади з відкритих стрічок.",
  applicationName: "ВАРТА",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="uk" className={geist.variable}>
      <body className="bg-[#f6f6f7] font-sans text-[#0A0A0C] antialiased dark:bg-[#0A0A0C] dark:text-[#f4f4f5]">
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
