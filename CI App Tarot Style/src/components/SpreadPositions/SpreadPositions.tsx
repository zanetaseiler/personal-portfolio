import './SpreadPositions.css';
import type { PpfPosition, Card as CardData } from '../../types/card';

const POSITIONS: { key: PpfPosition; label: string }[] = [
  { key: 'past', label: 'Past' },
  { key: 'present', label: 'Present' },
  { key: 'future', label: 'Future' },
];

interface SpreadPositionsProps {
  filled: Partial<Record<PpfPosition, CardData>>;
  onReset: () => void;
  canReset: boolean;
}

export function SpreadPositions({ filled, onReset, canReset }: SpreadPositionsProps) {
  return (
    <div className="spread-positions">
      <ol className="spread-positions-list">
        {POSITIONS.map(({ key, label }) => {
          const card = filled[key];
          return (
            <li key={key} className={`spread-slot ${card ? 'spread-slot--filled' : ''}`}>
              <span className="spread-slot-label" id={`slot-${key}`}>
                {label}
              </span>
              <span className="spread-slot-value" aria-labelledby={`slot-${key}`}>
                {card ? card.name : 'Choose a card'}
              </span>
            </li>
          );
        })}
      </ol>
      {canReset && (
        <button type="button" className="spread-reset-btn" onClick={onReset}>
          Start picks over
        </button>
      )}
    </div>
  );
}
