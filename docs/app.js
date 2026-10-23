"use strict";
// Visualizes only the committed pinned JSON. Browser makes NO blockchain/RPC
// calls and requests NO wallet permissions. textContent prevents injected HTML.
const $ = (id) => document.getElementById(id);
const human = (n, maximumFractionDigits = 2) => {
  const value = Number(n);
  return Number.isFinite(value)
    ? new Intl.NumberFormat("en-US", {maximumFractionDigits}).format(value)
    : "—";
};
const terminal = (value, len = 12) => value.length > len * 2 + 3
  ? value.slice(0, len + 2) + "…" + value.slice(-len) : value;
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};
function makePool(p, total) {
  const section = el("article", "pool");
  const title = el("div", "pool-title");
  title.append(el("h3", "", p.name), el("div", "kind", p.kind + "-curve basic pool"));
  const middle = el("div", "pool-middle");
  const bar = el("div", "bar");
  const fill = el("div");
  const pct = total > 0 ? (Number(p.musdReserve) / total) * 100 : 0;
  fill.style.width = (Math.max(0, Math.min(pct, 100))).toFixed(2) + "%";
  fill.title = pct.toFixed(2) + "% of these three pools' MUSD reserves";
  bar.append(fill);
  middle.append(bar, el("div", "bal", p.asset0 + ": " + human(p.reserve0, 4)
    + "   |   " + p.asset1 + ": " + human(p.reserve1, 4)));
  const foot = el("div", "bal",
    "MUSD reserve / token balance difference: " + p.reserveBalanceDifference + " MUSD");
  middle.append(foot);
  const last = el("div", "last");
  last.append(el("strong", "", human(p.musdReserve, 2)),
    el("small", "", "MUSD in pool · " + pct.toFixed(1) + "% of 3-pool total"));
  const link = el("a", "", "View verified contract ↗");
  link.href = "https://explorer.mezo.org/address/" + p.address;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  last.append(link);
  section.append(title, middle, last);
  return section;
}
async function load() {
  try {
    const res = await fetch("./latest.json", {cache: "no-store"});
    if (!res.ok) throw new Error("Snapshot HTTP " + res.status);
    const d = await res.json();
    if (d.schemaVersion !== "mezo-musd-proofdesk-v1" || d.network?.chainId !== 31612
        || !Array.isArray(d.pools) || d.pools.length !== 3
        || typeof d.block?.hash !== "string"
        || typeof d.assets?.MUSD?.totalSupply !== "string"
        || typeof d.assets?.MEZO?.totalSupply !== "string") {
      throw new Error("Wrong chain, missing fields or evidence schema");
    }
    $("snapshot-state").textContent = "PINNED · " + d.block.timestampUTC.replace("+00:00", " UTC");
    $("musd-supply").textContent = human(d.assets.MUSD.totalSupply, 0);
    $("mezo-supply").textContent = human(d.assets.MEZO.totalSupply, 0);
    $("pooled-musd").textContent = human(d.measuredPoolMUSDReserves, 2);
    $("block-number").textContent = human(d.block.number, 0);
    $("block-time").textContent = "At " + d.block.timestampUTC.replace("+00:00", " UTC");
    $("block-hash").textContent = d.block.hash;
    $("musd-codehash").textContent = d.assets.MUSD.runtime.sha256;
    $("mezo-codehash").textContent = d.assets.MEZO.runtime.sha256;
    const list = $("pool-list");
    list.replaceChildren(...d.pools.map(p => makePool(p, Number(d.measuredPoolMUSDReserves))));
  } catch (error) {
    $("snapshot-state").textContent = "EVIDENCE NOT VERIFIED";
    $("pool-list").replaceChildren(el("p", "data-warning",
      "Pinned JSON unavailable or incompatible. Stop. Never substitute fake balances. " + String(error.message)));
  }
}
load();
