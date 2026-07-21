// Deterministic seeded "sacred geometry" mandala generator. Same input
// always produces the same art — no image assets, no network calls.
// The output is a plain data structure; CardArt.tsx maps it to SVG.

export interface PetalShape {
  type: 'petal';
  cx: number;
  cy: number;
  rx: number;
  ry: number;
  rotate: number;
  color: string;
  opacity: number;
  filled: boolean;
}

export interface RingShape {
  type: 'ring';
  r: number;
  color: string;
  opacity: number;
}

export interface CenterMotif {
  kind: 'circle' | 'diamond' | 'triangle' | 'ringOnly';
  size: number;
  color: string;
  opacity: number;
}

export interface MandalaSpec {
  viewBox: string;
  shapes: (PetalShape | RingShape)[];
  center: CenterMotif;
}

function hashString(str: string): number {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return (h ^ (h >>> 16)) >>> 0;
}

function mulberry32(seed: number) {
  let a = seed;
  return function random() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CX = 100;
const CY = 100;

export function generateMandala(seedInput: string, hue: number): MandalaSpec {
  const rand = mulberry32(hashString(seedInput));
  const shapes: (PetalShape | RingShape)[] = [];

  const ringCount = 2 + Math.floor(rand() * 3); // 2-4

  for (let r = 0; r < ringCount; r++) {
    const radius = 24 + r * (68 / Math.max(ringCount - 1, 1));
    const petalCount = 6 + Math.floor(rand() * 7); // 6-12
    const rx = 3 + rand() * 3.5;
    const ry = rx * (1.7 + rand() * 1.1);
    const hueOffset = (rand() - 0.5) * 26;
    const sat = 32 + rand() * 24;
    const light = 44 + rand() * 14;
    const color = `hsl(${Math.round(hue + hueOffset)} ${sat.toFixed(0)}% ${light.toFixed(0)}%)`;
    const filled = r % 2 === 0;

    shapes.push({ type: 'ring', r: radius, color: `hsl(${hue} 28% 48%)`, opacity: 0.12 });

    for (let i = 0; i < petalCount; i++) {
      const angle = (360 / petalCount) * i + (r % 2 === 0 ? 0 : 360 / petalCount / 2);
      shapes.push({
        type: 'petal',
        cx: CX,
        cy: CY - radius,
        rx,
        ry,
        rotate: angle,
        color,
        opacity: filled ? 0.16 + rand() * 0.16 : 0.45 + rand() * 0.15,
        filled,
      });
    }
  }

  const motifKinds: CenterMotif['kind'][] = ['circle', 'diamond', 'triangle', 'ringOnly'];
  const center: CenterMotif = {
    kind: motifKinds[Math.floor(rand() * motifKinds.length)],
    size: 9 + rand() * 6,
    color: `hsl(${hue} 40% 42%)`,
    opacity: 0.55 + rand() * 0.25,
  };

  return { viewBox: '0 0 200 200', shapes, center };
}

// Fixed seed + brand hue so every face-down card shows an identical back.
export const CARD_BACK_SEED = 'ci-oracle-back';
export const BRAND_BACK_HUE = 38; // warm gold, matches --color-gold
