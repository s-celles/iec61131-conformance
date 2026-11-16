// Filter, sort and page the tables inside <div class="filterable">.
// Adapted from s-celles/julia-findings (MIT), docs/src/assets/interactive-tables.js.
document.addEventListener("DOMContentLoaded", () => {
  const collator = new Intl.Collator(undefined, {
    numeric: true,
    sensitivity: "base",
  });

  document.querySelectorAll(".filterable table").forEach((table, tableIndex) => {
    const body = table.tBodies[0];
    const headerRow = table.tHead?.rows[0] ?? table.rows[0];
    const headers = Array.from(headerRow?.cells ?? []);
    if (!body || !headerRow || headers.length === 0 || table.rows.length < 3) return;

    const rows = Array.from(table.rows).filter((row) => row !== headerRow);
    rows.forEach((row, index) => (row.dataset.originalIndex = String(index)));
    table.classList.add("interactive-table");
    table.id ||= `interactive-table-${tableIndex + 1}`;

    const pageSize = 50;
    let page = 0;
    let filteredRows = rows.slice();

    const tools = document.createElement("div");
    tools.className = "table-tools";

    const input = document.createElement("input");
    input.className = "table-filter";
    input.type = "search";
    input.placeholder = "Filter this table…";
    input.setAttribute("aria-label", "Filter table rows");
    input.setAttribute("aria-controls", table.id);

    const count = document.createElement("span");
    count.className = "table-count";
    count.setAttribute("aria-live", "polite");

    const pagination = document.createElement("div");
    pagination.className = "table-pagination";

    const previous = document.createElement("button");
    previous.type = "button";
    previous.textContent = "← Previous";
    previous.setAttribute("aria-controls", table.id);

    const pageLabel = document.createElement("span");
    pageLabel.className = "table-page";
    pageLabel.setAttribute("aria-live", "polite");

    const next = document.createElement("button");
    next.type = "button";
    next.textContent = "Next →";
    next.setAttribute("aria-controls", table.id);

    pagination.append(previous, pageLabel, next);

    const render = () => {
      const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
      page = Math.min(page, pageCount - 1);
      const start = page * pageSize;
      const end = Math.min(start + pageSize, filteredRows.length);
      const visibleRows = new Set(filteredRows.slice(start, end));

      rows.forEach((row) => (row.hidden = !visibleRows.has(row)));
      count.textContent = filteredRows.length === 0
        ? `0 of ${rows.length} rows`
        : `${start + 1}–${end} of ${filteredRows.length} rows${
            filteredRows.length === rows.length ? "" : ` (${rows.length} total)`
          }`;
      pageLabel.textContent = `Page ${page + 1} of ${pageCount}`;
      previous.disabled = page === 0;
      next.disabled = page + 1 >= pageCount;
      pagination.hidden = filteredRows.length <= pageSize;
    };

    const applyFilter = () => {
      const terms = input.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
      filteredRows = rows.filter((row) => {
        const haystack = row.textContent.toLocaleLowerCase();
        return terms.every((term) => haystack.includes(term));
      });
      page = 0;
      render();
    };

    input.addEventListener("input", applyFilter);
    previous.addEventListener("click", () => {
      page -= 1;
      render();
    });
    next.addEventListener("click", () => {
      page += 1;
      render();
    });

    const summary = document.createElement("div");
    summary.className = "table-summary";
    summary.append(count, pagination);
    tools.append(input, summary);
    table.parentElement.insertBefore(tools, table);
    render();

    headers.forEach((header, columnIndex) => {
      header.tabIndex = 0;
      header.setAttribute("role", "button");
      header.setAttribute("aria-sort", "none");

      const sort = () => {
        const descending = header.getAttribute("aria-sort") === "ascending";
        headers.forEach((item) => item.setAttribute("aria-sort", "none"));
        header.setAttribute("aria-sort", descending ? "descending" : "ascending");

        rows.sort((left, right) => {
          const a = left.cells[columnIndex]?.textContent.trim() ?? "";
          const b = right.cells[columnIndex]?.textContent.trim() ?? "";
          const compared = collator.compare(a, b);
          if (compared !== 0) return descending ? -compared : compared;
          return Number(left.dataset.originalIndex) - Number(right.dataset.originalIndex);
        });
        rows.forEach((row) => body.appendChild(row));
        applyFilter();
      };

      header.addEventListener("click", sort);
      header.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          sort();
        }
      });
    });

    input.id = `table-filter-${tableIndex + 1}`;
  });
});
