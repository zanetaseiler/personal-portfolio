import type { CSSProperties } from 'react';
import './DeckSpread.css';
import { Card } from '../Card/Card';
import { SUITS, SUIT_META } from '../../data/cards';
import { cardsForSuit } from '../../lib/deck';
import { computeFanTransform } from '../../lib/layout';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import type { Card as CardData } from '../../types/card';

interface DeckSpreadProps {
  cards: CardData[];
  disabledIds: Set<string>;
  revealedIds: Set<string>;
  onCardClick: (id: string) => void;
}

export function DeckSpread({ cards, disabledIds, revealedIds, onCardClick }: DeckSpreadProps) {
  const isDesktopFan = useMediaQuery('(min-width: 700px)');

  return (
    <div className="deck-spread">
      {SUITS.map((suit) => {
        const suitCards = cardsForSuit(cards, suit);
        return (
          <div className="suit-arc-row" key={suit}>
            <p className="suit-arc-label">{SUIT_META[suit].label}</p>
            <div className={`suit-arc ${isDesktopFan ? 'suit-arc--fan' : 'suit-arc--scroll'}`}>
              {suitCards.map((card, i) => {
                let style: CSSProperties = {};
                if (isDesktopFan) {
                  const { xCqw, yPx, rotateDeg } = computeFanTransform(i, suitCards.length);
                  style = {
                    position: 'absolute',
                    left: `calc(50% + ${xCqw}cqw)`,
                    top: `calc(50% + ${yPx}px)`,
                    transform: `translate(-50%, -50%) rotate(${rotateDeg}deg)`,
                    zIndex: revealedIds.has(card.id) ? 100 : i,
                  };
                }
                return (
                  <Card
                    key={card.id}
                    card={card}
                    isRevealed={revealedIds.has(card.id)}
                    disabled={disabledIds.has(card.id)}
                    onSelect={disabledIds.has(card.id) ? undefined : () => onCardClick(card.id)}
                    style={style}
                    ariaLabel={`Draw ${SUIT_META[suit].label} card ${i + 1} of ${suitCards.length}`}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
