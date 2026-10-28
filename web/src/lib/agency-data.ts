/** Server-side reads for the agency pages (the demo partner's token, see lib/api). */
import "server-only";
import { apiFetch, ApiError } from "@/lib/api";
import type { BookableDeparture, BookableResponse, BracketsResponse, Location, Page } from "@/lib/demo-types";

export type Itinerary = { position: number; id: string; name: string; type: string; danger: number; location: { id: string; name: string } };
export type TourPackage = {
  id: string;
  name: string;
  price: string;
  currency: string;
  description: string;
  duration_days: number;
  danger: number;
  danger_label: string;
  destinations: Itinerary[];
  departures_summary: { next: { starts_on: string; remaining_seats: number } | null; planned_count: number };
};
export type Departure = BookableDeparture & { status: "planned" | "cancelled" };

export async function getLocations(): Promise<Location[]> {
  return (await apiFetch<Page<Location>>("/locations?page_size=100")).results;
}

export async function getBrackets(): Promise<BracketsResponse> {
  return apiFetch<BracketsResponse>("/locations/brackets");
}

export async function getPackages(): Promise<TourPackage[]> {
  return (await apiFetch<Page<TourPackage>>("/packages?page_size=50")).results;
}

export async function getPackage(id: string): Promise<TourPackage | null> {
  try {
    return await apiFetch<TourPackage>(`/packages/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export async function getDepartures(packageId: string): Promise<Departure[]> {
  const rows = await apiFetch<Departure[]>(`/packages/${packageId}/departures`);
  return rows.filter((d) => d.status === "planned");
}

export async function searchBookable(q: { from: string; to: string; danger: number }): Promise<BookableResponse> {
  const params = new URLSearchParams({ from: q.from, to: q.to, danger: String(q.danger), page_size: "50" });
  return apiFetch<BookableResponse>(`/packages/bookable?${params}`);
}

/** Cities that appear in a package's itinerary, in order, without repeats. */
export function citiesOf(pkg: TourPackage): string[] {
  const seen = new Set<string>();
  return pkg.destinations.map((d) => d.location.name).filter((n) => (seen.has(n) ? false : (seen.add(n), true)));
}

export function isoToday(offsetDays = 0): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}
