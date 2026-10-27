import { useEffect, useState } from "react";
import { useFetch } from "./hooks.js";
import { getMeta } from "./api.js";
import DecisionView from "./DecisionView.jsx";
import AccuracyView from "./AccuracyView.jsx";

export default function App() {
  const [tab, setTab] = useState("decision");
  const [cutoff, setCutoff] = useState("09:30");
  const [date, setDate] = useState(null);
  const meta = useFetch(() => getMeta(cutoff), [cutoff]);

  useEffect(() => {
    if (meta.data && !date) setDate(meta.data.delivery_dates[Math.floor(meta.data.delivery_dates.length / 2)]);
  }, [meta.data, date]);

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>Wind forecast desk</h1>
          <p className="sub">Day-ahead buying: what wind will deliver, and how far to trust it. Great Britain, national level.</p>
        </div>
        <nav className="tabs" role="tablist">
          <button role="tab" aria-selected={tab === "decision"} onClick={() => setTab("decision")}>
            Decision view
          </button>
          <button role="tab" aria-selected={tab === "accuracy"} onClick={() => setTab("accuracy")}>
            Forecast accuracy
          </button>
        </nav>
      </header>

      {meta.data?.source === "synthetic" && (
        <div className="banner" role="status">
          You are looking at generated demo data, not Elexon data. Run <code>python -m scripts.build_cache</code> to load the real January 2026 data.
        </div>
      )}

      {meta.error && <div className="error">Could not load data: {meta.error}</div>}

      {meta.data && (
        <>
          <section className="controls" aria-label="Controls">
            {tab === "decision" && (
              <label>
                Delivery day
                <select style={{ cursor: 'pointer' }} value={date || ""} onChange={(e) => setDate(e.target.value)}>
                  {meta.data.delivery_dates.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Decision cutoff, London time on the day before
              <input  type="time" value={cutoff} onChange={(e) => e.target.value && setCutoff(e.target.value)} />
            </label>
            <p className="hint">Only forecasts published at or before the cutoff are used.</p>
          </section>

          {tab === "decision" && date && <DecisionView date={date} cutoff={cutoff} />}
          {tab === "accuracy" && <AccuracyView cutoff={cutoff} />}
        </>
      )}
      {meta.loading && !meta.data && <p className="loading">Loading data...</p>}
    </div>
  );
}
