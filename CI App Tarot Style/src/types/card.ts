export type Suit = 'body' | 'mind' | 'spirit';

export interface Card {
  id: string;
  suit: Suit;
  number: number;
  name: string;
  light: string;
  shadow: string;
}

export type DrawMode = 'single' | 'ppf';

export type PpfPosition = 'past' | 'present' | 'future';
