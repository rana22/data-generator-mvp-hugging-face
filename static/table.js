function ensureDialog() {
  let dialog = document.getElementById("cell-value-dialog");
  if (dialog) return dialog;

  dialog = document.createElement("dialog");
  dialog.id = "cell-value-dialog";
  dialog.style.padding = "20px";
  dialog.style.maxWidth = "800px";
  dialog.style.width = "80vw";

  dialog.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px;">
      <strong>Expanded value</strong>
      <button id="cell-value-close" type="button">Close</button>
    </div>
    <pre id="cell-value-content" style="white-space:pre-wrap; word-break:break-word; margin:0;"></pre>
  `;

  document.body.appendChild(dialog);

  dialog.querySelector("#cell-value-close").addEventListener("click", () => {
    dialog.close();
  });

  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  return dialog;
}

function openValueDialog(value) {
  const dialog = ensureDialog();
  const content = dialog.querySelector("#cell-value-content");
  content.textContent = value == null ? "" : String(value);
  dialog.showModal();
}

function expandableTextRenderer(params) {
  const maxLen = 80;
  const fullText = params.value == null ? "" : String(params.value);
  const isLong = fullText.length > maxLen;

  const eGui = document.createElement("div");
  eGui.style.whiteSpace = "normal";
  eGui.style.lineHeight = "1.3";
  eGui.style.cursor = isLong ? "pointer" : "default";

  const textSpan = document.createElement("span");
  textSpan.textContent = !isLong ? fullText : fullText.slice(0, maxLen) + "...";

  eGui.appendChild(textSpan);

  if (isLong) {
    eGui.title = "Click to expand";
    eGui.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openValueDialog(fullText);
    });
  }

  return eGui;
}

document.addEventListener("click", (e) => {
  const el = e.target.closest(".expandable-cell");
  if (!el) return;

  e.preventDefault();
  e.stopPropagation();
  openValueDialog(el.dataset.fullValue || "");
});

// window.addEventListener("load", initGrid);
// new MutationObserver(initGrid).observe(document.body, { childList: true, subtree: true });
function toggleExpand(el) {
  if (el.classList.contains("expandable-cell")) {
      el.classList.remove("expandable-cell");
  } else {
      el.classList.add("expandable-cell");
  }
}

function parseCellValue(text) {
  const t = (text || '').trim().replace(/,/g, '');
  if (!t) return { type: 0, value: '' };

  const num = Number(t);
  if (!Number.isNaN(num) && /^-?\d+(\.\d+)?$/.test(t)) {
      return { type: 1, value: num };
  }

  const dt = Date.parse(t);
  if (!Number.isNaN(dt)) {
      return { type: 2, value: dt };
  }

  return { type: 3, value: t.toLowerCase() };
}

function sortHtmlTable(tableId, colIndex) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const tbody = table.tBodies[0];
  if (!tbody) return;

  const currentCol = table.dataset.sortCol;
  const currentDir = table.dataset.sortDir || 'asc';
  const asc = !(currentCol === String(colIndex) && currentDir === 'asc');

  const rows = Array.from(tbody.rows);
  rows.sort((r1, r2) => {
      const a = parseCellValue(r1.cells[colIndex]?.innerText || '');
      const b = parseCellValue(r2.cells[colIndex]?.innerText || '');

      if (a.type !== b.type) return a.type - b.type;

      let cmp = 0;
      if (a.value < b.value) cmp = -1;
      else if (a.value > b.value) cmp = 1;

      return asc ? cmp : -cmp;
  });

  rows.forEach(r => tbody.appendChild(r));
  table.dataset.sortCol = String(colIndex);
  table.dataset.sortDir = asc ? 'asc' : 'desc';

  const indicators = table.querySelectorAll('.sort-indicator');
  indicators.forEach(ind => ind.textContent = '');

  const th = table.querySelectorAll('th')[colIndex];
  if (th) {
      const ind = th.querySelector('.sort-indicator');
      if (ind) ind.textContent = asc ? ' ▲' : ' ▼';
  }
}