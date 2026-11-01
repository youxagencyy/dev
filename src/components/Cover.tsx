"use client";

import { useState } from "react";

export function Cover({ src, className }: { src?: string; className?: string }) {
  const [visible, setVisible] = useState(Boolean(src));
  if (!src || !visible) return null;

  return (
    // External RSS images come from many hosts. Native img avoids a remote-pattern allowlist.
    <img
      src={src}
      alt=""
      className={className}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setVisible(false)}
    />
  );
}
