const { useState, useEffect } = React;

const COLORS = {
  parchment: '#f5f4ed',
  ivory: '#faf9f5',
  terracotta: '#c96442',
  coral: '#d97757',
  nearBlack: '#141413',
  darkSurface: '#30302e',
  warmSilver: '#b0aea5',
  borderCream: '#f0eee6',
  borderWarm: '#e8e6dc',
  olive: '#5e5d59',
  stone: '#87867f',
};

// ───────── HEADER CARD ─────────
function Brief() {
  return (
    <div style={{
      width:'100%', height:'100%', background: COLORS.nearBlack, color: COLORS.warmSilver,
      padding:'56px 64px', boxSizing:'border-box', fontFamily:"'Instrument Serif', Georgia, serif",
      display:'flex', flexDirection:'column', justifyContent:'space-between',
    }}>
      <div style={{
        fontFamily:'JetBrains Mono, monospace', fontSize:11, letterSpacing:'0.22em',
        textTransform:'uppercase', color: COLORS.coral,
      }}>
        Helm · Favicon &amp; Motion · v01
      </div>
      <div style={{display:'flex', alignItems:'center', gap: 32}}>
        <WheelAnimated size={112} color={COLORS.coral} className="anim-spin-slow" />
        <div>
          <div style={{fontSize: 76, lineHeight: 1, letterSpacing: '-0.015em', color: '#faf9f5'}}>
            01 + 06<span style={{color: COLORS.coral}}>.</span>
          </div>
          <div style={{
            marginTop: 14, fontFamily: 'system-ui, sans-serif',
            fontSize: 16, lineHeight: 1.55, color: COLORS.warmSilver, maxWidth: 560,
          }}>
            The Wheel as the favicon/app icon · the serif wordmark as the in-app brand. Below: size-tuned mark variants, OS-context previews, and a motion set for both directions.
          </div>
        </div>
      </div>
      <div style={{
        display:'flex', gap: 24, fontFamily:'JetBrains Mono, monospace',
        fontSize: 10, letterSpacing: '0.18em', textTransform: 'uppercase', color: COLORS.stone,
      }}>
        <span>favicon · 16/32/48/180/512</span>
        <span>motion · 8 studies</span>
        <span style={{marginLeft:'auto', color: COLORS.warmSilver}}>autoplays · loops</span>
      </div>
    </div>
  );
}

// ───────── FAVICON GRID ─────────
function FaviconRow({ size, note, MarkComp, color = COLORS.nearBlack }) {
  return (
    <div className="fav-row">
      <div className="meta">
        <div className="big">{size}×{size}</div>
        <div>{note.title}</div>
        <div className="note">{note.usage}</div>
      </div>
      <div className="swatches">
        <div className="fav-swatch">
          <div className="fav-tile" style={{width: Math.max(size+10, 32), height: Math.max(size+10, 32), padding: 4}}>
            <MarkComp size={size} color={color} />
          </div>
          <div className="px">ivory</div>
        </div>
        <div className="fav-swatch">
          <div className="fav-tile dark" style={{width: Math.max(size+10, 32), height: Math.max(size+10, 32), padding: 4}}>
            <MarkComp size={size} color={COLORS.coral} />
          </div>
          <div className="px">dark</div>
        </div>
        <div className="fav-swatch">
          <div className="fav-tile terra" style={{width: Math.max(size+10, 32), height: Math.max(size+10, 32), padding: 4}}>
            <MarkComp size={size} color={COLORS.ivory} />
          </div>
          <div className="px">terracotta</div>
        </div>
        {size >= 48 && (
          <div className="fav-swatch">
            <div className="fav-tile" style={{
              width: Math.max(size+10, 32), height: Math.max(size+10, 32), padding: 4,
              borderRadius: Math.round(size * 0.22),
              background: COLORS.terracotta, border: 'none',
            }}>
              <MarkComp size={size} color={COLORS.ivory} />
            </div>
            <div className="px">app icon</div>
          </div>
        )}
      </div>
    </div>
  );
}

function FaviconSet({ title, tag, MarkComp, blurb, sizes }) {
  return (
    <div className="card">
      <div className="head">
        <span className="tag">{tag}</span>
        <span className="title">{title}</span>
        <span className="sub">favicon set</span>
      </div>
      <div className="body" style={{overflowY:'auto'}}>
        {sizes.map(([sz, note]) => (
          <FaviconRow key={sz} size={sz} note={note} MarkComp={MarkComp} />
        ))}
      </div>
      <div className="foot">{blurb}</div>
    </div>
  );
}

// ───────── IN CONTEXT (browser tab, dock, iOS) ─────────
function InContextWheel() {
  return (
    <div className="card">
      <div className="head">
        <span className="tag">In context</span>
        <span className="title">The Wheel · across surfaces</span>
        <span className="sub">tab · dock · home screen</span>
      </div>
      <div className="body">
        <div className="ctx-grid">
          {/* Browser tabs */}
          <div>
            <div className="ctx-label">Browser tab · 16px</div>
            <div className="browser-frame">
              <div className="tab-strip">
                <div className="tab">
                  <Wheel size={14} color={COLORS.nearBlack} />
                  <span>Helm — Overview</span>
                  <span className="x">×</span>
                </div>
                <div className="tab inactive">
                  <div style={{width:14, height:14, background:'#9aa', borderRadius:3}}></div>
                  <span>EVE-Mail</span>
                  <span className="x">×</span>
                </div>
                <div className="tab inactive">
                  <div style={{width:14, height:14, background:'#aa9', borderRadius:3}}></div>
                  <span>zKillboard</span>
                  <span className="x">×</span>
                </div>
              </div>
              <div className="url-bar">
                <span className="lock">⌬</span>
                <span>helm.local/characters/jerry-scintilla</span>
              </div>
              <div style={{height: 90, background: COLORS.parchment, display:'flex', alignItems:'center', padding:'0 18px', gap:10}}>
                <Wheel size={20} color={COLORS.nearBlack} />
                <span style={{fontFamily:"'Instrument Serif', Georgia, serif", fontSize: 22, color: COLORS.nearBlack}}>
                  Helm<span style={{color: COLORS.terracotta}}>.</span>
                </span>
              </div>
            </div>
          </div>

          {/* Bookmarks bar (smaller still) */}
          <div>
            <div className="ctx-label">Bookmarks bar · 14px</div>
            <div style={{
              background: COLORS.ivory, border: `1px solid ${COLORS.borderCream}`,
              borderRadius: 6, padding: '8px 6px', display: 'flex', gap: 4, alignItems:'center',
              fontFamily: 'system-ui, sans-serif', fontSize: 11, color: COLORS.olive,
            }}>
              {['Inbox','Calendar','Helm','EVE Forums','zKill','Reddit/r/eve'].map((n, i) => (
                <div key={n} style={{display:'flex', alignItems:'center', gap:5, padding:'4px 7px', borderRadius:4, background: i===2 ? COLORS.borderCream : 'transparent'}}>
                  {i === 2 ? <Wheel size={14} color={COLORS.nearBlack} /> : <div style={{width:14, height:14, borderRadius:3, background:['#c0d0e0','#d0c0a0','#000','#a0c0b0','#b0a0c0','#c0a0a0'][i]}}></div>}
                  <span>{n}</span>
                </div>
              ))}
            </div>

            <div className="ctx-label" style={{marginTop: 14}}>macOS dock · 52px</div>
            <div className="dock">
              <div className="dock-icon dummy"></div>
              <div className="dock-icon dummy b"></div>
              <div className="dock-icon terra"><Wheel size={36} color={COLORS.ivory} /></div>
              <div className="dock-icon"><Wheel size={36} color={COLORS.nearBlack} /></div>
              <div className="dock-icon dark"><Wheel size={36} color={COLORS.coral} /></div>
            </div>
          </div>

          {/* iOS home screen */}
          <div style={{gridColumn: '1 / -1'}}>
            <div className="ctx-label">iOS / Android home screen · 60×60 + 180px touch icon</div>
            <div style={{display:'grid', gridTemplateColumns:'auto 1fr', gap: 24, alignItems:'center'}}>
              <div className="ios-grid" style={{width: 280}}>
                {Array.from({length: 8}).map((_, i) => (
                  <div key={i} className={`ios-icon ${i === 5 ? 'helm' : 'dummy'}`}>
                    {i === 5 && <Wheel size={36} color={COLORS.ivory} />}
                  </div>
                ))}
              </div>
              <div style={{display:'flex', gap: 18, alignItems:'center'}}>
                <div style={{
                  width: 180, height: 180, borderRadius: 40,
                  background: COLORS.terracotta,
                  display:'flex', alignItems:'center', justifyContent:'center',
                  boxShadow: '0 12px 32px rgba(0,0,0,0.25)',
                }}>
                  <Wheel size={108} color={COLORS.ivory} />
                </div>
                <div style={{
                  width: 180, height: 180, borderRadius: 40,
                  background: COLORS.nearBlack,
                  display:'flex', alignItems:'center', justifyContent:'center',
                  boxShadow: '0 12px 32px rgba(0,0,0,0.25)',
                }}>
                  <Wheel size={108} color={COLORS.coral} />
                </div>
                <div style={{
                  width: 180, height: 180, borderRadius: 40,
                  background: COLORS.ivory, border: `1px solid ${COLORS.borderCream}`,
                  display:'flex', alignItems:'center', justifyContent:'center',
                }}>
                  <Wheel size={108} color={COLORS.nearBlack} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="foot">
        At ≤20px the wheel automatically swaps to a 4-spoke simplified form with thicker strokes so it stays legible. The full 8-spoke detail returns at 24px+. App icon padding follows the 22% radius ratio Apple/Google use.
      </div>
    </div>
  );
}

// ───────── MOTION CELLS ─────────
function MotionCell({ name, label, desc, children, dark = false }) {
  return (
    <div className={`motion-cell ${dark ? 'dark' : ''}`}>
      <div className="motion-label">{label}</div>
      <div className="motion-stage">{children}</div>
      <div className="name">{name}</div>
      <div className="desc">{desc}</div>
    </div>
  );
}

function WheelMotion() {
  return (
    <div className="card">
      <div className="head">
        <span className="tag">Motion · The Wheel</span>
        <span className="title">Four loops</span>
        <span className="sub">CSS · autoplay</span>
      </div>
      <div className="body">
        <div className="motion-grid">
          <MotionCell
            label="01 · Idle"
            name="Always at the helm"
            desc="A 24-second full rotation. Imperceptibly slow — only noticed if you stare. For empty-state hero, loading splash, or the dark-section banner."
          >
            <WheelAnimated size={120} color={COLORS.nearBlack} className="anim-spin-slow" />
          </MotionCell>
          <MotionCell
            label="02 · Loading"
            name="Spin"
            desc="1.6s linear loop. The workhorse — drop in anywhere data is being pulled from ESI."
          >
            <div style={{display:'flex', flexDirection:'column', gap: 14, alignItems:'center'}}>
              <WheelAnimated size={64} color={COLORS.terracotta} className="anim-spin-fast" />
              <span className="loading-caption">
                Syncing ESI
                <span className="dot-loader"><i></i><i></i><i></i></span>
              </span>
            </div>
          </MotionCell>
          <MotionCell
            label="03 · Reveal"
            name="Draw in"
            desc="Outer ring → inner ring → eight spokes draw in sequence. For first-paint / page-mount entrance. Plays once on load, loops here for preview."
          >
            <WheelDrawIn size={120} color={COLORS.nearBlack} />
          </MotionCell>
          <MotionCell
            label="04 · Pulse"
            name="Status pip"
            desc="Wheel static, center pip pulses terracotta. Use as a 'live / connected' indicator — system online, fleet armed, comms green."
            dark
          >
            <WheelPulse size={120} color={COLORS.warmSilver} pipColor={COLORS.coral} />
          </MotionCell>
        </div>
      </div>
      <div className="foot">
        All loops respect <code style={{fontFamily:'JetBrains Mono', background: COLORS.borderCream, padding:'1px 5px', borderRadius:3}}>prefers-reduced-motion</code> when wired into the app shell — disable rotation, keep pulse / draw-in single-shot.
      </div>
    </div>
  );
}

function WordmarkMotion() {
  return (
    <div className="card">
      <div className="head">
        <span className="tag">Motion · Wordmark</span>
        <span className="title">Four loops</span>
        <span className="sub">CSS · autoplay</span>
      </div>
      <div className="body">
        <div className="motion-grid">
          <MotionCell
            label="01 · Blink"
            name="Terminal stop"
            desc="The terracotta full-stop blinks like a CLI cursor. Subtle nod to Helm's plugin/CLI nature. For empty terminals, prompts, and the splash screen."
          >
            <div className="wm-base">
              Helm<span className="stop blink">.</span>
            </div>
          </MotionCell>

          <MotionCell
            label="02 · Pulse"
            name="Breathing dot"
            desc="Slower than blink, ease-in-out — feels alive rather than impatient. Better in passive contexts (footer, settings page)."
            dark
          >
            <div className="wm-base" style={{color: '#faf9f5'}}>
              Helm<span className="stop pulse" style={{color: COLORS.coral}}>.</span>
            </div>
          </MotionCell>

          <MotionCell
            label="03 · Reveal"
            name="Letter-in"
            desc="Each glyph fades up + de-blurs in sequence. Use once on app boot, never again. Looping here only for preview."
          >
            <div className="wm-base wm-letters">
              <span>H</span><span>e</span><span>l</span><span>m</span><span style={{color: COLORS.terracotta}}>.</span>
            </div>
          </MotionCell>

          <MotionCell
            label="04 · Underline"
            name="Course set"
            desc="A terracotta line draws left-to-right under the wordmark — like plotting a course. Holds, then resets. Suits the homepage hero."
          >
            <div className="wm-underline">
              <span className="wm-base">
                Helm<span className="stop">.</span>
              </span>
            </div>
          </MotionCell>
        </div>
      </div>
      <div className="foot">
        The blink is the most distinctive: it gives an otherwise quiet wordmark a heartbeat. Pair with the spinning wheel on the auth screen — wheel handles "working", dot handles "ready".
      </div>
    </div>
  );
}

// ───────── COMBINED ENTRANCE ─────────
function CombinedEntrance() {
  return (
    <div className="card">
      <div className="head">
        <span className="tag">Motion · Combined</span>
        <span className="title">App entrance · lockup</span>
        <span className="sub">5s loop</span>
      </div>
      <div className="body" style={{display:'flex', alignItems:'center', justifyContent:'center', background: COLORS.parchment}}>
        <CombinedLoop />
      </div>
      <div className="foot">
        Used once on login / app-shell mount. Wheel rotates into place with a soft over-shoot, then the wordmark glyphs fade up after it. Total runtime ~1.4s. Auto-disabled under reduced-motion.
      </div>
    </div>
  );
}

function CombinedLoop() {
  const [key, setKey] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setKey(k => k + 1), 4200);
    return () => clearInterval(id);
  }, []);
  return (
    <div key={key} style={{display:'flex', alignItems:'center', gap: 28}}>
      <div className="mark-wrap" style={{
        animation: 'rotate-snap 1.2s cubic-bezier(.34,1.56,.64,1) both',
        transformOrigin: 'center',
        display: 'inline-flex',
      }}>
        <WheelAnimated size={120} color={COLORS.nearBlack} />
      </div>
      <div style={{
        fontFamily:"'Instrument Serif', Georgia, serif",
        fontSize: 112, lineHeight: 1, letterSpacing: '-0.015em', color: COLORS.nearBlack,
        display: 'inline-flex', alignItems: 'baseline',
      }}>
        {['H','e','l','m'].map((ch, i) => (
          <span key={ch} style={{
            display:'inline-block',
            opacity: 0,
            animation: `letter-in .55s cubic-bezier(.2,.7,.3,1) ${0.6 + i*0.12}s forwards`,
          }}>{ch}</span>
        ))}
        <span style={{
          color: COLORS.terracotta,
          opacity: 0,
          display:'inline-block',
          animation: `letter-in .55s cubic-bezier(.2,.7,.3,1) 1.2s forwards, blink 1.1s steps(1) 2s infinite`,
        }}>.</span>
      </div>
    </div>
  );
}

// ───────── ROOT ─────────
const wheelSizes = [
  [512, { title: 'PWA splash · app store', usage: 'Maximum-resolution master. All other sizes derived from this.' }],
  [180, { title: 'Apple touch icon', usage: 'iOS home screen, Safari pinned tab. Full detail.' }],
  [64,  { title: 'Modern browser tab @ 2x', usage: 'Standard tab icon on hi-dpi displays. Full detail still works.' }],
  [48,  { title: 'Windows site icon · Android', usage: 'Last size where full 8-spoke detail reads clearly.' }],
  [32,  { title: 'Browser tab @ 2x · taskbar', usage: 'Mid variant: drop inner ring, thicker strokes, keep 8 spokes.' }],
  [16,  { title: 'Browser tab @ 1x · bookmark', usage: 'Tiny variant: 4 spokes only, fat strokes, large center pip.' }],
];

const hmarkSizes = [
  [180, { title: 'Apple touch icon · serif H.', usage: 'The wordmark stripped to its monogram for use as an icon.' }],
  [48,  { title: 'Windows site icon · favicon', usage: 'Serif "H" with terracotta period — readable at this size.' }],
  [32,  { title: 'Standard favicon', usage: 'Letter stays legible if you use a heavier-grade serif rather than Instrument.' }],
  [16,  { title: 'Tab favicon', usage: 'Borderline; the period dot risks subpixel loss. Wheel is the safer favicon for the Wordmark direction too.' }],
];

function App() {
  return (
    <DesignCanvas>
      <DCSection id="brief" title="Helm · Favicon & Motion" subtitle="01 The Wheel + 06 Wordmark — sizes and motion studies.">
        <DCArtboard id="hero" label="Brief" width={1180} height={420}>
          <Brief />
        </DCArtboard>
      </DCSection>

      <DCSection id="favicons" title="Favicon · size variants" subtitle="Mark optimized per size — small sizes get a simplified form so detail doesn't muddy.">
        <DCArtboard id="wheel-faviset" label="Wheel · all sizes" width={720} height={780}>
          <FaviconSet
            tag="01 · The Wheel"
            title="Sizes & colorways"
            MarkComp={Wheel}
            sizes={wheelSizes}
            blurb="Recommended primary favicon for both directions — its silhouette holds up far better at 16px than a serif H. Export the 512px as the master SVG, rasterize the rest."
          />
        </DCArtboard>
        <DCArtboard id="wordmark-faviset" label="Wordmark · derived H." width={620} height={780}>
          <FaviconSet
            tag="06 · Wordmark"
            title="Derived H. mark"
            MarkComp={HMark}
            sizes={hmarkSizes}
            blurb="If you prefer the wordmark direction, the favicon must derive from it — a serif H with the terracotta period. Honest, but loses detail below ~24px. Consider pairing with the Wheel as the small-size fallback."
          />
        </DCArtboard>
      </DCSection>

      <DCSection id="context" title="In context · OS &amp; browser surfaces" subtitle="Where the favicon actually lives. Wheel direction.">
        <DCArtboard id="ctx-all" label="Browser · dock · home" width={1180} height={760}>
          <InContextWheel />
        </DCArtboard>
      </DCSection>

      <DCSection id="motion" title="Motion studies" subtitle="All loops autoplay. Inspect any one fullscreen via the ⛶ in its header.">
        <DCArtboard id="motion-wheel" label="Wheel · 4 motions" width={1180} height={560}>
          <WheelMotion />
        </DCArtboard>
        <DCArtboard id="motion-word" label="Wordmark · 4 motions" width={1180} height={560}>
          <WordmarkMotion />
        </DCArtboard>
        <DCArtboard id="motion-combined" label="Combined entrance" width={1180} height={500}>
          <CombinedEntrance />
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
