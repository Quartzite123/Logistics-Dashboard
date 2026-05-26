/* global React */
const { useState } = React;

const NAV_ITEMS = [
  { id: 'landing',  label: 'Landing',      sub: 'Overview',       badge: '959',  icon: 'sq' },
  { id: 'tat',      label: 'TAT Analysis', sub: 'Delivered SLA',  badge: '856',  icon: 'cl' },
  { id: 'transit',  label: 'Transit',      sub: 'In-flight',      badge: '103',  icon: 'tr' },
  { id: 'custom',   label: 'Customize',    sub: 'Ad-hoc query',   badge: null,   icon: 'fn' },
  { id: 'edit',     label: 'Edit',         sub: 'Reference data', badge: null,   icon: 'pn' },
];

const NavIcon = ({ kind }) => {
  const stroke = 'currentColor';
  const sw = 1.6;
  const props = { width: 16, height: 16, viewBox: '0 0 16 16', fill: 'none', stroke, strokeWidth: sw, strokeLinecap: 'round', strokeLinejoin: 'round' };
  switch (kind) {
    case 'sq': return (<svg {...props}><rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/><rect x="2" y="9" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/></svg>);
    case 'cl': return (<svg {...props}><circle cx="8" cy="8" r="6"/><path d="M8 4.5V8l2.5 2"/></svg>);
    case 'tr': return (<svg {...props}><path d="M2 11h9V4H2zM11 7h2.5l1.5 2v2h-4"/><circle cx="5" cy="13" r="1.3"/><circle cx="12" cy="13" r="1.3"/></svg>);
    case 'fn': return (<svg {...props}><path d="M3 4h10M5 8h6M7 12h2"/></svg>);
    case 'pn': return (<svg {...props}><path d="M3 13l3-1L13 5l-2-2-7 7-1 3z"/></svg>);
    default:   return null;
  }
};

function Sidebar({ active, onNav, sidebarWidth, theme, onTheme, onToggleCollapse }) {
  const collapsed = sidebarWidth === 'collapsed';

  return (
    <aside className="sidebar">
      <button
        className="sidebar-collapse-btn"
        onClick={onToggleCollapse}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {collapsed
            ? <path d="M6 4l4 4-4 4"/>
            : <path d="M10 4l-4 4 4 4"/>}
        </svg>
      </button>

      <div className="sidebar-brand">
        <div className="sidebar-brand-logo">
          <img src="assets/logo.png" alt="Kiirus" style={{ objectPosition: 'left center', objectFit: 'cover', transform: 'scale(2.6) translateX(-3px)' }} />
        </div>
        {!collapsed && (
          <div className="sidebar-brand-text">
            <div className="sidebar-brand-name">Kiirus Xpress</div>
            <div className="sidebar-brand-tag">Logistics · Intelligence</div>
          </div>
        )}
      </div>

      {!collapsed && <div className="sidebar-section-label">Workspace</div>}

      <nav className="sidebar-nav" role="navigation">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className="nav-row"
            aria-current={active === item.id ? 'true' : 'false'}
            onClick={() => onNav(item.id)}
            title={collapsed ? `${item.label} — ${item.sub}` : undefined}
          >
            <span className="nav-icon"><NavIcon kind={item.icon} /></span>
            {!collapsed && (
              <span className="nav-text">
                <span className="nav-label">{item.label}</span>
                <span className="nav-sublabel">{item.sub}</span>
              </span>
            )}
            {!collapsed && item.badge && <span className="nav-badge">{item.badge}</span>}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && (
          <div className="theme-toggle" role="tablist" aria-label="Theme">
            <button
              className="theme-toggle-btn"
              aria-pressed={theme === 'dark'}
              onClick={() => onTheme('dark')}
            >
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M13 9.5A5.5 5.5 0 1 1 6.5 3a4.5 4.5 0 0 0 6.5 6.5z"/></svg>
              Dark
            </button>
            <button
              className="theme-toggle-btn"
              aria-pressed={theme === 'light'}
              onClick={() => onTheme('light')}
            >
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="8" cy="8" r="3"/><path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3 3l1 1M12 12l1 1M3 13l1-1M12 4l1-1"/></svg>
              Light
            </button>
          </div>
        )}

        {!collapsed && (
          <>
            <div className="sidebar-status"><span className="status-dot"/>Local · Offline-ready</div>
            <div className="sidebar-status" style={{color: 'var(--text-dim)'}}>
              <span style={{ width:6, height:6, borderRadius:'50%', background:'var(--text-dim)' }}/>
              kiirus.db · 12.4 MB
            </div>
            <div className="sidebar-footer-meta">
              <span>v 1.3.0</span>
              <span>BUILT FOR KIIRUS</span>
            </div>
          </>
        )}
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
