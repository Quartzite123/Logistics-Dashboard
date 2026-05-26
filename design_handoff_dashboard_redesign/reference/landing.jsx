/* global React */
const { useMemo: useMemoLanding } = React;

// Synthetic KPI snapshot driven by the README sample distribution.
const KPI = {
  total: 959,
  delivered: 856,
  inTransit: 71,
  pending: 16,
  rto: 4,
  dispatched: 11,
  manifested: 1,
  early: 549,
  onTime: 161,
  late: 146,
  oda: 142,
  nonOda: 814,
  dateFrom: '25 Nov 2025',
  dateTo: '24 Feb 2026',
};
const pct = (n, base = KPI.total) => ((n / base) * 100).toFixed(1) + '%';

// Tiny inline sparkline
const Spark = ({ data, color = 'var(--accent)' }) => {
  const w = 56, h = 22;
  const max = Math.max(...data), min = Math.min(...data);
  const step = w / (data.length - 1);
  const pts = data.map((v, i) => `${i*step},${h - ((v-min)/(max-min||1))*h}`).join(' ');
  return (
    <svg className="kpi-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round"/>
    </svg>
  );
};

const KpiCard = ({ label, value, valueColor='accent', unit, meta, delta, deltaKind, spark, progress, accent=false, dateRange=false, children, icon }) => (
  <div className={`kpi ${accent ? 'kpi-accent' : ''} ${dateRange ? 'kpi-daterange' : ''}`}>
    <div className="kpi-label">
      <span>{label}</span>
      {icon && <span className="kpi-label-ic">{icon}</span>}
    </div>
    {spark && <Spark data={spark} color={valueColor==='ok' ? 'var(--ok)' : valueColor==='bad' ? 'var(--bad)' : 'var(--accent)'}/>}
    <div className={`kpi-value text-${valueColor}`}>
      {value}
      {unit && <span className="kpi-value-unit">{unit}</span>}
    </div>
    {progress != null && (
      <div className="kpi-progress"><div className={`kpi-progress-fill ${progress.kind || ''}`} style={{ width: `${progress.value}%` }}/></div>
    )}
    {(meta || delta) && (
      <div className="kpi-meta">
        {delta && <span className={`kpi-delta ${deltaKind || 'flat'}`}>{delta}</span>}
        {meta && <span>{meta}</span>}
      </div>
    )}
    {children}
  </div>
);

// Donut chart for "Overall Delivery Performance"
function DeliveryDonut() {
  const segments = [
    { label: 'Early',              value: KPI.early,    color: 'var(--ok)' },
    { label: 'On Time',            value: KPI.onTime,   color: 'var(--info)' },
    { label: 'Late',               value: KPI.late,     color: 'var(--bad)' },
    { label: 'Not Yet Delivered',  value: KPI.total - KPI.delivered, color: 'var(--text-dim)' },
  ];
  const total = segments.reduce((s, x) => s + x.value, 0);
  const r = 64, c = 80;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  const slaPct = ((KPI.early + KPI.onTime) / KPI.delivered * 100).toFixed(1);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24, alignItems: 'center' }}>
      <svg width={c*2} height={c*2} viewBox={`0 0 ${c*2} ${c*2}`}>
        <circle cx={c} cy={c} r={r} fill="none" stroke="var(--bg-elev-3)" strokeWidth="14"/>
        {segments.map((s, i) => {
          const length = (s.value / total) * circ;
          const dash = `${length} ${circ - length}`;
          const el = (
            <circle key={i} cx={c} cy={c} r={r} fill="none"
              stroke={s.color} strokeWidth="14"
              strokeDasharray={dash}
              strokeDashoffset={-offset}
              transform={`rotate(-90 ${c} ${c})`}
              strokeLinecap="butt"
            />
          );
          offset += length;
          return el;
        })}
        <text x={c} y={c-4} textAnchor="middle" fontSize="22" fontFamily="var(--font-mono)" fontWeight="500" fill="var(--accent)">{slaPct}%</text>
        <text x={c} y={c+14} textAnchor="middle" fontSize="10" letterSpacing="0.16em" fill="var(--text-dim)">SLA</text>
      </svg>

      <div className="legend">
        {segments.map((s) => (
          <div className="legend-row" key={s.label}>
            <span className="legend-swatch" style={{ background: s.color }}/>
            <span className="legend-label">{s.label}</span>
            <span className="legend-value mono">{s.value.toLocaleString()}</span>
            <span className="legend-pct mono">{((s.value/total)*100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Bar chart — top 8 companies, stacked Early/On Time/Late
function CompanyBars() {
  const companies = [
    { name: 'KENSTAR',     total: 638, e: 392, o: 102, l: 102 },
    { name: 'CLAD METAL',  total: 84,  e: 51,  o: 14,  l: 12 },
    { name: 'NIRMAL',      total: 47,  e: 29,  o: 8,   l: 7 },
    { name: 'BAJAJ ELEC',  total: 42,  e: 22,  o: 10,  l: 8 },
    { name: 'ORIENT',      total: 38,  e: 19,  o: 9,   l: 9 },
    { name: 'CROMPTON',    total: 31,  e: 15,  o: 8,   l: 7 },
    { name: 'HAVELLS',     total: 28,  e: 12,  o: 7,   l: 8 },
    { name: 'PHILIPS',     total: 22,  e: 9,   o: 6,   l: 6 },
  ];
  const max = Math.max(...companies.map(c => c.total));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {companies.map((c) => {
        const w = (c.total / max) * 100;
        const eW = (c.e / c.total) * w;
        const oW = (c.o / c.total) * w;
        const lW = (c.l / c.total) * w;
        return (
          <div key={c.name} style={{ display: 'grid', gridTemplateColumns: '110px 1fr 56px', alignItems: 'center', gap: 12, fontSize: 12 }}>
            <span style={{ color: 'var(--text-muted)', fontSize: 11, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</span>
            <div style={{ display: 'flex', height: 16, background: 'var(--bg-elev-2)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${eW}%`, background: 'var(--ok)' }}/>
              <div style={{ width: `${oW}%`, background: 'var(--info)' }}/>
              <div style={{ width: `${lW}%`, background: 'var(--bad)' }}/>
            </div>
            <span className="mono" style={{ color: 'var(--text)', textAlign: 'right', fontSize: 11 }}>{c.total}</span>
          </div>
        );
      })}
      <div style={{ display: 'flex', gap: 14, marginTop: 6, paddingTop: 12, borderTop: '1px solid var(--border)', fontSize: 11, color: 'var(--text-muted)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--ok)' }}/>Early</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--info)' }}/>On Time</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--bad)' }}/>Late</span>
      </div>
    </div>
  );
}

function Landing() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">Section 01 · Landing</div>
          <h1 className="page-title">Operations Snapshot</h1>
          <div className="page-sub">959 shipments across 21 companies · synced 4 minutes ago</div>
        </div>
        <div className="row">
          <button className="btn btn-ghost">
            <svg className="ic" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M3 13h10M8 11V3M5 6l3-3 3 3"/></svg>
            Export
          </button>
          <button className="btn btn-primary">
            <svg className="ic" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 11v2h10v-2M8 3v8M5 6l3-3 3 3"/></svg>
            Upload new file
          </button>
        </div>
      </div>

      {/* Row 1: Totals */}
      <div className="kpi-grid kpi-row-3">
        <KpiCard
          label="Total Orders"
          value={KPI.total.toLocaleString()}
          valueColor="primary"
          accent
          spark={[34,42,38,45,52,49,58,63,70,68,75,72,78,82]}
          meta="All shipments in pipeline"
          delta="+12.4%"
          deltaKind="up"
        />
        <KpiCard
          label="Delivered"
          value={KPI.delivered.toLocaleString()}
          valueColor="ok"
          accent
          spark={[28,34,40,38,46,52,48,58,63,65,71,68,74,78]}
          meta={`${pct(KPI.delivered)} of total`}
          delta="+8.1%"
          deltaKind="up"
          progress={{ value: (KPI.delivered/KPI.total)*100, kind: 'ok' }}
        />
        <KpiCard
          label="In Transit"
          value={KPI.inTransit}
          valueColor="info"
          accent
          spark={[12,15,18,14,16,18,14,12,10,11,9,8,9,7]}
          meta={`${pct(KPI.inTransit)} of total`}
          delta="−2.4%"
          deltaKind="down"
        />
      </div>

      {/* Row 2: Status + Date */}
      <div className="kpi-grid kpi-row-3">
        <KpiCard
          label="Pending"
          value={KPI.pending}
          valueColor="warn"
          accent
          meta={`${pct(KPI.pending)} of total`}
          delta="+1"
          deltaKind="flat"
        />
        <KpiCard
          label="RTO"
          value={KPI.rto}
          valueColor="bad"
          accent
          meta={`${pct(KPI.rto)} of total`}
          delta="0"
          deltaKind="flat"
        />
        <KpiCard
          label="Date Range"
          dateRange
          valueColor="primary"
          value={<span><span className="mono">{KPI.dateFrom}</span><span className="kpi-daterange-arrow mono">→</span><span className="mono">{KPI.dateTo}</span></span>}
          meta="92 days · weekly cadence"
        />
      </div>

      {/* Row 3: SLA quad */}
      <div className="kpi-grid kpi-row-4">
        <KpiCard
          label="Early"
          value={KPI.early}
          valueColor="ok"
          accent
          meta={`${((KPI.early/KPI.delivered)*100).toFixed(1)}% of delivered`}
          progress={{ value: (KPI.early/KPI.delivered)*100, kind: 'ok' }}
        />
        <KpiCard
          label="On Time"
          value={KPI.onTime}
          valueColor="info"
          accent
          meta={`${((KPI.onTime/KPI.delivered)*100).toFixed(1)}% of delivered`}
          progress={{ value: (KPI.onTime/KPI.delivered)*100, kind: 'ok' }}
        />
        <KpiCard
          label="SLA (Early + On Time)"
          value={KPI.early + KPI.onTime}
          valueColor="accent"
          accent
          meta={`${(((KPI.early+KPI.onTime)/KPI.delivered)*100).toFixed(1)}% SLA compliance`}
          progress={{ value: ((KPI.early+KPI.onTime)/KPI.delivered)*100 }}
        />
        <KpiCard
          label="Late"
          value={KPI.late}
          valueColor="bad"
          accent
          meta={`${((KPI.late/KPI.delivered)*100).toFixed(1)}% of delivered`}
          progress={{ value: (KPI.late/KPI.delivered)*100, kind: 'bad' }}
        />
      </div>

      {/* Row 4: ODA */}
      <div className="kpi-grid kpi-row-2">
        <KpiCard
          label="ODA · Out of delivery area"
          value={KPI.oda}
          valueColor="warn"
          accent
          unit="pincodes"
          meta={`${pct(KPI.oda)} of total`}
          delta="+1 day SLA penalty"
          deltaKind="flat"
        />
        <KpiCard
          label="Non-ODA"
          value={KPI.nonOda.toLocaleString()}
          valueColor="primary"
          accent
          unit="pincodes"
          meta={`${pct(KPI.nonOda)} of total`}
        />
      </div>

      {/* Charts */}
      <div className="charts-grid" style={{ marginTop: 'var(--space-xl)' }}>
        <div className="chart-card">
          <div className="chart-head">
            <div>
              <h3 className="chart-title">Overall Delivery Performance</h3>
              <div className="chart-sub">All 959 shipments · SLA buckets</div>
            </div>
            <span className="pill pill-accent"><span className="dot"/>Live</span>
          </div>
          <div className="chart-body">
            <DeliveryDonut/>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-head">
            <div>
              <h3 className="chart-title">Per-company breakdown</h3>
              <div className="chart-sub">Top 8 of 21 companies · stacked SLA</div>
            </div>
            <div className="chart-controls">
              <div className="seg">
                <button aria-pressed="true">Bar</button>
                <button>Line</button>
                <button>Pie</button>
              </div>
              <div className="seg">
                <button aria-pressed="true">Company</button>
                <button>Region</button>
                <button>Month</button>
                <button>Status</button>
              </div>
            </div>
          </div>
          <div className="chart-body">
            <CompanyBars/>
          </div>
        </div>
      </div>
    </>
  );
}

window.Landing = Landing;
