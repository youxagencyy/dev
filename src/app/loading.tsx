function Bone({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-[28px] bg-black/[0.05] dark:bg-white/[0.06] ${className}`} />;
}

export default function Loading() {
  return (
    <main id="content" className="mx-auto w-full max-w-[1240px] px-4 pb-20 pt-8 sm:px-6" aria-busy="true">
      <span className="sr-only">Збираємо стрічку</span>
      <Bone className="mb-8 h-10 w-48 rounded-full" />
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-12">
        <Bone className="min-h-[520px] lg:col-span-7 lg:row-span-2" />
        <Bone className="min-h-[240px] lg:col-span-5" />
        <div className="grid grid-cols-2 gap-3 lg:col-span-5">
          <Bone className="min-h-[200px]" />
          <Bone className="min-h-[200px]" />
        </div>
      </div>
      <div className="mt-16 grid grid-cols-1 gap-8 lg:grid-cols-3">
        <Bone className="h-72 rounded-[28px]" />
        <Bone className="h-72 rounded-[28px]" />
        <Bone className="h-72 rounded-[28px]" />
      </div>
    </main>
  );
}
