import { useState } from 'react';
import { CARDS } from '../data/cards';
import { findCard } from '../lib/deck';
import { commitPpfDraw, commitSingleDraw, getTodaysDraw } from '../lib/dailyLock';
import type { Card, PpfPosition } from '../types/card';

export interface SingleDrawState {
  isLocked: boolean;
  card: Card | null;
  draw: (cardId: string) => void;
}

export function useSingleDraw(): SingleDrawState {
  const [card, setCard] = useState<Card | null>(() => {
    const record = getTodaysDraw('single');
    return record ? (findCard(CARDS, record.cardId) ?? null) : null;
  });

  return {
    isLocked: card !== null,
    card,
    draw: (cardId: string) => {
      commitSingleDraw(cardId);
      setCard(findCard(CARDS, cardId) ?? null);
    },
  };
}

export type PpfCards = Record<PpfPosition, Card>;

export interface PpfDrawState {
  isLocked: boolean;
  cards: PpfCards | null;
  draw: (cardIds: Record<PpfPosition, string>) => void;
}

function resolvePpfCards(cardIds: Record<PpfPosition, string>): PpfCards | null {
  const past = findCard(CARDS, cardIds.past);
  const present = findCard(CARDS, cardIds.present);
  const future = findCard(CARDS, cardIds.future);
  if (!past || !present || !future) return null;
  return { past, present, future };
}

export function usePpfDraw(): PpfDrawState {
  const [cards, setCards] = useState<PpfCards | null>(() => {
    const record = getTodaysDraw('ppf');
    return record ? resolvePpfCards(record.cardIds) : null;
  });

  return {
    isLocked: cards !== null,
    cards,
    draw: (cardIds: Record<PpfPosition, string>) => {
      commitPpfDraw(cardIds);
      setCards(resolvePpfCards(cardIds));
    },
  };
}
