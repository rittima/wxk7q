export const mw = (n) => (n == null ? "n/a" : Math.round(n).toLocaleString("en-GB"));
export const signed = (n) => (n == null ? "n/a" : `${n > 0 ? "+" : n < 0 ? "-" : ""}${Math.abs(Math.round(n)).toLocaleString("en-GB")}`);

const dayFmt = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
export const dayLabel = (iso) => dayFmt.format(new Date(`${iso}T00:00:00Z`));
export const addDays = (iso, n) => {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};

const londonFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/London",
});
export const londonTime = (isoUtc) => (isoUtc ? londonFmt.format(new Date(isoUtc)) : "n/a");
