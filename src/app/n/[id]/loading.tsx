function Bone({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-[28px] bg-black/[0.05] dark:bg-white/[0.06] ${className}`} />;
}

export default function Loading() {
  return (
    <main id="content" className="mx-auto w-full max-w-[760px] px-4 pb-32 pt-12 sm:px-6" aria-busy="true">
      <span className="sr-only">Відкриваємо матеріал</span>
      <Bone className="h-7 w-24 rounded-full" />
      <Bone className="mt-5 h-24 w-full" />
      <Bone className="mt-8 aspect-[16/9] w-full" />
      <Bone className="mt-10 h-36 w-full" />
    </main>
  );
}
