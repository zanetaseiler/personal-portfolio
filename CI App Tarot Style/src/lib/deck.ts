import type { Card } from '../types/card';

export function shuffle<T>(items: T[], seed?: number): T[] {
  const arr = items.slice();
  let random = Math.random;
  if (seed !== undefined) {
    let s = seed;
    random = () => {
      s = (s * 1103515245 + 12345) & 0x7fffffff;
      return s / 0x7fffffff;
    };
  }
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export function cardsForSuit(cards: Card[], suit: Card['suit']): Card[] {
  return cards.filter((c) => c.suit === suit).sort((a, b) => a.number - b.number);
}

export function findCard(cards: Card[], id: string): Card | undefined {
  return cards.find((c) => c.id === id);
}
