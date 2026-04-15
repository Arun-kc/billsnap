"use client";

import { useState } from "react";
import Image from "next/image";
import BottomSheet from "@/components/ui/BottomSheet";

interface ImagePeekButtonProps {
  thumbnailUrl?: string;
  imageUrl?: string;
  alt?: string;
}

export default function ImagePeekButton({
  thumbnailUrl,
  imageUrl,
  alt = "Bill photo",
}: ImagePeekButtonProps) {
  const [open, setOpen] = useState(false);

  if (!thumbnailUrl && !imageUrl) return null;

  const fullImage = imageUrl ?? thumbnailUrl!;
  const peekImage = thumbnailUrl ?? imageUrl!;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="View bill photo"
        className="fixed right-4 bottom-28 z-30 w-14 h-14 rounded-2xl overflow-hidden shadow-lg border-2 border-white bg-[var(--color-surface-2)] active:scale-95 transition-transform"
        style={{ boxShadow: "0 6px 20px rgba(0,0,0,0.18)" }}
      >
        <Image
          src={peekImage}
          alt={alt}
          fill
          sizes="56px"
          className="object-cover"
        />
        <span
          aria-hidden="true"
          className="absolute bottom-0.5 right-0.5 text-[10px] leading-none px-1 py-0.5 rounded bg-black/60 text-white font-medium"
        >
          ⤢
        </span>
      </button>

      <BottomSheet open={open} onClose={() => setOpen(false)} title="Bill photo">
        <div
          className="w-full max-h-[70dvh] overflow-auto bg-[var(--color-surface-2)]"
          style={{ touchAction: "pinch-zoom" }}
        >
          <Image
            src={fullImage}
            alt={alt}
            width={1200}
            height={1600}
            className="w-full h-auto object-contain"
            sizes="100vw"
            unoptimized
          />
        </div>
      </BottomSheet>
    </>
  );
}
