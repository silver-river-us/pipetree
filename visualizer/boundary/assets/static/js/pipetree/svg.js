/**
 * SVG rendering helpers for pipetree visualization
 */

import { ICON_COLORS } from "./constants.js";
import { truncateName, formatDuration } from "./utils.js";

/**
 * Create an SVG element with attributes
 */
export function createSvgElement(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    el.setAttribute(key, value);
  }
  return el;
}

/**
 * Draw a status icon for a node
 */
export function drawStatusIcon(g, node, iconX, iconY, iconSize) {
  const iconG = createSvgElement("g");
  const iconColor = ICON_COLORS[node.status] || ICON_COLORS.pending;

  if (node.isRouter) {
    // Router: filled diamond shape (purple)
    const cx = iconX + iconSize / 2;
    const cy = iconY + iconSize / 2;
    const r = iconSize / 2;
    const diamond = createSvgElement("path", {
      d: `M${cx},${cy - r} L${cx + r},${cy} L${cx},${cy + r} L${cx - r},${cy} Z`,
      fill: "#8250df",
      stroke: "#8250df",
      "stroke-width": "2",
    });
    iconG.appendChild(diamond);
  } else if (node.status === "completed") {
    // Green circle with white checkmark
    const circle = createSvgElement("circle", {
      cx: iconX + iconSize / 2,
      cy: iconY + iconSize / 2,
      r: iconSize / 2,
      fill: iconColor,
    });
    iconG.appendChild(circle);

    const check = createSvgElement("path", {
      d: `M${iconX + 4},${iconY + 8} l3,3 l5,-6`,
      fill: "none",
      stroke: "white",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    });
    iconG.appendChild(check);
  } else if (node.status === "running") {
    // Blue spinning circle
    const cx = iconX + iconSize / 2;
    const cy = iconY + iconSize / 2;
    const spinnerG = createSvgElement("g", {
      class: "spinner",
      style: `transform-origin: ${cx}px ${cy}px`,
    });

    const circle = createSvgElement("circle", {
      cx: cx,
      cy: cy,
      r: iconSize / 2 - 1,
      fill: "none",
      stroke: iconColor,
      "stroke-width": "2.5",
      "stroke-dasharray": "12 8",
      "stroke-linecap": "round",
    });
    spinnerG.appendChild(circle);
    iconG.appendChild(spinnerG);
  } else if (node.status === "failed") {
    // Red circle with X
    const circle = createSvgElement("circle", {
      cx: iconX + iconSize / 2,
      cy: iconY + iconSize / 2,
      r: iconSize / 2,
      fill: iconColor,
    });
    iconG.appendChild(circle);

    const x = createSvgElement("path", {
      d: `M${iconX + 5},${iconY + 5} l6,6 M${iconX + 11},${iconY + 5} l-6,6`,
      stroke: "white",
      "stroke-width": "2",
      "stroke-linecap": "round",
    });
    iconG.appendChild(x);
  } else {
    // Gray outline circle for pending/skipped
    const circle = createSvgElement("circle", {
      cx: iconX + iconSize / 2,
      cy: iconY + iconSize / 2,
      r: iconSize / 2 - 1,
      fill: "none",
      stroke: iconColor,
      "stroke-width": "1.5",
    });
    iconG.appendChild(circle);
  }

  g.appendChild(iconG);
}

/**
 * Draw a single node
 */
export function drawNode(svg, node, onNodeClick) {
  if (node.type === "label") {
    const txt = createSvgElement("text", {
      x: node.x,
      y: node.y + 12,
      class: "branch-text" + (node.active ? " active" : ""),
    });
    if (node.align === "middle") {
      txt.setAttribute("text-anchor", "middle");
    }
    txt.textContent = node.name.toUpperCase();
    svg.appendChild(txt);
    return;
  }

  const g = createSvgElement("g", { class: "node-group" });
  g.onclick = () => onNodeClick(node.step_index);

  // White rect with gray border
  const rect = createSvgElement("rect", {
    x: node.x,
    y: node.y,
    width: node.w,
    height: node.h,
    class: "node-rect" + (node.isRouter ? " router" : ""),
  });
  g.appendChild(rect);

  // Status icon
  const iconSize = 16;
  const iconX = node.x + 12;
  const iconY = node.y + (node.h - iconSize) / 2;
  drawStatusIcon(g, node, iconX, iconY, iconSize);

  // Name (truncate if needed)
  const hasDuration = node.duration_s != null && !node.isRouter;
  const availableWidth = node.w - 36 - (hasDuration ? 55 : 10);
  const maxChars = Math.floor(availableWidth / 7.5);
  const displayName = truncateName(node.name, maxChars);

  const nameText = createSvgElement("text", {
    x: node.x + 36,
    y: node.y + node.h / 2 + 4,
    class: "node-text",
  });
  nameText.textContent = displayName;

  // Add tooltip if truncated
  if (node.name.length > maxChars) {
    const title = createSvgElement("title");
    title.textContent = node.name;
    nameText.appendChild(title);
  }
  g.appendChild(nameText);

  // Duration
  if (hasDuration) {
    const dur = createSvgElement("text", {
      x: node.x + node.w - 10,
      y: node.y + node.h / 2 + 4,
      "text-anchor": "end",
      class: "node-duration",
    });
    dur.textContent = formatDuration(node.duration_s);
    g.appendChild(dur);
  }

  svg.appendChild(g);
}

/**
 * Draw a link/path between nodes
 */
export function drawLink(svg, link) {
  const path = createSvgElement("path");
  let d;

  if (link.type === "h") {
    if (link.y1 === link.y2) {
      d = `M${link.x1},${link.y1} L${link.x2},${link.y2}`;
    } else {
      const midX = (link.x1 + link.x2) / 2;
      d = `M${link.x1},${link.y1} L${midX},${link.y1} L${midX},${link.y2} L${link.x2},${link.y2}`;
    }
  } else if (link.type === "v") {
    if (link.x1 === link.x2) {
      d = `M${link.x1},${link.y1} L${link.x2},${link.y2}`;
    } else {
      const midY = (link.y1 + link.y2) / 2;
      d = `M${link.x1},${link.y1} L${link.x1},${midY} L${link.x2},${midY} L${link.x2},${link.y2}`;
    }
  } else if (link.type === "L") {
    d = `M${link.x1},${link.y1} L${link.x2},${link.y2} L${link.x3},${link.y3}`;
  }

  path.setAttribute("d", d);
  let linkClass = "link";
  if (link.isRouter) {
    linkClass += " router";
  } else if (link.active) {
    linkClass += " active";
  }
  path.setAttribute("class", linkClass);
  svg.appendChild(path);
}
