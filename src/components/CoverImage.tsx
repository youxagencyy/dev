"use client";

import { useState } from "react";

export function CoverImage({ src }: { src: string }) {
  const [visible, setVisible] = useState(true);
  if (!visible) return null;

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      className="cover"
      src={src}
      alt=""
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setVisible(false)}
    />
  );
}
