/* global React */
function StubSection({ name, eyebrow, desc }) {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">{eyebrow}</div>
          <h1 className="page-title">{name}</h1>
          <div className="page-sub">{desc}</div>
        </div>
        <div className="row">
          <button className="btn btn-primary">
            <svg className="ic" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 11v2h10v-2M8 3v8M5 6l3-3 3 3"/></svg>
            Upload new file
          </button>
        </div>
      </div>
      <div style={{
        background: 'var(--bg-elev-1)',
        border: '1px dashed var(--border-strong)',
        borderRadius: 'var(--card-radius)',
        padding: '64px 24px',
        textAlign: 'center',
        color: 'var(--text-muted)',
      }}>
        <div style={{ fontSize: 13, color: 'var(--text-dim)', letterSpacing: '0.16em', textTransform: 'uppercase', marginBottom: 12 }}>Not yet redesigned</div>
        <div style={{ fontSize: 16, color: 'var(--text)', marginBottom: 6 }}>{name} screen will mirror the Landing system</div>
        <div style={{ fontSize: 13 }}>Tables, filters and charts use the same tokens, pills, cards and segmented controls you see on Landing.</div>
      </div>
    </>
  );
}

window.StubSection = StubSection;
