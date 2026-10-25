async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/api/${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      msg = (await res.json()).detail || msg;
    } catch {
      /* body was not JSON */
    }
    throw new Error(msg);
  }
  return res.json();
}

export const getMeta = (cutoff) => get("meta", { cutoff });
export const getForecast = (delivery_date, cutoff) => get("forecast", { delivery_date, cutoff });
export const getAccuracy = (cutoff) => get("accuracy", { cutoff });
