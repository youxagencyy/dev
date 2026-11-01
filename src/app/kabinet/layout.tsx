import { redirect } from "next/navigation";
import { CabinetNav } from "@/components/CabinetNav";
import { auth } from "@/auth";

export default async function CabinetLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session?.user) redirect("/uviity");

  return (
    <main id="content" className="mx-auto w-full max-w-[860px] px-4 pb-24 pt-12 sm:px-6">
      <p className="text-[11px] font-medium tracking-[0.18em] text-zinc-400 uppercase">Кабінет</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">{session.user.name || "Читач"}</h1>
      <CabinetNav />
      <div className="mt-10">{children}</div>
    </main>
  );
}
