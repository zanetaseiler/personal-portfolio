import { CardArt } from '../CardArt/CardArt';
import { BRAND_BACK_HUE, CARD_BACK_SEED } from '../../lib/cardArt';

export function CardBack() {
  return (
    <div className="card-back">
      <CardArt seedInput={CARD_BACK_SEED} hue={BRAND_BACK_HUE} className="card-art" />
      <span className="card-back-mark">CI</span>
    </div>
  );
}
