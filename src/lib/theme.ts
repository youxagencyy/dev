export const THEME_COOKIE = "varta-theme";

export const THEMES = [
  { id: "SYSTEM", label: "Система" },
  { id: "LIGHT", label: "Світла" },
  { id: "DARK", label: "Темна" },
] as const;

export type ThemeChoice = (typeof THEMES)[number]["id"];

export function parseTheme(value: string | undefined | null): ThemeChoice {
  if (value === "LIGHT" || value === "DARK" || value === "SYSTEM") return value;
  return "SYSTEM";
}

export const themeCookie = {
  path: "/",
  sameSite: "lax" as const,
  maxAge: 60 * 60 * 24 * 400,
  httpOnly: true,
};

export const themeBootScript = `(function(){var root=document.documentElement;function apply(){var theme=root.dataset.theme||"SYSTEM";var dark=theme==="DARK"||(theme==="SYSTEM"&&window.matchMedia("(prefers-color-scheme: dark)").matches);root.classList.toggle("dark",dark);root.style.colorScheme=dark?"dark":"light";}apply();window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",apply);window.__vartaApplyTheme=function(theme){root.dataset.theme=theme;apply();};})();`;

declare global {
  interface Window {
    __vartaApplyTheme?: (theme: ThemeChoice) => void;
  }
}

export function applyTheme(theme: ThemeChoice) {
  if (typeof window === "undefined") return;
  if (window.__vartaApplyTheme) {
    window.__vartaApplyTheme(theme);
    return;
  }
  const root = document.documentElement;
  root.dataset.theme = theme;
  const dark =
    theme === "DARK" ||
    (theme === "SYSTEM" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  root.classList.toggle("dark", dark);
  root.style.colorScheme = dark ? "dark" : "light";
}
