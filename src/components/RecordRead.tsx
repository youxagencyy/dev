"use client";

import { useEffect } from "react";
import { recordReadAction } from "@/app/kabinet/actions";

export function RecordRead({ articleId }: { articleId: string }) {
  useEffect(() => {
    void recordReadAction(articleId);
  }, [articleId]);
  return null;
}
