// Pure arc-math for the desktop deck fan. Cards are positioned relative to
// the center of their suit's arc using a normalized parameter t in [-1, 1],
// producing a shallow "smile" — horizontal spread widest at the center,
// gently drooping at the edges, like a hand-held fan of cards.
//
// x is expressed in `cqw` (container query width units) so the whole arc
// scales with its container's width with no JS resize listeners; y/rotate
// are scale-independent so fixed px/deg values are fine.

export interface FanTransform {
  xCqw: number;
  yPx: number;
  rotateDeg: number;
}

export interface FanConfig {
  maxAngleDeg: number;
  halfSpreadCqw: number;
  amplitudePx: number;
  rotateFactor: number;
}

export const DEFAULT_FAN_CONFIG: FanConfig = {
  maxAngleDeg: 30,
  halfSpreadCqw: 44,
  amplitudePx: 30,
  rotateFactor: 0.8,
};

export function computeFanTransform(index: number, total: number, config: FanConfig = DEFAULT_FAN_CONFIG): FanTransform {
  if (total <= 1) return { xCqw: 0, yPx: 0, rotateDeg: 0 };

  const t = (index - (total - 1) / 2) / ((total - 1) / 2); // -1..1

  return {
    xCqw: t * config.halfSpreadCqw,
    yPx: config.amplitudePx * t * t,
    rotateDeg: t * config.maxAngleDeg * config.rotateFactor,
  };
}
