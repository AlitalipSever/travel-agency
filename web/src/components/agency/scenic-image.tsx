import Image from "next/image";
import { cn } from "@/lib/utils";

/** A photo with a quiet gradient fallback when no file exists for the place. */
export function ScenicImage({ src, alt, className, priority = false, sizes = "(min-width: 1024px) 33vw, 100vw" }: {
  src: string | null;
  alt: string;
  className?: string;
  priority?: boolean;
  sizes?: string;
}) {
  return (
    <div className={cn("relative overflow-hidden bg-gradient-to-br from-spectral-deep via-spectral-sky to-spectral-cyan", className)}>
      {src ? <Image src={src} alt={alt} fill sizes={sizes} priority={priority} className="object-cover" /> : null}
    </div>
  );
}
