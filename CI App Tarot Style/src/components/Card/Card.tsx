import { motion } from 'framer-motion';
import type { CSSProperties } from 'react';
import './Card.css';
import { CardBack } from './CardBack';
import { CardFace } from './CardFace';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { theme } from '../../styles/theme';
import type { Card as CardData } from '../../types/card';

interface CardProps {
  card: CardData;
  isRevealed: boolean;
  onSelect?: () => void;
  disabled?: boolean;
  style?: CSSProperties;
  ariaLabel?: string;
}

export function Card({ card, isRevealed, onSelect, disabled, style, ariaLabel }: CardProps) {
  const reducedMotion = usePrefersReducedMotion();
  const flipTransition = reducedMotion ? { duration: 0 } : theme.spring.flip;
  const hoverTransition = reducedMotion ? { duration: 0 } : theme.spring.hover;

  return (
    <motion.button
      type="button"
      className="card"
      style={{ perspective: 1000, ...style }}
      onClick={onSelect}
      disabled={disabled || !onSelect}
      whileHover={!disabled && onSelect ? { y: -18, scale: 1.04, zIndex: 60 } : undefined}
      whileFocus={!disabled && onSelect ? { y: -18, scale: 1.04, zIndex: 60 } : undefined}
      transition={hoverTransition}
      aria-label={isRevealed ? `${card.name}, revealed` : (ariaLabel ?? 'Draw a card')}
      aria-pressed={isRevealed}
    >
      <motion.div
        className="card-flip-inner"
        animate={{ rotateY: isRevealed ? 180 : 0 }}
        transition={flipTransition}
      >
        <div className="card-face card-face--back">
          <CardBack />
        </div>
        <div className="card-face card-face--front">
          <CardFace card={card} />
        </div>
      </motion.div>
    </motion.button>
  );
}
