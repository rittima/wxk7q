import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getAccuracy } from "./api.js";
import { useFetch } from "./hooks.js";
import { dayLabel, mw, signed } from "./format.js";

const BLUE = "#102F5C";
const GOLD = "#B88700";
const GREY = "#7C8B97";
const axis = { fontSize: 12 };

function Panel({ title, note, children }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {note && <p className="reading">{note}</p>}
      <div className="chart">
        <ResponsiveContainer>{children}</ResponsiveContainer>
      </div>
    </section>
  );
}

export default function AccuracyView({ cutoff }) {
  const { data, loading, error } = useFetch(() => getAccuracy(cutoff), [cutoff]);
  if (error) return <div className="error">{error}</div>;
  if (!data) return <p className="loading">Loading accuracy...</p>;

  const s = data.summary;
  const daily = data.daily.map((d) => ({ ...d, label: dayLabel(d.delivery_date).slice(4) }));
  const hours = data.by_hour.map((d) => ({ ...d, label: String(d.hour).padStart(2, "0") }));
  const histEvery = Math.max(1, Math.ceil(data.histogram.length / 12));

  return (
    <main className={loading ? "dim" : ""}>
      <section className="kpis" aria-label="Accuracy summary">
        <div>
          <span className="k-label">Average miss (MAE)</span>
          <span className="k-value">{mw(s.mae)} MW</span>
          <span className="k-note">{s.mape_pct != null ? `About ${s.mape_pct}% of actual output` : ""}</span>
        </div>
        <div>
          <span className="k-label">Large misses weigh more (RMSE)</span>
          <span className="k-value">{mw(s.rmse)} MW</span>
          <span className="k-note">Closer to MAE means errors are evenly sized</span>
        </div>
        <div>
          <span className="k-label">Bias (forecast minus actual)</span>
          <span className="k-value">{signed(s.bias)} MW</span>
          <span className="k-note">{Math.abs(s.bias) < 0.1 * s.mae ? "Little systematic bias" : s.bias > 0 ? "Forecast runs high: risk of under-buying" : "Forecast runs low: risk of over-buying"}</span>
        </div>
        <div>
          <span className="k-label">9 in 10 half-hours miss by less than</span>
          <span className="k-value">{mw(s.p90_abs)} MW</span>
          <span className="k-note">95th percentile {mw(s.p95_abs)} MW</span>
        </div>
      </section>

      <p className="reading wide">
        {data.date_from} to {data.date_to}: {s.n.toLocaleString("en-GB")} half-hours compared, using the forecast available at {cutoff} on the day before delivery
        (forecasts were {data.horizon_range_h[0]} to {data.horizon_range_h[1]} hours old at the target time). Average wind was {mw(data.mean_actual)} MW.
      </p>

      <div className="grid">
        <Panel title="Error by forecast age" note="Longer lead time, larger error. Late half-hours of the delivery day rely on older forecasts.">
          <BarChart data={data.by_horizon} margin={{ top: 8, right: 8, left: 8 }}>
            <CartesianGrid stroke="#D6E0EC" vertical={false} />
            <XAxis dataKey="label" tick={axis} />
            <YAxis tickFormatter={mw} tick={axis} width={56} />
            <Tooltip formatter={(v) => `${mw(v)} MW`} />
            <Legend />
            <Bar dataKey="mae" name="Average miss" fill={BLUE} />
            <Bar dataKey="rmse" name="RMSE" fill={GREY} />
          </BarChart>
        </Panel>

        <Panel title="Error by time of day" note="Local time on the delivery day. Bars: average miss. Line: bias.">
          <ComposedChart data={hours} margin={{ top: 8, right: 8, left: 8 }}>
            <CartesianGrid stroke="#D6E0EC" vertical={false} />
            <XAxis dataKey="label" tick={axis} interval={1} />
            <YAxis tickFormatter={mw} tick={axis} width={56} />
            <Tooltip formatter={(v) => `${mw(v)} MW`} />
            <Legend />
            <Bar dataKey="mae" name="Average miss" fill={BLUE} />
            <Line dataKey="bias" name="Bias" stroke={GOLD} strokeWidth={2} dot={false} />
          </ComposedChart>
        </Panel>

        <Panel title="Error by delivery day" note="Some days are much harder to forecast than others.">
          <ComposedChart data={daily} margin={{ top: 8, right: 8, left: 8 }}>
            <CartesianGrid stroke="#D6E0EC" vertical={false} />
            <XAxis dataKey="label" tick={axis} interval={2} />
            <YAxis tickFormatter={mw} tick={axis} width={56} />
            <Tooltip formatter={(v) => `${mw(v)} MW`} />
            <Legend />
            <Bar dataKey="mae" name="Average miss" fill={BLUE} />
            <Line dataKey="bias" name="Bias" stroke={GOLD} strokeWidth={2} dot={false} />
          </ComposedChart>
        </Panel>

        <Panel title="How big are the misses?" note="Number of half-hours by error size (MW). Left of zero: forecast too low.">
          <BarChart data={data.histogram} margin={{ top: 8, right: 8, left: 8 }}>
            <CartesianGrid stroke="#D6E0EC" vertical={false} />
            <XAxis dataKey="label" tick={axis} interval={histEvery - 1} />
            <YAxis tick={axis} width={48} />
            <Tooltip labelFormatter={(l) => `${signed(Number(l))} MW and above`} formatter={(v) => [v, "Half-hours"]} />
            <Bar dataKey="count" fill={BLUE} />
          </BarChart>
        </Panel>
      </div>
    </main>
  );
}
