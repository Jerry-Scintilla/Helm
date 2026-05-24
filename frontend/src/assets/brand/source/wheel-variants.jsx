/* Wheel variants optimized for different sizes.
   At small sizes, full 8-spoke + inner ring detail muddies — use simpler forms.
   stroke widths are tuned in the 100×100 viewBox so the rendered px stroke
   matches design intent at each display size. */

// Full detail — for 48px and up
const WheelFull = ({ size = 96, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="3.2" strokeLinecap="round">
    <circle cx="50" cy="50" r="32" />
    <circle cx="50" cy="50" r="9" />
    {Array.from({length: 8}).map((_, i) => {
      const a = (i * 45) * Math.PI / 180;
      const x1 = 50 + Math.cos(a) * 12;
      const y1 = 50 + Math.sin(a) * 12;
      const x2 = 50 + Math.cos(a) * 44;
      const y2 = 50 + Math.sin(a) * 44;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
    })}
    <circle cx="50" cy="50" r="2.2" fill={color} stroke="none" />
  </svg>
);

// Mid detail — drop inner ring, thicker strokes. For 24–32px.
const WheelMid = ({ size = 32, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round">
    <circle cx="50" cy="50" r="30" />
    {Array.from({length: 8}).map((_, i) => {
      const a = (i * 45) * Math.PI / 180;
      const x1 = 50 + Math.cos(a) * 15;
      const y1 = 50 + Math.sin(a) * 15;
      const x2 = 50 + Math.cos(a) * 45;
      const y2 = 50 + Math.sin(a) * 45;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
    })}
    <circle cx="50" cy="50" r="5" fill={color} stroke="none" />
  </svg>
);

// Tiny — 4 spokes only, thick strokes. For 16px.
const WheelTiny = ({ size = 16, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round">
    <circle cx="50" cy="50" r="28" />
    {Array.from({length: 4}).map((_, i) => {
      const a = (i * 90) * Math.PI / 180;
      const x1 = 50 + Math.cos(a) * 14;
      const y1 = 50 + Math.sin(a) * 14;
      const x2 = 50 + Math.cos(a) * 50;
      const y2 = 50 + Math.sin(a) * 50;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
    })}
    <circle cx="50" cy="50" r="9" fill={color} stroke="none" />
  </svg>
);

// Picks the right variant based on display size
const Wheel = ({ size = 64, color = '#141413' }) => {
  if (size <= 20) return <WheelTiny size={size} color={color} />;
  if (size <= 36) return <WheelMid size={size} color={color} />;
  return <WheelFull size={size} color={color} />;
};

// H. mark derived from the wordmark — for use as a favicon when wordmark is the chosen direction
const HMark = ({ size = 64, color = '#141413', dotColor = '#c96442' }) => (
  <span className="h-mark" style={{ fontSize: size, color }}>
    H<span style={{ color: dotColor }}>.</span>
  </span>
);

// Animated wheel — applies a className to the SVG for CSS animations
const WheelAnimated = ({ size = 96, color = '#141413', className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none"
       stroke={color} strokeWidth="3.2" strokeLinecap="round"
       className={className}
       style={{ transformOrigin: '50% 50%' }}>
    <circle cx="50" cy="50" r="32" />
    <circle cx="50" cy="50" r="9" />
    {Array.from({length: 8}).map((_, i) => {
      const a = (i * 45) * Math.PI / 180;
      const x1 = 50 + Math.cos(a) * 12;
      const y1 = 50 + Math.sin(a) * 12;
      const x2 = 50 + Math.cos(a) * 44;
      const y2 = 50 + Math.sin(a) * 44;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
    })}
    <circle cx="50" cy="50" r="2.2" fill={color} stroke="none" />
  </svg>
);

// Draw-in wheel — spokes and ring stroke in
const WheelDrawIn = ({ size = 96, color = '#141413' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="3.2" strokeLinecap="round">
    <circle cx="50" cy="50" r="32" className="draw-ring" pathLength="220" />
    <circle cx="50" cy="50" r="9" className="draw-ring" pathLength="220" style={{ animationDelay: '0.2s' }} />
    {Array.from({length: 8}).map((_, i) => {
      const a = (i * 45) * Math.PI / 180;
      const x1 = 50 + Math.cos(a) * 12;
      const y1 = 50 + Math.sin(a) * 12;
      const x2 = 50 + Math.cos(a) * 44;
      const y2 = 50 + Math.sin(a) * 44;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} className="draw-spoke" pathLength="60" style={{ animationDelay: `${0.4 + i * 0.06}s` }} />;
    })}
    <circle cx="50" cy="50" r="2.2" fill={color} stroke="none" />
  </svg>
);

// Wheel with pulsing center pip
const WheelPulse = ({ size = 96, color = '#141413', pipColor = '#c96442' }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke={color} strokeWidth="3.2" strokeLinecap="round">
    <circle cx="50" cy="50" r="32" />
    <circle cx="50" cy="50" r="9" />
    {Array.from({length: 8}).map((_, i) => {
      const a = (i * 45) * Math.PI / 180;
      const x1 = 50 + Math.cos(a) * 12;
      const y1 = 50 + Math.sin(a) * 12;
      const x2 = 50 + Math.cos(a) * 44;
      const y2 = 50 + Math.sin(a) * 44;
      return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
    })}
    <circle cx="50" cy="50" r="3.5" fill={pipColor} stroke="none" className="anim-pulse" style={{ transformOrigin: '50% 50%', transformBox: 'fill-box' }} />
  </svg>
);

Object.assign(window, { Wheel, WheelFull, WheelMid, WheelTiny, HMark, WheelAnimated, WheelDrawIn, WheelPulse });
