import {BRAND} from '@/lib/brand';
/** The user's approved artwork, exported without redrawing the identity. */
export default function BrandMark({wordmark=false}:{wordmark?:boolean}){return <span className="brand-artwork"><img className={wordmark?'brand-wordmark':'brand-mark'} src={wordmark?BRAND.logo:BRAND.mark} alt={wordmark?`${BRAND.name} — ${BRAND.tagline}`:''} width={wordmark?351:108} height={wordmark?100:93}/></span>}
