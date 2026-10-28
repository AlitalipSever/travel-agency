/** The seven sections of the case study (05-work-packages W1), reached from the "Case study" menu. */
export const SECTIONS = [
  { href: "/case-study", label: "Overview", short: "What the system is and how it is built" },
  { href: "/demo", label: "Live demo", short: "Brackets, forecasts and the bookable search against the API" },
  { href: "/api", label: "API", short: "The OpenAPI contract, browsable" },
  { href: "/decisions", label: "Decisions", short: "Every architecture decision record" },
  { href: "/plan", label: "Plan", short: "Work packages, what is done, what comes next" },
  { href: "/operations", label: "Operations", short: "Live status of the weather pipeline" },
  { href: "/walkthrough", label: "Walkthrough", short: "The ten minute path through the system" },
] as const;

export type Section = (typeof SECTIONS)[number];
