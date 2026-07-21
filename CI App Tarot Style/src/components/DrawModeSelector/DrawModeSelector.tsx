import './DrawModeSelector.css';
import type { DrawMode } from '../../types/card';

interface DrawModeSelectorProps {
  mode: DrawMode;
  onChange: (mode: DrawMode) => void;
  disabled?: boolean;
}

export function DrawModeSelector({ mode, onChange, disabled }: DrawModeSelectorProps) {
  return (
    <div className="draw-mode-selector" role="tablist" aria-label="Choose a draw">
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'single'}
        className={`draw-mode-btn ${mode === 'single' ? 'draw-mode-btn--active' : ''}`}
        onClick={() => onChange('single')}
        disabled={disabled}
      >
        Pick one card for today
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'ppf'}
        className={`draw-mode-btn ${mode === 'ppf' ? 'draw-mode-btn--active' : ''}`}
        onClick={() => onChange('ppf')}
        disabled={disabled}
      >
        Past · Present · Future
      </button>
    </div>
  );
}
