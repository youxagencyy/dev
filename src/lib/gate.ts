import { redirect } from "next/navigation";
import { auth } from "@/auth";

export async function requireAdmin() {
  const session = await auth();
  if (!session?.user) redirect("/uviity?next=/redaktsiia");
  if (session.user.role !== "ADMIN") return null;
  return session.user;
}
