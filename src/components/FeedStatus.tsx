import { formatClock } from "@/lib/format";
import type { NewsSnapshot } from "@/lib/types";

export function FeedStatus({ snapshot }: { snapshot: NewsSnapshot }) {
  if (snapshot.items.length === 0) return null;
  const clock = formatClock(snapshot.fetchedAt);

  return (
    <p className="status">
      {clock ? <>Оновлено о {clock}</> : "Стрічку зібрано"}
      {snapshot.failures.length > 0 ? " · деякі джерела зараз недоступні" : null}
    </p>
  );
}
