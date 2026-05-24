/* Six Helm logo marks — all geometric primitives only.
   Each component takes (size, color) and returns an SVG mark.
   Sized to a 100×100 viewBox so it composes cleanly. */

// 01 — The Wheel: a ship's helm, eight spokes radiating out.
const LogoWheel = ({ size = 96, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="3.2" strokeLinecap="round">
    {/* outer ring */}
    <circle cx="50" cy="50" r="32" />
    {/* inner ring */}
    <circle cx="50" cy="50" r="9" />
    {/* eight spoke-handles, simple lines from inner edge to past outer ring */}
    {Array.from({length: 8}).map((_, i) => {
      const a = (i * 45) * Math.PI / 180;
      const x1 = 50 + Math.cos(a) * 12;
      const y1 = 50 + Math.sin(a) * 12;
      const x2 = 50 + Math.cos(a) * 44;
      const y2 = 50 + Math.sin(a) * 44;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
    })}
    {/* center pip */}
    <circle cx="50" cy="50" r="2.2" fill={color} stroke="none" />
  </svg>
);

// 02 — North Star: navigation/celestial reference. 4-point compass star.
const LogoStar = ({ size = 96, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill={color} stroke="none">
    {/* primary 4-point star */}
    <path d="M50 8 L54 46 L92 50 L54 54 L50 92 L46 54 L8 50 L46 46 Z" />
    {/* inner negative diamond for sparkle */}
    <path d="M50 38 L52 48 L62 50 L52 52 L50 62 L48 52 L38 50 L48 48 Z" fill="#f5f4ed" />
  </svg>
);

// 03 — Reticle: targeting crosshair, EVE tactical feel
const LogoReticle = ({ size = 96, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round">
    <circle cx="50" cy="50" r="30" />
    {/* cardinal ticks extending through ring */}
    <line x1="50" y1="6" x2="50" y2="28" />
    <line x1="50" y1="72" x2="50" y2="94" />
    <line x1="6" y1="50" x2="28" y2="50" />
    <line x1="72" y1="50" x2="94" y2="50" />
    {/* inner dot */}
    <circle cx="50" cy="50" r="3.5" fill={color} stroke="none" />
    {/* inner small ring */}
    <circle cx="50" cy="50" r="12" />
  </svg>
);

// 04 — Pod: concentric circles, EVE capsuleer-in-pod
const LogoPod = ({ size = 96, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="3">
    <circle cx="50" cy="50" r="36" />
    <circle cx="50" cy="50" r="22" />
    <circle cx="50" cy="50" r="6" fill={color} stroke="none" />
    {/* four orbital pips at cardinal */}
    <circle cx="50" cy="6" r="2.2" fill={color} stroke="none" />
    <circle cx="50" cy="94" r="2.2" fill={color} stroke="none" />
    <circle cx="6" cy="50" r="2.2" fill={color} stroke="none" />
    <circle cx="94" cy="50" r="2.2" fill={color} stroke="none" />
  </svg>
);

// 05 — Hex Coordinate: starmap node
const LogoHex = ({ size = 96, color = '#141413' }) => {
  // pointy-top hexagon centered at (50,50), radius 38
  const pts = Array.from({length:6}).map((_,i) => {
    const a = (i * 60 - 90) * Math.PI / 180;
    return [50 + 38*Math.cos(a), 50 + 38*Math.sin(a)].map(n => n.toFixed(2)).join(',');
  }).join(' ');
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="miter">
      <polygon points={pts} />
      {/* inner small hex */}
      {(() => {
        const inner = Array.from({length:6}).map((_,i) => {
          const a = (i * 60 - 90) * Math.PI / 180;
          return [50 + 12*Math.cos(a), 50 + 12*Math.sin(a)].map(n => n.toFixed(2)).join(',');
        }).join(' ');
        return <polygon points={inner} fill={color} stroke="none" />;
      })()}
      {/* coordinate ticks pointing in from each vertex */}
      {Array.from({length:6}).map((_,i) => {
        const a = (i * 60 - 90) * Math.PI / 180;
        const x1 = 50 + 38*Math.cos(a);
        const y1 = 50 + 38*Math.sin(a);
        const x2 = 50 + 26*Math.cos(a);
        const y2 = 50 + 26*Math.sin(a);
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
      })}
    </svg>
  );
};

// 06 — Monogram H + crossbar as a horizon line, with a small star above
const LogoMonogram = ({ size = 96, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="6" strokeLinecap="square">
    {/* H */}
    <line x1="22" y1="22" x2="22" y2="86" />
    <line x1="78" y1="22" x2="78" y2="86" />
    <line x1="22" y1="54" x2="78" y2="54" />
    {/* small star above the crossbar (tiny diamond) */}
    <path d="M50 8 L53 16 L50 24 L47 16 Z" fill={color} stroke="none" />
  </svg>
);

// Helpers — Wordmark used in lockups
const Wordmark = ({ size = 56, color = '#141413', stopColor = '#c96442', stop = true }) => (
  <span style={{
    fontFamily: "'Instrument Serif', Georgia, serif",
    fontWeight: 400,
    fontSize: `${size}px`,
    letterSpacing: '-0.01em',
    lineHeight: 1,
    color,
  }}>
    Helm{stop && <span style={{color: stopColor}}>.</span>}
  </span>
);

// Stacked-lockup variant
const StackedLockup = ({ Mark, markSize = 120, wordSize = 36, color = '#141413' }) => (
  <div style={{display:'flex', flexDirection:'column', alignItems:'center', gap: 14}}>
    <Mark size={markSize} color={color} />
    <Wordmark size={wordSize} color={color} />
  </div>
);

Object.assign(window, {
  LogoWheel, LogoStar, LogoReticle, LogoPod, LogoHex, LogoMonogram,
  Wordmark, StackedLockup,
});
