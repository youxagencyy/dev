export function safeNext(value: string | null | undefined): string {
  if (!value) return "/kabinet";
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\") || value.includes("://")) {
    return "/kabinet";
  }
  return value;
}
