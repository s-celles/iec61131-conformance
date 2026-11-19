// Tooltips and a crosshair for the inline SVG charts of the History page.
// Each point (g.viz-pt) is focusable and carries an aria-label; hovering or
// focusing it shows that label in a tooltip and a vertical guide line.
document.addEventListener("DOMContentLoaded", () => {
  const tip = document.createElement("div");
  tip.className = "viz-tooltip";
  tip.setAttribute("role", "status");
  tip.hidden = true;
  document.body.appendChild(tip);

  document.querySelectorAll("svg.viz-chart").forEach((svg) => {
    const ns = "http://www.w3.org/2000/svg";
    const guide = document.createElementNS(ns, "line");
    guide.setAttribute("class", "viz-guide");
    guide.style.display = "none";
    svg.insertBefore(guide, svg.firstChild);
    const grid = svg.querySelectorAll(".viz-grid");
    const top = grid.length ? grid[grid.length - 1].getAttribute("y1") : 0;
    const bottom = grid.length ? grid[0].getAttribute("y1") : 0;

    const show = (pt) => {
      const dot = pt.querySelector(".viz-dot");
      const x = dot.getAttribute("cx");
      guide.setAttribute("x1", x); guide.setAttribute("x2", x);
      guide.setAttribute("y1", top); guide.setAttribute("y2", bottom);
      guide.style.display = "";
      tip.textContent = pt.getAttribute("aria-label");
      tip.hidden = false;
      const r = dot.getBoundingClientRect();
      tip.style.left = `${window.scrollX + r.left + r.width / 2}px`;
      tip.style.top = `${window.scrollY + r.top - 8}px`;
    };
    const hide = () => { guide.style.display = "none"; tip.hidden = true; };

    svg.querySelectorAll("g.viz-pt").forEach((pt) => {
      const title = pt.querySelector("title");
      if (title) title.remove();             // the custom tooltip replaces the native one
      pt.addEventListener("mouseenter", () => show(pt));
      pt.addEventListener("focus", () => show(pt));
      pt.addEventListener("mouseleave", hide);
      pt.addEventListener("blur", hide);
      pt.addEventListener("keydown", (e) => { if (e.key === "Escape") { hide(); pt.blur(); } });
    });
  });
});
