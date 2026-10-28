/** The thermal spectrum as a scale: a fraction 0 (cool) to 1 (warm) becomes a colour. */
const STOPS: [number, string][] = [
  [0, "#0a1f9e"],
  [0.3, "#2f6bea"],
  [0.5, "#56c8ee"],
  [0.65, "#e9f3c6"],
  [0.8, "#f5b36b"],
  [0.92, "#ee5a24"],
  [1, "#b8250f"],
];

function hex(c: string): [number, number, number] {
  return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
}

export function spectrum(t: number): string {
  const x = Math.max(0, Math.min(1, t));
  for (let i = 1; i < STOPS.length; i++) {
    const [t0, c0] = STOPS[i - 1];
    const [t1, c1] = STOPS[i];
    if (x <= t1) {
      const k = (x - t0) / (t1 - t0);
      const a = hex(c0);
      const b = hex(c1);
      const m = a.map((v, j) => Math.round(v + (b[j] - v) * k));
      return `rgb(${m[0]} ${m[1]} ${m[2]})`;
    }
  }
  return STOPS[STOPS.length - 1][1];
}

/** Colour of bracket i out of n, spread over the scale. */
export function bracketColour(i: number, n: number): string {
  return spectrum(n <= 1 ? 0.5 : i / (n - 1));
}

/** Text colour that reads on a given scale position: white on the cool half, Night on the warm. */
export function onSpectrum(t: number): string {
  return t < 0.55 ? "#ffffff" : "#0a1030";
}
