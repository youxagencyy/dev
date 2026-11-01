import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { cookies } from "next/headers";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { auth } from "@/auth";
import { THEME_COOKIE, parseTheme, themeBootScript } from "@/lib/theme";
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

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const session = await auth();
  const jar = await cookies();
  const theme = session?.user
    ? parseTheme(jar.get(THEME_COOKIE)?.value ?? session.user.theme)
    : "SYSTEM";

  return (
    <html
      lang="uk"
      data-theme={theme}
      className={`${geist.variable}${theme === "DARK" ? " dark" : ""}`}
      suppressHydrationWarning
    >
      <body className="bg-[#f6f6f7] font-sans text-[#0A0A0C] antialiased dark:bg-[#0A0A0C] dark:text-[#f4f4f5]">
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
        <SiteHeader signedIn={Boolean(session?.user)} admin={session?.user?.role === "ADMIN"} />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
