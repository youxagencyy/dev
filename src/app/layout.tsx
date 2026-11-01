import type { Metadata } from "next";
import { Literata, Manrope } from "next/font/google";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

const sans = Manrope({
  subsets: ["cyrillic", "latin"],
  variable: "--font-sans",
  display: "swap",
});

const serif = Literata({
  subsets: ["cyrillic", "latin"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "ВАРТА — новини України та світу",
    template: "%s — ВАРТА",
  },
  description:
    "Агрегатор новин українською: Україна, війна, політика, світ. Заголовки та короткі виклади з відкритих стрічок.",
  applicationName: "ВАРТА",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="uk" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
