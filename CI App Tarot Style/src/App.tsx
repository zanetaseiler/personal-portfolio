import { useState } from 'react';
import './App.css';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { DrawModeSelector } from './components/DrawModeSelector/DrawModeSelector';
import { DeckSpread } from './components/DeckSpread/DeckSpread';
import { SpreadPositions } from './components/SpreadPositions/SpreadPositions';
import { RevealPanel } from './components/RevealPanel/RevealPanel';
import { CARDS } from './data/cards';
import { findCard } from './lib/deck';
import { useSingleDraw, usePpfDraw } from './hooks/useDailyDraw';
import { usePrefersReducedMotion } from './hooks/usePrefersReducedMotion';
import type { DrawMode, PpfPosition, Card as CardData } from './types/card';

const FLIP_SETTLE_MS = 650;
const PPF_ORDER: PpfPosition[] = ['past', 'present', 'future'];
const ALL_CARD_IDS = new Set(CARDS.map((c) => c.id));

function App() {
  const [mode, setMode] = useState<DrawMode>('single');
  const singleDraw = useSingleDraw();
  const ppfDraw = usePpfDraw();
  const reducedMotion = usePrefersReducedMotion();

  const [pendingSingleId, setPendingSingleId] = useState<string | null>(null);
  const [pendingPpfIds, setPendingPpfIds] = useState<string[]>([]);

  const flipDelay = reducedMotion ? 0 : FLIP_SETTLE_MS;

  function handleSingleClick(id: string) {
    if (pendingSingleId) return;
    setPendingSingleId(id);
    window.setTimeout(() => {
      singleDraw.draw(id);
      setPendingSingleId(null);
    }, flipDelay);
  }

  function handlePpfClick(id: string) {
    if (pendingPpfIds.includes(id) || pendingPpfIds.length >= 3) return;
    const next = [...pendingPpfIds, id];
    setPendingPpfIds(next);
    if (next.length === 3) {
      window.setTimeout(() => {
        ppfDraw.draw({ past: next[0], present: next[1], future: next[2] });
        setPendingPpfIds([]);
      }, flipDelay);
    }
  }

  function handleResetPpf() {
    setPendingPpfIds([]);
  }

  const hasPendingPicks = mode === 'single' ? pendingSingleId !== null : pendingPpfIds.length > 0;

  const singleDisabledIds = pendingSingleId ? ALL_CARD_IDS : new Set<string>();
  const singleRevealedIds = pendingSingleId ? new Set([pendingSingleId]) : new Set<string>();

  const ppfDisabledIds = pendingPpfIds.length === 3 ? ALL_CARD_IDS : new Set(pendingPpfIds);
  const ppfRevealedIds = new Set(pendingPpfIds);

  const ppfFilled: Partial<Record<PpfPosition, CardData>> = {};
  pendingPpfIds.forEach((id, i) => {
    const card = findCard(CARDS, id);
    if (card) ppfFilled[PPF_ORDER[i]] = card;
  });

  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <DrawModeSelector
          mode={mode}
          onChange={(next) => !hasPendingPicks && setMode(next)}
          disabled={hasPendingPicks}
        />

        {mode === 'single' &&
          (singleDraw.isLocked && singleDraw.card ? (
            <RevealPanel
              entries={[{ card: singleDraw.card }]}
              note="Come back tomorrow for a new single-card draw."
            />
          ) : (
            <DeckSpread
              cards={CARDS}
              disabledIds={singleDisabledIds}
              revealedIds={singleRevealedIds}
              onCardClick={handleSingleClick}
            />
          ))}

        {mode === 'ppf' &&
          (ppfDraw.isLocked && ppfDraw.cards ? (
            <RevealPanel
              entries={[
                { positionLabel: 'Past', card: ppfDraw.cards.past },
                { positionLabel: 'Present', card: ppfDraw.cards.present },
                { positionLabel: 'Future', card: ppfDraw.cards.future },
              ]}
              note="Come back tomorrow for a new Past · Present · Future draw."
            />
          ) : (
            <>
              <SpreadPositions
                filled={ppfFilled}
                onReset={handleResetPpf}
                canReset={pendingPpfIds.length > 0 && pendingPpfIds.length < 3}
              />
              <DeckSpread
                cards={CARDS}
                disabledIds={ppfDisabledIds}
                revealedIds={ppfRevealedIds}
                onCardClick={handlePpfClick}
              />
            </>
          ))}
      </main>
      <Footer />
    </div>
  );
}

export default App;
