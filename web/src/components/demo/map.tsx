"use client";

import { useMemo, useRef } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import land from "world-atlas/land-110m.json";
import { cn } from "@/lib/utils";

export type MapPoint = { id: string; name: string; lat: number; lon: number; colour: string | null; stale?: boolean };
export type Coordinate = { lat: number; lon: number };

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
  pick,
  onPick,
  className,
}: {
  points: MapPoint[];
  selected: string | null;
  onSelect: (id: string) => void;
  /** A free coordinate chosen by clicking the map (not a location); drawn as a cross. */
  pick?: Coordinate | null;
  onPick?: (c: Coordinate) => void;
  className?: string;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { landPath, project, invert } = useMemo(() => {
    const projection = geoMercator().fitExtent(
      [
        [8, 8],
        [W - 8, H - 8],
      ],
      BBOX,
    );
    const topo = land as unknown as Topology<{ land: GeometryCollection }>;
    const geo = feature(topo, topo.objects.land);
    return {
      landPath: geoPath(projection)(geo) ?? "",
      project: (lon: number, lat: number) => projection([lon, lat]),
      invert: (x: number, y: number) => projection.invert?.([x, y]) ?? null,
    };
  }, []);

  /** Client pixels to viewBox units, then back through the projection to a coordinate. */
  function handleClick(e: React.MouseEvent<SVGSVGElement>) {
    if (!onPick || !svgRef.current) return;
    const box = svgRef.current.getBoundingClientRect();
    const x = ((e.clientX - box.left) / box.width) * W;
    const y = ((e.clientY - box.top) / box.height) * H;
    const ll = invert(x, y);
    if (ll) onPick({ lat: Math.round(ll[1] * 1000) / 1000, lon: Math.round(ll[0] * 1000) / 1000 });
  }
  const pickXY = pick ? project(pick.lon, pick.lat) : null;

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className={cn("h-auto w-full", onPick && "cursor-crosshair", className)}
      role="img"
      aria-label="Locations on a map of South America"
      onClick={handleClick}
    >
      <rect width={W} height={H} className="fill-spectral-night" rx="8" />
      <path d={landPath} className="fill-[#172052] stroke-spectral-line/40" strokeWidth="0.6" />
      {points.map((p) => {
        const xy = project(p.lon, p.lat);
        if (!xy) return null;
        const [x, y] = xy;
        const active = p.id === selected;
        return (
          <g
            key={p.id}
            transform={`translate(${x},${y})`}
            className="cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(p.id);
            }}
          >
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
      {pickXY ? (
        <g transform={`translate(${pickXY[0]},${pickXY[1]})`} pointerEvents="none">
          <circle r={9} fill="none" stroke="var(--spectral-cyan)" strokeWidth="1.5" />
          <line x1={-14} x2={14} y1={0} y2={0} stroke="var(--spectral-cyan)" strokeWidth="1" />
          <line x1={0} x2={0} y1={-14} y2={14} stroke="var(--spectral-cyan)" strokeWidth="1" />
        </g>
      ) : null}
    </svg>
  );
}
