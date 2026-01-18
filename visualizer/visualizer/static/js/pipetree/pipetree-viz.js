/**
 * PipetreeViz - Main visualization class
 */

import { layoutHorizontal, layoutVertical } from "./layout.js";
import { drawNode, drawLink } from "./svg.js";

export class PipetreeViz {
  constructor(options) {
    this.svgSelector = options.svgSelector || "#tree-svg";
    this.dataSelector = options.dataSelector || "#steps-data";
    this.containerSelector = options.containerSelector || ".tree-container";
    this.onNodeClick = options.onNodeClick || function () {};
    this.layout = localStorage.getItem("pipetreeLayout") || "vertical";
    this.data = null;
  }

  /**
   * Read data from the DOM
   */
  readData() {
    const el = document.querySelector(this.dataSelector);
    if (!el) return null;
    return {
      mainSteps: JSON.parse(el.dataset.mainSteps || "[]"),
      branchesByParent: JSON.parse(el.dataset.branchesByParent || "{}"),
      runId: el.dataset.runId || "",
      dbPath: el.dataset.dbPath || "",
    };
  }

  /**
   * Set layout mode
   */
  setLayout(layout) {
    this.layout = layout;
    localStorage.setItem("pipetreeLayout", layout);
    this.render();
  }

  /**
   * Render the tree
   */
  render() {
    this.data = this.readData();
    if (!this.data) return;

    const svg = document.querySelector(this.svgSelector);
    const container = svg ? svg.closest(this.containerSelector) : null;
    if (!svg) return;

    const prevScrollLeft = container ? container.scrollLeft : 0;
    const prevScrollTop = container ? container.scrollTop : 0;
    svg.innerHTML = "";

    const isH = this.layout === "horizontal";
    const nodes = [];
    const links = [];
    const mainSteps = this.data.mainSteps;
    const branchesByParent = this.data.branchesByParent;
    const margin = 40;

    let bounds;
    if (isH) {
      bounds = layoutHorizontal(mainSteps, branchesByParent, nodes, links, margin);
    } else {
      bounds = layoutVertical(mainSteps, branchesByParent, nodes, links, margin);
    }

    // Adjust bounds based on actual node positions
    let minX = margin;
    let maxX = bounds.maxWidth;
    let svgH = bounds.maxHeight;

    nodes.forEach((n) => {
      if (n.type !== "label" && n.x != null) {
        minX = Math.min(minX, n.x);
        maxX = Math.max(maxX, n.x + (n.w || 0));
        svgH = Math.max(svgH, (n.y || 0) + (n.h || 0) + margin);
      }
    });

    // Shift if nodes are to the left of margin
    if (minX < margin) {
      const shiftX = margin - minX + 20;
      nodes.forEach((n) => {
        if (n.x != null) n.x += shiftX;
      });
      links.forEach((l) => {
        if (l.x1 != null) l.x1 += shiftX;
        if (l.x2 != null) l.x2 += shiftX;
        if (l.x3 != null) l.x3 += shiftX;
      });
      maxX += shiftX;
    }

    // Center vertical layout
    if (!isH && container) {
      const viewWidth = container.clientWidth;
      const contentWidth = maxX + margin;
      if (viewWidth > contentWidth) {
        const shiftX = Math.floor((viewWidth - contentWidth) / 2);
        nodes.forEach((n) => {
          if (n.x != null) n.x += shiftX;
        });
        links.forEach((l) => {
          if (l.x1 != null) l.x1 += shiftX;
          if (l.x2 != null) l.x2 += shiftX;
          if (l.x3 != null) l.x3 += shiftX;
        });
        maxX += shiftX;
      }
    }

    const svgW = maxX + margin;
    svg.setAttribute("width", svgW);
    svg.setAttribute("height", svgH);

    // Draw links (sorted so active/router links are on top)
    const sortedLinks = [...links].sort((a, b) => {
      const rank = (l) => (l.isRouter ? 1 : l.active ? 2 : 0);
      return rank(a) - rank(b);
    });
    sortedLinks.forEach((link) => drawLink(svg, link));

    // Draw nodes
    const self = this;
    nodes.forEach((node) => {
      drawNode(svg, node, function (stepIndex) {
        self.onNodeClick(self.data.runId, stepIndex, self.data.dbPath);
      });
    });

    // Restore scroll position
    if (container) {
      container.scrollLeft = prevScrollLeft;
      container.scrollTop = prevScrollTop;
    }
  }

  /**
   * Handle HTMX updates
   */
  handleUpdate(evt) {
    if (evt.target && evt.target.id === "steps-data") {
      this.render();
    }
  }

  /**
   * Initialize the tree
   */
  init() {
    this.render();

    // Listen for HTMX updates
    const self = this;
    document.body.addEventListener("htmx:afterSwap", function (evt) {
      self.handleUpdate(evt);
    });

    return this;
  }
}
