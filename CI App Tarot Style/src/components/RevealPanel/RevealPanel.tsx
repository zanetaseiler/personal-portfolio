import { motion } from 'framer-motion';
import './RevealPanel.css';
import { CardArt } from '../CardArt/CardArt';
import { SUIT_META } from '../../data/cards';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import type { Card as CardData } from '../../types/card';

export interface RevealEntry {
  positionLabel?: string;
  card: CardData;
}

interface RevealPanelProps {
  entries: RevealEntry[];
  note: string;
}

function RevealCard({ entry }: { entry: RevealEntry }) {
  const meta = SUIT_META[entry.card.suit];
  return (
    <article className={`reveal-card reveal-card--${entry.card.suit}`}>
      {entry.positionLabel && <p className="reveal-card-position">{entry.positionLabel}</p>}
      <div className="reveal-card-art-wrap">
        <CardArt seedInput={entry.card.id} hue={meta.hue} className="card-art" />
      </div>
      <p className="reveal-card-suit">{meta.label}</p>
      <h3 className="reveal-card-name">{entry.card.name}</h3>
      <div className="reveal-card-message reveal-card-message--light">
        <p className="reveal-card-message-label">Light</p>
        <p>{entry.card.light}</p>
      </div>
      <div className="reveal-card-message reveal-card-message--shadow">
        <p className="reveal-card-message-label">Shadow</p>
        <p>{entry.card.shadow}</p>
      </div>
    </article>
  );
}

export function RevealPanel({ entries, note }: RevealPanelProps) {
  const reducedMotion = usePrefersReducedMotion();

  return (
    <div className="reveal-panel" role="status" aria-live="polite">
      <motion.div
        className="reveal-panel-cards"
        initial={reducedMotion ? undefined : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.4 }}
      >
        {entries.map((entry) => (
          <RevealCard key={entry.card.id} entry={entry} />
        ))}
      </motion.div>
      <p className="reveal-panel-note">{note}</p>
    </div>
  );
}
