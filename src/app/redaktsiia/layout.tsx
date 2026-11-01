import { DeskNav } from "@/components/DeskNav";
import { DeskRefusal } from "@/components/DeskRefusal";
import { requireAdmin } from "@/lib/gate";

export default async function DeskLayout({ children }: { children: React.ReactNode }) {
  const admin = await requireAdmin();
  if (!admin) return <DeskRefusal />;

  return (
    <main id="content" className="mx-auto w-full max-w-[860px] px-4 pb-24 pt-12 sm:px-6">
      <p className="text-[11px] font-medium tracking-[0.18em] text-zinc-400 uppercase">Редакція</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">{admin.name || "Редактор"}</h1>
      <DeskNav />
      <div className="mt-10">{children}</div>
    </main>
  );
}
