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
    // Track the last active step index for auto-scrolling
    this.lastActiveStepIndex = -1;
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
   * Find the active step (running) or last completed/failed step
   */
  findActiveStepIndex(nodes) {
    let activeIndex = -1;
    let lastCompletedIndex = -1;

    for (const node of nodes) {
      if (node.type === "label") continue;
      if (node.status === "running") {
        activeIndex = node.step_index;
        break; // Running step takes priority
      }
      if (node.status === "completed" || node.status === "failed") {
        lastCompletedIndex = node.step_index;
      }
    }

    return activeIndex !== -1 ? activeIndex : lastCompletedIndex;
  }

  /**
   * Scroll a node into view within the container
   */
  scrollNodeIntoView(container, node) {
    if (!container || !node) return;

    const isH = this.layout === "horizontal";

    if (isH) {
      // Horizontal: scroll so node is visible with some padding
      const nodeRight = node.x + node.w;
      const viewLeft = container.scrollLeft;
      const viewRight = viewLeft + container.clientWidth;

      if (nodeRight > viewRight - 50) {
        // Node is off the right edge, scroll to show it
        container.scrollLeft = nodeRight - container.clientWidth + 100;
      } else if (node.x < viewLeft + 50) {
        // Node is off the left edge
        container.scrollLeft = Math.max(0, node.x - 100);
      }
    } else {
      // Vertical: scroll so node is visible
      const nodeBottom = node.y + node.h;
      const viewTop = container.scrollTop;
      const viewBottom = viewTop + container.clientHeight;

      if (nodeBottom > viewBottom - 50) {
        container.scrollTop = nodeBottom - container.clientHeight + 100;
      } else if (node.y < viewTop + 50) {
        container.scrollTop = Math.max(0, node.y - 100);
      }
    }
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

    // Find and scroll to active step if it changed
    const activeStepIndex = this.findActiveStepIndex(nodes);
    if (activeStepIndex !== -1 && activeStepIndex !== this.lastActiveStepIndex) {
      this.lastActiveStepIndex = activeStepIndex;
      const activeNode = nodes.find(
        (n) => n.type !== "label" && n.step_index === activeStepIndex
      );
      if (activeNode && container) {
        requestAnimationFrame(() => {
          this.scrollNodeIntoView(container, activeNode);
        });
      }
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

    const self = this;

    // Re-render after HTMX updates
    document.body.addEventListener("htmx:afterSwap", function (evt) {
      self.handleUpdate(evt);
    });

    return this;
  }
}
