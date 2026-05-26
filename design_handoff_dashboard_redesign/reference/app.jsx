/* global React, ReactDOM, Sidebar, Landing, StubSection, useTweaks, TweaksPanel, TweakSection, TweakRadio */
const { useState: useAppState, useEffect: useAppEffect } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "dark",
  "density": "balanced",
  "sidebar": "standard"
}/*EDITMODE-END*/;

function App() {
  const [active, setActive] = useAppState('landing');
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // Apply tweaks to <html>
  useAppEffect(() => {
    document.documentElement.dataset.theme = t.theme;
    document.documentElement.dataset.density = t.density;
    document.documentElement.dataset.sidebar = t.sidebar;
  }, [t.theme, t.density, t.sidebar]);

  const onTheme = (mode) => setTweak('theme', mode);
  const onToggleCollapse = () => {
    setTweak('sidebar', t.sidebar === 'collapsed' ? (t._lastSidebar || 'standard') : 'collapsed');
    if (t.sidebar !== 'collapsed') setTweak('_lastSidebar', t.sidebar);
  };

  let content;
  switch (active) {
    case 'tat':     content = <StubSection name="TAT Analysis" eyebrow="Section 02 · TAT" desc="Delivered-only SLA inspection · 856 rows"/>; break;
    case 'transit': content = <StubSection name="Transit"      eyebrow="Section 03 · Transit" desc="Non-delivered triage · 103 rows · Stuck-first sort"/>; break;
    case 'custom':  content = <StubSection name="Customize"    eyebrow="Section 04 · Customize" desc="Ad-hoc filtered query · Detail / Aggregate"/>; break;
    case 'edit':    content = <StubSection name="Edit"         eyebrow="Section 05 · Edit" desc="Region matrix + 22 K pincode master · Save → Apply"/>; break;
    default:        content = <Landing/>;
  }

  return (
    <div className="app">
      <Sidebar
        active={active}
        onNav={setActive}
        sidebarWidth={t.sidebar}
        theme={t.theme}
        onTheme={onTheme}
        onToggleCollapse={onToggleCollapse}
      />
      <main className="main">
        {content}
      </main>

      <TweaksPanel title="Tweaks">
        <TweakSection label="Theme">
          <TweakRadio
            value={t.theme}
            options={['dark', 'light']}
            onChange={(v) => setTweak('theme', v)}
          />
        </TweakSection>
        <TweakSection label="Density">
          <TweakRadio
            value={t.density}
            options={['compact', 'balanced', 'spacious']}
            onChange={(v) => setTweak('density', v)}
          />
        </TweakSection>
        <TweakSection label="Sidebar width">
          <TweakRadio
            value={t.sidebar}
            options={['collapsed', 'narrow', 'standard', 'wide']}
            onChange={(v) => setTweak('sidebar', v)}
          />
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
