import { useMemo } from 'react';
import { generateMandala } from '../../lib/cardArt';

interface CardArtProps {
  seedInput: string;
  hue: number;
  className?: string;
}

export function CardArt({ seedInput, hue, className }: CardArtProps) {
  const spec = useMemo(() => generateMandala(seedInput, hue), [seedInput, hue]);

  return (
    <svg viewBox={spec.viewBox} className={className} aria-hidden="true" focusable="false">
      {spec.shapes.map((shape, i) =>
        shape.type === 'ring' ? (
          <circle
            key={i}
            cx={100}
            cy={100}
            r={shape.r}
            fill="none"
            stroke={shape.color}
            strokeOpacity={shape.opacity}
            strokeWidth={0.75}
          />
        ) : (
          <ellipse
            key={i}
            cx={shape.cx}
            cy={shape.cy}
            rx={shape.rx}
            ry={shape.ry}
            transform={`rotate(${shape.rotate} 100 100)`}
            fill={shape.filled ? shape.color : 'none'}
            fillOpacity={shape.filled ? shape.opacity : undefined}
            stroke={shape.filled ? 'none' : shape.color}
            strokeOpacity={shape.filled ? undefined : shape.opacity}
            strokeWidth={shape.filled ? 0 : 0.6}
          />
        ),
      )}

      {spec.center.kind === 'circle' && (
        <circle cx={100} cy={100} r={spec.center.size} fill={spec.center.color} fillOpacity={spec.center.opacity} />
      )}
      {spec.center.kind === 'ringOnly' && (
        <circle
          cx={100}
          cy={100}
          r={spec.center.size}
          fill="none"
          stroke={spec.center.color}
          strokeOpacity={spec.center.opacity}
          strokeWidth={1.2}
        />
      )}
      {spec.center.kind === 'diamond' && (
        <rect
          x={100 - spec.center.size}
          y={100 - spec.center.size}
          width={spec.center.size * 2}
          height={spec.center.size * 2}
          transform={`rotate(45 100 100)`}
          fill={spec.center.color}
          fillOpacity={spec.center.opacity}
        />
      )}
      {spec.center.kind === 'triangle' && (
        <polygon
          points={`100,${100 - spec.center.size} ${100 + spec.center.size * 0.87},${100 + spec.center.size * 0.5} ${100 - spec.center.size * 0.87},${100 + spec.center.size * 0.5}`}
          fill={spec.center.color}
          fillOpacity={spec.center.opacity}
        />
      )}
    </svg>
  );
}
