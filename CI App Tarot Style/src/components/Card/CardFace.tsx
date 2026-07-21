import { CardArt } from '../CardArt/CardArt';
import { SUIT_META } from '../../data/cards';
import type { Card as CardData } from '../../types/card';

interface CardFaceProps {
  card: CardData;
}

export function CardFace({ card }: CardFaceProps) {
  const meta = SUIT_META[card.suit];

  return (
    <div className={`card-front card-front--${card.suit}`}>
      <CardArt seedInput={card.id} hue={meta.hue} className="card-art" />
      <div className="card-front-content">
        <span className="card-suit-label">
          {meta.label} · {card.number}
        </span>
        <h3 className="card-name">{card.name}</h3>
      </div>
    </div>
  );
}
