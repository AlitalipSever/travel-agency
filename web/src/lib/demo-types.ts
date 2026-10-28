/** Response shapes of the API as the demo reads them (04-api). */

export type Problem = { type: string; title: string; status: number; detail?: string; [k: string]: unknown };

export type BracketLocation = {
  id: string;
  name: string;
  country_code: string;
  temp: number;
  observed_at: string;
  stale: boolean;
};

export type Bracket = { label: string; from: number | null; to: number | null; count: number; locations: BracketLocation[] };

export type BracketsResponse = {
  mode: "fixed" | "quantile";
  edges: number[];
  requested_buckets: number | null;
  effective_buckets: number;
  refreshed_at: string | null;
  brackets: Bracket[];
  no_data: { id: string; name: string; country_code: string; reason?: string }[];
};

export type Location = { id: string; name: string; country_code: string; latitude: string; longitude: string; timezone: string; active: boolean };

export type DaySummary = {
  date: string;
  temp_avg: number | null;
  temp_min: number | null;
  temp_max: number | null;
  condition: string;
  observed_samples: number;
  forecast_samples: number;
  partial: boolean;
};

export type CurrentWeather = {
  lat: number;
  lon: number;
  timezone: string;
  temp: number;
  condition: string;
  condition_code: number;
  humidity: number | null;
  wind_speed: number | null;
  observed_at: string;
  source: "sample" | "cached" | "live" | "stale";
  age_s: number;
  location_id: string | null;
};

export type ForecastResponse = {
  lat: number;
  lon: number;
  timezone: string;
  as_of: string;
  source: "sample" | "cached" | "live" | "stale";
  today: DaySummary | null;
  days: DaySummary[];
  location_id: string | null;
};

export type BookableDeparture = { id: string; starts_on: string; ends_on: string; capacity: number; confirmed_seats: number; remaining_seats: number };

export type BookablePackage = {
  id: string;
  name: string;
  price: string;
  currency: string;
  description: string;
  duration_days: number;
  danger: number;
  danger_label: string;
  departures: BookableDeparture[];
};

export type BookableResponse = {
  query: { from: string; to: string; danger: number; danger_mode: string; today: string; timezone: string };
  count: number;
  next: string | null;
  previous: string | null;
  results: BookablePackage[];
};

export type Traveller = { id: string; name: string; email: string; risk_appetite: number | null; partner_id: string | null };

export type Booking = {
  id: string;
  departure: { id: string; starts_on: string; ends_on: string; package: { id: string; name: string } };
  traveller: { id: string; name: string };
  seats: number;
  price_at_booking: string;
  currency: string;
  danger_at_booking: number;
  status: "confirmed" | "cancelled";
  cancelled_by: string | null;
  created_at: string;
};

export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };
