import { useState } from "react";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getForecast } from "./api.js";
import { useFetch } from "./hooks.js";
import { addDays, dayLabel, londonTime, mw, signed } from "./format.js";

function DecisionClock({ date, cutoff }) {
  const [h, m] = cutoff.split(":").map(Number);
  const pct = ((h + m / 60) / 48) * 100;
  return (
    <div className="clock" role="img" aria-label={`You decide by ${cutoff} on ${dayLabel(addDays(date, -1))}; power is delivered on ${dayLabel(date)}`}>
      <div className="clock-track">
        <div className="clock-delivery">Power delivered on {dayLabel(date)}</div>
        <div className="clock-mark" style={{ left: `${pct}%` }}>
          <span>You decide by {cutoff}</span>
        </div>
      </div>
      <div className="clock-axis">
        <span>{dayLabel(addDays(date, -1))}, 00:00</span>
        <span>{dayLabel(date)}, 00:00</span>
        <span>{dayLabel(addDays(date, 1))}, 00:00</span>
      </div>
    </div>
  );
}

function ChartTip({ active, payload, label, showActuals }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="tip">
      <strong>{label}</strong>
      <div>Forecast {mw(p.forecast)} MW</div>
      {p.lower != null && <div>Likely range {mw(p.lower)} to {mw(p.upper)} MW</div>}
      {showActuals && p.actual != null && <div>Actual {mw(p.actual)} MW</div>}
      <div className="muted">Published {londonTime(p.publish_time)}</div>
    </div>
  );
}

export default function DecisionView({ date, cutoff }) {
  const [showActuals, setShowActuals] = useState(false);
  const [demand, setDemand] = useState(35000);
  const { data, loading, error } = useFetch(() => getForecast(date, cutoff), [date, cutoff]);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <p className="loading">Loading forecast...</p>;

  const s = data.summary;
  const b = data.band;
  const pts = data.points.map((p) => ({ ...p, band: p.lower != null ? [p.lower, p.upper] : null }));
  const need = (w) => (w == null ? null : demand - w);

  return (
    <main className={loading ? "dim" : ""}>
      <DecisionClock date={date} cutoff={cutoff} />

      <section className="kpis" aria-label="Key figures">
        <div>
          <span className="k-label">Average forecast wind</span>
          <span className="k-value">{mw(s.avg_forecast)} MW</span>
          <span className="k-note">Peak {mw(s.peak_forecast)} MW, lowest {mw(s.min_forecast)} MW</span>
        </div>
        <div>
          <span className="k-label">Typical miss (90% of half-hours)</span>
          <span className="k-value">{b ? `${signed(b.q_lo)} to ${signed(b.q_hi)} MW` : "n/a"}</span>
          <span className="k-note">Actual minus forecast. Based on {b ? `${b.days} days, ${b.basis}` : "no history"}</span>
        </div>
        <div>
          <span className="k-label">Newest forecast used</span>
          <span className="k-value">{londonTime(s.latest_publish)}</span>
          <span className="k-note">Oldest {londonTime(s.earliest_publish)}. {s.n_points} of {s.expected_points} half-hours covered</span>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Wind forecast for {dayLabel(date)}, as known at {cutoff} the day before</h2>
          <label className="switch">
            <input type="checkbox" checked={showActuals} onChange={(e) => setShowActuals(e.target.checked)} disabled={!s.actuals_available} />
            Show what actually happened
          </label>
        </div>
        <div className="chart tall">
          <ResponsiveContainer>
            <ComposedChart data={pts} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="#D6DEE4" vertical={false} />
              <XAxis dataKey="label" interval={5} tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={mw} tick={{ fontSize: 12 }} width={64} label={{ value: "MW", angle: -90, position: "insideLeft", fontSize: 12 }} />
              <Tooltip content={<ChartTip showActuals={showActuals} />} />
              <Legend verticalAlign="top" height={28} />
              <Area dataKey="band" name="Likely range (90%)" stroke="none" fill="#9CC3E6" fillOpacity={0.5} isAnimationActive={false} />
              <Line dataKey="forecast" name="Forecast" stroke="#1F4E8C" strokeWidth={2.5} dot={false} isAnimationActive={false} />
              {showActuals && <Line dataKey="actual" name="Actual" stroke="#E0701B" strokeWidth={2} dot={false} isAnimationActive={false} />}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        {showActuals && data.day_metrics.n > 0 && (
          <p className="reading">
            On {dayLabel(date)} the forecast missed by {mw(data.day_metrics.mae)} MW on average and was{" "}
            {data.day_metrics.bias > 0 ? "too high" : "too low"} by {mw(Math.abs(data.day_metrics.bias))} MW on average.
          </p>
        )}
      </section>

      <section className="panel">
        <h2>How much else do you need to buy?</h2>
        <p className="reading">
          Demand data is outside this pilot, so enter an assumed demand. This view subtracts wind from a flat demand figure for the day.
        </p>
        <label className="inline">
          Assumed demand (MW)
          <input type="number" min="0" step="500" value={demand} onChange={(e) => setDemand(Number(e.target.value) || 0)} />
        </label>
        <div className="kpis compact">
          <div>
            <span className="k-label">Expected need from other sources</span>
            <span className="k-value">{mw(need(s.avg_forecast))} MW</span>
          </div>
          <div>
            <span className="k-label">Plan for up to (wind at the low end)</span>
            <span className="k-value">{mw(need(s.avg_lower))} MW</span>
          </div>
          <div>
            <span className="k-label">Could be as low as (wind at the high end)</span>
            <span className="k-value">{mw(need(s.avg_upper))} MW</span>
          </div>
        </div>
      </section>
    </main>
  );
}
