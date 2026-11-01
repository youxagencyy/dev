function Bone({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-full bg-black/[0.05] dark:bg-white/[0.06] ${className}`} />;
}

export default function Loading() {
  return (
    <main id="content" className="mx-auto w-full max-w-[860px] px-4 pb-24 pt-12 sm:px-6" aria-busy="true">
      <span className="sr-only">Відкриваємо пошук</span>
      <Bone className="h-4 w-16" />
      <Bone className="mt-4 h-12 w-72 rounded-[28px]" />
      <Bone className="mt-8 h-14 w-full" />
      <div className="mt-6 flex gap-2">
        <Bone className="h-8 w-16" />
        <Bone className="h-8 w-24" />
        <Bone className="h-8 w-20" />
        <Bone className="h-8 w-24" />
      </div>
      <Bone className="mt-10 h-24 w-full rounded-[28px]" />
      <Bone className="mt-3 h-24 w-full rounded-[28px]" />
    </main>
  );
}
