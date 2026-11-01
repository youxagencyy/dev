import Link from "next/link";
import { categoryLabel } from "@/lib/categories";
import { formatWhen } from "@/lib/format";
import type { NewsItem } from "@/lib/types";
import { CoverImage } from "./CoverImage";

export function NewsCard({
  item,
  variant = "tile",
}: {
  item: NewsItem;
  variant?: "tile" | "feature" | "row";
}) {
  const when = formatWhen(item.publishedAt);
  const TitleTag = variant === "feature" ? "h2" : "h3";

  return (
    <article className={`story story-${variant}`} data-cat={item.category}>
      <Link href={`/n/${item.id}`} className="story-link">
        {item.image ? <CoverImage src={item.image} /> : null}
        <span className="story-body">
          <span className="kicker">{categoryLabel(item.category)}</span>
          <TitleTag className="story-title">{item.title}</TitleTag>
          {item.summary ? <p className="excerpt">{item.summary}</p> : null}
          <p className="meta">
            {item.source ? <span className="source">{item.source}</span> : null}
            {item.source && when ? <span aria-hidden="true"> · </span> : null}
            {when ? <time dateTime={item.publishedAt}>{when}</time> : null}
          </p>
        </span>
      </Link>
    </article>
  );
}
