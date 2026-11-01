function Bone({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-[28px] bg-black/[0.05] dark:bg-white/[0.06] ${className}`} />;
}

export default function Loading() {
  return (
    <div aria-busy="true">
      <span className="sr-only">Відкриваємо редакцію</span>
      <Bone className="h-8 w-48" />
      <Bone className="mt-4 h-28 w-full" />
      <Bone className="mt-3 h-28 w-full" />
    </div>
  );
}
