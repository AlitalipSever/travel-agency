"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Map as LeafletMap, LayerGroup, Marker } from "leaflet";
import "leaflet/dist/leaflet.css";
import { demoFetch } from "@/lib/demo-client";
import type { BracketsResponse, CurrentWeather, Location } from "@/lib/demo-types";
import { spectrum, onSpectrum } from "@/lib/spectrum";

// Key-free light basemap: Esri's World Light Gray canvas, plus its label layer on top.
const TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}";
const LABELS = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}";
const ATTRIBUTION = "Tiles &copy; Esri, HERE, Garmin, OpenStreetMap contributors";
const SOURCE_WORDS: Record<CurrentWeather["source"], string> = {
  live: "live reading",
  cached: "reading from the last few minutes",
  stale: "older reading; the weather service did not answer",
  sample: "from our records for this city",
};

type City = Location & { temp: number | null; stale: boolean };

function distanceKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const r = Math.PI / 180;
  const h = Math.sin(((b.lat - a.lat) * r) / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lon - a.lon) * r) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

function esc(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c);
}

function popupHtml(lat: number, lon: number, w: CurrentWeather | null | "failed", nearest: { c: City; km: number } | null): string {
  const head = `<div class="text-xs text-muted-foreground">${lat.toFixed(2)}, ${lon.toFixed(2)}</div>`;
  const body =
    w === "failed"
      ? `<p class="mt-1 text-sm">No weather for this point right now.<br/>Please try again in a minute.</p>`
      : w === null
        ? `<p class="mt-1 text-sm text-muted-foreground">Reading the weather…</p>`
        : `<p class="mt-1 text-2xl font-semibold">${Math.round(w.temp)}° <span class="text-sm font-normal text-muted-foreground">${esc(w.condition)}</span></p>
           <p class="text-xs text-muted-foreground">${w.humidity != null ? `humidity ${w.humidity}%` : ""}${w.wind_speed != null ? ` · wind ${w.wind_speed} m/s` : ""}</p>
           <p class="text-xs text-muted-foreground">${SOURCE_WORDS[w.source]}, ${w.observed_at.slice(11, 16)} UTC</p>`;
  const foot = nearest
    ? `<p class="mt-2 border-t pt-2 text-xs">Nearest of our cities: <a href="/destinations/${nearest.c.id}" class="font-medium underline">${esc(nearest.c.name)}</a>, ${Math.round(nearest.km)} km</p>`
    : "";
  return `<div class="w-56">${head}${body}${foot}</div>`;
}

/** A real map (Leaflet, light CARTO tiles): our cities as temperature badges, any other point on click. */
export function WorldMap({ className = "h-[420px] sm:h-[560px]" }: { className?: string }) {
  const router = useRouter();
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const [cities, setCities] = useState<City[] | null>(null);

  useEffect(() => {
    Promise.all([demoFetch<BracketsResponse>("locations/brackets"), demoFetch<{ results: Location[] }>("locations?page_size=100")])
      .then(([b, l]) => {
        const temps = new Map(b.data.brackets.flatMap((x) => x.locations).map((x) => [x.id, x]));
        setCities(l.data.results.map((c) => ({ ...c, temp: temps.get(c.id)?.temp ?? null, stale: temps.get(c.id)?.stale ?? false })));
      })
      .catch(() => setCities([]));
  }, []);

  useEffect(() => {
    if (!box.current || !cities) return;
    let cancelled = false;
    let pins: LayerGroup | null = null;
    let pick: Marker | null = null;

    import("leaflet").then((L) => {
      if (cancelled || !box.current) return;
      const map = L.map(box.current, { center: [-18, -62], zoom: 3, minZoom: 2, maxZoom: 16, worldCopyJump: true, scrollWheelZoom: false });
      mapRef.current = map;
      L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 16 }).addTo(map);
      L.tileLayer(LABELS, { maxZoom: 16, pane: "overlayPane" }).addTo(map);

      pins = L.layerGroup().addTo(map);
      for (const c of cities) {
        const t = c.temp === null ? null : (c.temp - 5) / 30;
        const style = t === null ? "background:#9ca3af;color:#fff" : `background:${spectrum(t)};color:${onSpectrum(t)}`;
        const label = c.temp === null ? "–" : `${Math.round(c.temp)}°`;
        const icon = L.divIcon({
          className: "",
          html: `<div class="ta-pin" style="${style}" title="${esc(c.name)}">${label}</div>`,
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        });
        L.marker([Number(c.latitude), Number(c.longitude)], { icon, keyboard: true, title: c.name })
          .bindTooltip(`${esc(c.name)}${c.stale ? " (older reading)" : ""}`, { direction: "top", offset: [0, -18] })
          .on("click", () => router.push(`/destinations/${c.id}`))
          .addTo(pins!);
      }

      map.on("click", (e) => {
        const { lat, lng } = e.latlng;
        const nearest = cities
          .map((c) => ({ c, km: distanceKm({ lat, lon: lng }, { lat: Number(c.latitude), lon: Number(c.longitude) }) }))
          .sort((a, b) => a.km - b.km)[0] ?? null;
        if (pick) pick.remove();
        const cross = L.divIcon({ className: "", html: '<div class="ta-cross"></div>', iconSize: [18, 18], iconAnchor: [9, 9] });
        pick = L.marker([lat, lng], { icon: cross, interactive: false }).addTo(map);
        const popup = L.popup({ offset: [0, -8], closeButton: true, autoPan: true, maxWidth: 260 })
          .setLatLng([lat, lng])
          .setContent(popupHtml(lat, lng, null, nearest))
          .openOn(map);
        demoFetch<CurrentWeather>(`weather/current?lat=${lat.toFixed(4)}&lon=${lng.toFixed(4)}`)
          .then((r) => popup.setContent(popupHtml(lat, lng, r.data, nearest)))
          .catch(() => popup.setContent(popupHtml(lat, lng, "failed", nearest)));
      });
    });

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [cities, router]);

  return (
    <div className={`relative overflow-hidden rounded-2xl border ${className}`}>
      <div ref={box} className="h-full w-full bg-[#eaf2f6]" aria-label="Map of our cities" />
      {!cities ? <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">Loading the map…</div> : null}
    </div>
  );
}
