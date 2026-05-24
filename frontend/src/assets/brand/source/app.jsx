const { useState } = React;

// ───────── Helpers ─────────
const COLORS = {
  parchment: '#f5f4ed',
  ivory: '#faf9f5',
  terracotta: '#c96442',
  coral: '#d97757',
  nearBlack: '#141413',
  darkSurface: '#30302e',
  warmSilver: '#b0aea5',
  borderCream: '#f0eee6',
  olive: '#5e5d59',
  stone: '#87867f',
};

// One full logo artboard: hero mark, horizontal lockup, three colorway variants, footnote
function LogoBoard({ Mark, label, blurb, markSize = 180 }) {
  return (
    <div className="art with-desc">
      {/* Hero mark — primary stage on parchment */}
      <div className="stage">
        <Mark size={markSize} color={COLORS.nearBlack} />
      </div>

      {/* Horizontal lockup */}
      <div className="lockup">
        <Mark size={64} color={COLORS.nearBlack} />
        <Wordmark size={64} />
      </div>

      {/* Colorway variants */}
      <div className="variants">
        <div className="v-terra">
          <Mark size={48} color={COLORS.ivory} />
          <span className="v-label">on terracotta</span>
        </div>
        <div className="v-ivory">
          <Mark size={48} color={COLORS.nearBlack} />
          <span className="v-label">on ivory</span>
        </div>
        <div className="v-dark">
          <Mark size={48} color={COLORS.coral} />
          <span className="v-label">on near-black</span>
        </div>
      </div>

      {/* Footnote */}
      <div className="desc">
        <span className="tag">{label}</span>
        <span>{blurb}</span>
      </div>
    </div>
  );
}

// Wordmark-only artboard (Direction 06)
function WordmarkBoard() {
  return (
    <div className="art with-desc">
      <div className="stage" style={{flexDirection:'column', gap: 20}}>
        <div style={{
          fontFamily: "'Instrument Serif', Georgia, serif",
          fontWeight: 400,
          fontSize: 168,
          lineHeight: 1,
          letterSpacing: '-0.02em',
          color: COLORS.nearBlack,
        }}>
          Helm<span style={{color: COLORS.terracotta}}>.</span>
        </div>
        <div style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          color: COLORS.olive,
        }}>
          fleet&nbsp;·&nbsp;command&nbsp;·&nbsp;quietly
        </div>
      </div>

      <div className="lockup" style={{justifyContent:'flex-start', paddingLeft: 36}}>
        <span style={{
          fontFamily: "'Instrument Serif', Georgia, serif",
          fontWeight: 400,
          fontSize: 64,
          letterSpacing: '-0.01em',
          color: COLORS.nearBlack,
        }}>
          Helm<span style={{color: COLORS.terracotta}}>.</span>
        </span>
        <span style={{
          flex: 1,
          marginLeft: 18,
          paddingLeft: 18,
          borderLeft: `1px solid ${COLORS.borderCream}`,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: COLORS.stone,
          lineHeight: 1.5,
        }}>
          EVE Online<br/>fleet ops
        </span>
      </div>

      <div className="variants">
        <div className="v-terra">
          <span style={{fontFamily:"'Instrument Serif',Georgia,serif", fontSize:48, color:COLORS.ivory, letterSpacing:'-0.01em'}}>Helm.</span>
          <span className="v-label">on terracotta</span>
        </div>
        <div className="v-ivory">
          <span style={{fontFamily:"'Instrument Serif',Georgia,serif", fontSize:48, color:COLORS.nearBlack, letterSpacing:'-0.01em'}}>Helm<span style={{color:COLORS.terracotta}}>.</span></span>
          <span className="v-label">on ivory</span>
        </div>
        <div className="v-dark">
          <span style={{fontFamily:"'Instrument Serif',Georgia,serif", fontSize:48, color:COLORS.warmSilver, letterSpacing:'-0.01em'}}>Helm<span style={{color:COLORS.coral}}>.</span></span>
          <span className="v-label">on near-black</span>
        </div>
      </div>

      <div className="desc">
        <span className="tag">06 · Wordmark only</span>
        <span>No mark, just authority. Instrument Serif at heavy size with a terracotta full-stop. Pairs cleanly beside the existing UI without competing.</span>
      </div>
    </div>
  );
}

// ───────── Banner / Hero card ─────────
function HelmHero() {
  return (
    <div style={{
      width: '100%', height: '100%',
      background: COLORS.nearBlack,
      color: COLORS.warmSilver,
      borderRadius: 0,
      padding: '64px 72px',
      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
      boxSizing: 'border-box',
      fontFamily: "'Instrument Serif', Georgia, serif",
    }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
        letterSpacing: '0.22em', textTransform: 'uppercase', color: COLORS.coral,
      }}>
        Logo Exploration · Helm · v01
      </div>

      <div style={{display:'flex', alignItems:'center', gap: 36}}>
        <LogoWheel size={140} color={COLORS.coral} />
        <div>
          <div style={{
            fontSize: 96, lineHeight: 1, letterSpacing: '-0.015em', color: '#faf9f5',
          }}>
            Helm<span style={{color: COLORS.coral}}>.</span>
          </div>
          <div style={{
            marginTop: 14,
            fontFamily: 'system-ui, sans-serif',
            fontSize: 17, lineHeight: 1.55, color: COLORS.warmSilver, maxWidth: 540,
          }}>
            Named after the command center of a spaceship — a thin, fast host for EVE Online fleet ops, with plugins for everything else. Six directions below.
          </div>
        </div>
      </div>

      <div style={{
        display: 'flex', gap: 28, alignItems: 'center',
        fontFamily: 'JetBrains Mono, monospace', fontSize: 10,
        letterSpacing: '0.18em', textTransform: 'uppercase',
        color: COLORS.stone,
      }}>
        <span>parchment&nbsp;#f5f4ed</span>
        <span>terracotta&nbsp;#c96442</span>
        <span>near-black&nbsp;#141413</span>
        <span style={{marginLeft:'auto', color: COLORS.warmSilver}}>Instrument Serif · JetBrains Mono</span>
      </div>
    </div>
  );
}

// ───────── Usage demo: simulated app header ─────────
function HeaderDemo({ Mark, name }) {
  return (
    <div style={{
      width:'100%', height:'100%', background: COLORS.parchment,
      display:'flex', flexDirection:'column', boxSizing:'border-box',
      fontFamily: 'system-ui, sans-serif',
    }}>
      {/* Top nav bar */}
      <div style={{
        height: 56,
        background: COLORS.ivory,
        borderBottom: `1px solid ${COLORS.borderCream}`,
        display: 'flex', alignItems: 'center',
        padding: '0 20px', gap: 14,
      }}>
        <Mark size={26} color={COLORS.nearBlack} />
        <span style={{
          fontFamily: "'Instrument Serif', Georgia, serif",
          fontSize: 24, color: COLORS.nearBlack, letterSpacing: '-0.01em',
        }}>
          Helm<span style={{color: COLORS.terracotta}}>.</span>
        </span>
        <span style={{
          marginLeft: 18,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10, letterSpacing:'0.16em', textTransform:'uppercase', color: COLORS.stone,
        }}>
          Overview&nbsp;·&nbsp;Skills&nbsp;·&nbsp;Assets&nbsp;·&nbsp;Plugins
        </span>
        <div style={{marginLeft:'auto', display:'flex', gap:10, alignItems:'center'}}>
          <div style={{
            padding: '6px 12px',
            background: COLORS.terracotta, color: COLORS.ivory,
            borderRadius: 8, fontSize: 13, fontWeight: 500,
          }}>Log in with EVE</div>
        </div>
      </div>

      {/* Body */}
      <div style={{flex:1, padding: '32px 28px', display:'grid', gridTemplateColumns:'1fr 1fr', gap: 20}}>
        <div style={{
          background: COLORS.ivory, border: `1px solid ${COLORS.borderCream}`,
          borderRadius: 16, padding: '24px 24px 28px',
          display:'flex', flexDirection:'column', gap: 8,
        }}>
          <div style={{fontFamily:'JetBrains Mono, monospace', fontSize:10, letterSpacing:'0.18em', textTransform:'uppercase', color: COLORS.coral}}>Capsuleer</div>
          <div style={{fontFamily:"'Instrument Serif',Georgia,serif", fontSize:32, color: COLORS.nearBlack, lineHeight:1.1}}>Jerry Scintilla</div>
          <div style={{fontSize: 13, color: COLORS.olive}}>Pandemic Horde · Goonswarm Federation</div>
          <div style={{
            marginTop: 14, display:'flex', gap: 16,
            fontFamily:'JetBrains Mono, monospace', fontSize:11, color: COLORS.olive,
          }}>
            <span>SP&nbsp;124.7m</span><span>ISK&nbsp;14.2b</span><span>Ships&nbsp;48</span>
          </div>
        </div>
        <div style={{
          background: COLORS.nearBlack, color: COLORS.warmSilver,
          borderRadius: 16, padding: '24px 24px 28px',
          display:'flex', flexDirection:'column', gap: 10,
        }}>
          <div style={{fontFamily:'JetBrains Mono, monospace', fontSize:10, letterSpacing:'0.18em', textTransform:'uppercase', color: COLORS.coral}}>Fleet status</div>
          <div style={{fontFamily:"'Instrument Serif',Georgia,serif", fontSize:32, color:'#faf9f5', lineHeight:1.1}}>Form-up at 23:00</div>
          <div style={{fontSize:13, color: COLORS.warmSilver}}>1DQ1-A · Keepstar · 142 pilots committed</div>
          <div style={{marginTop:'auto', alignSelf:'flex-end'}}>
            <Mark size={32} color={COLORS.coral} />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        height: 40, background: COLORS.ivory, borderTop: `1px solid ${COLORS.borderCream}`,
        display:'flex', alignItems:'center', padding:'0 20px',
        fontFamily:'JetBrains Mono, monospace', fontSize:10, letterSpacing:'0.14em', textTransform:'uppercase', color: COLORS.stone,
      }}>
        <span>{name}</span>
        <span style={{marginLeft:'auto'}}>helm v0.1.0-alpha</span>
      </div>
    </div>
  );
}

// ───────── Root ─────────
function App() {
  return (
    <DesignCanvas>
      <DCSection id="hero" title="Helm" subtitle="Logo exploration — six directions on the existing Anthropic-inspired palette.">
        <DCArtboard id="banner" label="Brief" width={1080} height={420}>
          <HelmHero />
        </DCArtboard>
      </DCSection>

      <DCSection id="marks" title="01 — 06 · Mark directions" subtitle="Each board: large mark · horizontal lockup · three colorways · notes.">
        <DCArtboard id="wheel" label="01 · The Wheel" width={540} height={780}>
          <LogoBoard
            Mark={LogoWheel}
            label="01 · The Wheel"
            blurb="The literal helm. Eight spokes, balanced ring, single center pip. Reads instantly at any size — favicon-safe. Most on-the-nose, most ownable."
          />
        </DCArtboard>
        <DCArtboard id="star" label="02 · North Star" width={540} height={780}>
          <LogoBoard
            Mark={LogoStar}
            label="02 · North Star"
            blurb="A four-point navigation star with a hollowed sparkle. Solid fill, no strokes — feels printed rather than drawn. Quietly editorial."
          />
        </DCArtboard>
        <DCArtboard id="reticle" label="03 · Reticle" width={540} height={780}>
          <LogoBoard
            Mark={LogoReticle}
            label="03 · Reticle"
            blurb="A tactical crosshair: outer ring, inner ring, cardinal ticks. The most EVE-native direction — overlay-friendly, telemetry-feel."
          />
        </DCArtboard>
        <DCArtboard id="pod" label="04 · The Pod" width={540} height={780}>
          <LogoBoard
            Mark={LogoPod}
            label="04 · The Pod"
            blurb="Capsuleer in a pod: nested circles with orbital pips. Soft, almost domestic — leans into Anthropic's editorial warmth rather than fighting it."
          />
        </DCArtboard>
        <DCArtboard id="hex" label="05 · Hex Node" width={540} height={780}>
          <LogoBoard
            Mark={LogoHex}
            label="05 · Hex Node"
            blurb="A starmap coordinate — hexagonal frame with internal hex pip and six inward ticks. Reads as 'system node' to any EVE pilot."
          />
        </DCArtboard>
        <DCArtboard id="wordmark" label="06 · Wordmark" width={540} height={780}>
          <WordmarkBoard />
        </DCArtboard>
      </DCSection>

      <DCSection id="inuse" title="In use · application header" subtitle="Each mark dropped into a simulated Helm app header so you can compare presence in context.">
        <DCArtboard id="use-wheel" label="In use · 01 Wheel" width={780} height={460}>
          <HeaderDemo Mark={LogoWheel} name="01 — Wheel" />
        </DCArtboard>
        <DCArtboard id="use-star" label="In use · 02 Star" width={780} height={460}>
          <HeaderDemo Mark={LogoStar} name="02 — Star" />
        </DCArtboard>
        <DCArtboard id="use-reticle" label="In use · 03 Reticle" width={780} height={460}>
          <HeaderDemo Mark={LogoReticle} name="03 — Reticle" />
        </DCArtboard>
        <DCArtboard id="use-pod" label="In use · 04 Pod" width={780} height={460}>
          <HeaderDemo Mark={LogoPod} name="04 — Pod" />
        </DCArtboard>
        <DCArtboard id="use-hex" label="In use · 05 Hex" width={780} height={460}>
          <HeaderDemo Mark={LogoHex} name="05 — Hex" />
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
