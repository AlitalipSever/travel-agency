/** The agency face of the site: name, navigation, plain-language labels and image lookup. */

export const AGENCY = {
  name: "Andes & Coast",
  tagline: "Small group trips in South America",
  demoNote: "This is a demo travel agency built for a backend case study. Bookings are not real.",
};

export const AGENCY_NAV = [
  { href: "/", label: "Home" },
  { href: "/destinations", label: "Destinations" },
  { href: "/tours", label: "Tours" },
  { href: "/about", label: "About" },
] as const;

/** Danger score 0 to 3 in customer words. */
export const LEVELS = [
  { score: 0, label: "Relaxed", hint: "Easy days, no physical demands" },
  { score: 1, label: "Easy", hint: "Some walking, nothing difficult" },
  { score: 2, label: "Active", hint: "Long days, some height or rough roads" },
  { score: 3, label: "Tough", hint: "Demanding terrain, for fit travellers" },
] as const;

export function levelLabel(score: number): string {
  return LEVELS[Math.min(Math.max(score, 0), 3)].label;
}

export function money(amount: string | number, currency: string): string {
  return new Intl.NumberFormat("en", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(amount));
}

export function longDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

/** "Buenos Aires" -> "buenos-aires"; accents removed so file names stay plain. */
export function slugify(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

const TOUR_IMAGES: Record<string, string> = {
  "andes-adventure": "tour-andes-adventure",
  "lima-weekend": "tour-lima-weekend",
  "rio-de-la-plata": "tour-rio-de-la-plata",
  "volcano-trek": "tour-volcano-trek",
};

/** Images live in public/images; every file listed here exists (generated once, AI-made). */
const AVAILABLE = new Set([
  "asuncion", "bogota", "brasilia", "buenos-aires", "caracas", "georgetown", "la-paz", "lima",
  "montevideo", "paramaribo", "quito", "santiago", "sucre",
  "tour-andes-adventure", "tour-lima-weekend", "tour-rio-de-la-plata", "tour-volcano-trek", "hero-andes-coast",
]);

export function cityImage(name: string): string | null {
  const slug = slugify(name);
  return AVAILABLE.has(slug) ? `/images/${slug}.jpg` : null;
}

export function tourImage(name: string, firstCity?: string): string | null {
  const slug = TOUR_IMAGES[slugify(name)];
  if (slug && AVAILABLE.has(slug)) return `/images/${slug}.jpg`;
  return firstCity ? cityImage(firstCity) : null;
}

export const HERO_IMAGE = "/images/hero-andes-coast.jpg";

/** Temperature in words for the home page strip. */
export function tempWord(temp: number): string {
  if (temp < 10) return "cold";
  if (temp < 20) return "cool";
  if (temp < 25) return "mild";
  if (temp < 30) return "warm";
  return "hot";
}
