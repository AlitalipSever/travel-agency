"use client";

import { useMemo } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import land from "world-atlas/land-110m.json";
import { cn } from "@/lib/utils";

export type MapPoint = { id: string; name: string; lat: number; lon: number; colour: string | null; stale?: boolean };

const W = 520;
const H = 640;
const BBOX = {
  type: "Feature" as const,
  properties: {},
  geometry: { type: "Polygon" as const, coordinates: [[[-84, -57], [-84, 14], [-33, 14], [-33, -57], [-84, -57]]] },
};

/** South America from the public domain world atlas (Natural Earth, 110 m), Mercator, no tiles. */
export function SouthAmericaMap({
  points,
  selected,
  onSelect,
  className,
}: {
  points: MapPoint[];
  selected: string | null;
  onSelect: (id: string) => void;
  className?: string;
}) {
  const { landPath, project } = useMemo(() => {
    const projection = geoMercator().fitExtent(
      [
        [8, 8],
        [W - 8, H - 8],
      ],
      BBOX,
    );
    const topo = land as unknown as Topology<{ land: GeometryCollection }>;
    const geo = feature(topo, topo.objects.land);
    return { landPath: geoPath(projection)(geo) ?? "", project: (lon: number, lat: number) => projection([lon, lat]) };
  }, []);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={cn("h-auto w-full", className)} role="img" aria-label="Locations on a map of South America">
      <rect width={W} height={H} className="fill-spectral-night" rx="8" />
      <path d={landPath} className="fill-[#172052] stroke-spectral-line/40" strokeWidth="0.6" />
      {points.map((p) => {
        const xy = project(p.lon, p.lat);
        if (!xy) return null;
        const [x, y] = xy;
        const active = p.id === selected;
        return (
          <g key={p.id} transform={`translate(${x},${y})`} className="cursor-pointer" onClick={() => onSelect(p.id)}>
            <title>{p.name}</title>
            {active ? <circle r={13} fill="none" stroke="#fff" strokeWidth="1.5" /> : null}
            <circle
              r={7}
              fill={p.colour ?? "transparent"}
              stroke={p.colour ? "#fff" : "var(--spectral-line)"}
              strokeWidth={1.5}
              strokeDasharray={p.stale || !p.colour ? "2 2" : undefined}
            />
            <text x={11} y={4} fontSize="11" fontFamily="var(--font-mono)" fill="#eef2fb" style={{ paintOrder: "stroke" }} stroke="#0a1030" strokeWidth="3">
              {p.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
