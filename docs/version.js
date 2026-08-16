// StockLab version — single source of truth, shown on every page.
// Bumped with each release (see CHANGELOG.md).
const STOCKLAB_VERSION = "v1.5.0";
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".sl-ver").forEach(e => e.textContent = STOCKLAB_VERSION);
});
