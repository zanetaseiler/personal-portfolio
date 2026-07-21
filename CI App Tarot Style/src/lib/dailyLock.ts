import { localDateKey } from './dateKey';
import type { DrawMode } from '../types/card';

const STORAGE_KEYS: Record<DrawMode, string> = {
  single: 'ci-oracle:draw:single',
  ppf: 'ci-oracle:draw:ppf',
};

export interface SingleDrawRecord {
  dateKey: string;
  cardId: string;
}

export interface PpfDrawRecord {
  dateKey: string;
  cardIds: { past: string; present: string; future: string };
}

type DrawRecord<M extends DrawMode> = M extends 'single' ? SingleDrawRecord : PpfDrawRecord;

export function getTodaysDraw<M extends DrawMode>(mode: M): DrawRecord<M> | null {
  const raw = localStorage.getItem(STORAGE_KEYS[mode]);
  if (!raw) return null;

  try {
    const record = JSON.parse(raw) as DrawRecord<M>;
    if (!record || record.dateKey !== localDateKey()) return null;
    return record;
  } catch {
    return null;
  }
}

export function commitSingleDraw(cardId: string): void {
  const record: SingleDrawRecord = { dateKey: localDateKey(), cardId };
  localStorage.setItem(STORAGE_KEYS.single, JSON.stringify(record));
}

export function commitPpfDraw(cardIds: PpfDrawRecord['cardIds']): void {
  const record: PpfDrawRecord = { dateKey: localDateKey(), cardIds };
  localStorage.setItem(STORAGE_KEYS.ppf, JSON.stringify(record));
}
