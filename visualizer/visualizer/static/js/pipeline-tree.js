/**
 * Pipeline Tree Visualization Library
 *
 * Renders pipeline steps as an interactive SVG tree diagram.
 * Supports horizontal and vertical layouts with branching.
 */

(function (global) {
  "use strict";

  // Constants
  const NODE_H = 36;
  const H_GAP = 24;
  const V_GAP = 48;
  const BRANCH_GAP = 60;
  const MAX_NODE_WIDTH = 220;
  const MIN_NODE_WIDTH = 100;

  // Icon colors by status
  const ICON_COLORS = {
    completed: "#1a7f37",
    running: "#0969da",
    failed: "#cf222e",
    skipped: "#8c959f",
    pending: "#8c959f",
  };

  /**
   * Calculate node width based on content
   */
  function textWidth(name, durationS, isRouter) {
    const nameWidth = name.length * 7.5;
    const durationWidth = durationS != null && !isRouter ? 50 : 0;
    const padding = 50;
    const calculated = nameWidth + durationWidth + padding;
    return Math.min(MAX_NODE_WIDTH, Math.max(MIN_NODE_WIDTH, calculated));
  }

  /**
   * Truncate name with ellipsis
   */
  function truncateName(name, maxChars) {
    if (name.length <= maxChars) return name;
    return name.substring(0, maxChars - 1) + "…";
  }

  /**
   * Check if a step has run
   */
  function stepRan(step) {
    return (
      step &&
      (step.status === "completed" ||
        step.status === "running" ||
        step.status === "failed")
    );
  }

  /**
   * Check if any steps in a branch have activity
   */
  function branchHasActivity(steps, branchesMap) {
    if (!Array.isArray(steps) || steps.length === 0) return false;
    for (const step of steps) {
      if (stepRan(step)) return true;
      const nested = branchesMap[step.name];
      if (nested) {
        for (const nestedSteps of Object.values(nested)) {
          if (branchHasActivity(nestedSteps, branchesMap)) return true;
        }
      }
    }
    return false;
  }

  /**
   * Format duration for display
   */
  function formatDuration(seconds) {
    if (seconds < 1) {
      return Math.round(seconds * 1000) + "ms";
    }
    return seconds.toFixed(1) + "s";
  }

  /**
   * Create an SVG element
   */
  function createSvgElement(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      el.setAttribute(key, value);
    }
    return el;
  }

  /**
   * Draw a status icon for a node
   */
  function drawStatusIcon(g, node, iconX, iconY, iconSize) {
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
  function drawNode(svg, node, onNodeClick) {
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
  function drawLink(svg, link) {
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

  /**
   * Layout nodes horizontally
   */
  function layoutHorizontal(
    mainSteps,
    branchesByParent,
    nodes,
    links,
    margin
  ) {
    let x = margin;
    const centerY = margin + 100;

    // Find router index
    let routerIndex = -1;
    mainSteps.forEach((step, i) => {
      if (branchesByParent[step.name]) {
        routerIndex = i;
      }
    });

    const preRouterSteps = mainSteps.slice(0, routerIndex + 1);
    const postRouterSteps = mainSteps.slice(routerIndex + 1);

    // Pre-router steps
    preRouterSteps.forEach((step, i) => {
      const isRouter = step.name.startsWith("route_");
      const w = textWidth(step.name, step.duration_s, isRouter);
      nodes.push({ ...step, x, y: centerY - NODE_H / 2, w, h: NODE_H, isRouter });
      if (i > 0) {
        const prev = nodes[nodes.length - 2];
        links.push({
          type: "h",
          x1: prev.x + prev.w,
          y1: centerY,
          x2: x,
          y2: centerY,
          active: prev.status === "completed",
        });
      }
      x += w + H_GAP;
    });

    // Router branches
    const router = nodes[nodes.length - 1];
    const branches = branchesByParent[router.name] || {};
    const branchNames = Object.keys(branches);

    const branchStartX = router.x + router.w + H_GAP * 2;
    const branchEndPoints = [];
    let maxX = branchStartX;

    branchNames.forEach((bname, bi) => {
      const bsteps = branches[bname];
      const branchRan = branchHasActivity(bsteps, branchesByParent);
      const branchY =
        centerY + (bi - (branchNames.length - 1) / 2) * (NODE_H + BRANCH_GAP);

      nodes.push({
        type: "label",
        name: bname,
        x: branchStartX,
        y: branchY - NODE_H / 2 - 20,
        active: branchRan,
      });

      let bx = branchStartX;

      bsteps.forEach((bstep, si) => {
        const isRouter = bstep.name.startsWith("route_");
        const bw = textWidth(bstep.name, bstep.duration_s, isRouter);
        const bnode = {
          ...bstep,
          x: bx,
          y: branchY - NODE_H / 2,
          w: bw,
          h: NODE_H,
          isRouter,
        };
        nodes.push(bnode);

        if (si === 0) {
          const isRouterLink = router.isRouter && branchRan;
          links.push({
            type: "h",
            x1: router.x + router.w,
            y1: centerY,
            x2: bx,
            y2: branchY,
            active: stepRan(router) && branchRan,
            isRouter: isRouterLink,
          });
        }

        // Handle nested branches
        const nested = branchesByParent[bstep.name];
        if (nested) {
          const nestedNames = Object.keys(nested);
          const nestedStartX = bx + bw + H_GAP * 2;

          nestedNames.forEach((nname, ni) => {
            const nsteps = nested[nname];
            const nestedRan = branchHasActivity(nsteps, branchesByParent);
            const nestedY =
              branchY + (ni - (nestedNames.length - 1) / 2) * (NODE_H + 24);

            nodes.push({
              type: "label",
              name: nname,
              x: nestedStartX,
              y: nestedY - NODE_H / 2 - 20,
              active: nestedRan,
            });

            let nx = nestedStartX;
            nsteps.forEach((nstep) => {
              const nw = textWidth(nstep.name, nstep.duration_s, false);
              const nnode = {
                ...nstep,
                x: nx,
                y: nestedY - NODE_H / 2,
                w: nw,
                h: NODE_H,
              };
              nodes.push(nnode);
              const isRouterLink = bnode.isRouter && nestedRan;
              links.push({
                type: "h",
                x1: bx + bw,
                y1: branchY,
                x2: nx,
                y2: nestedY,
                active: bnode.status === "completed" && nestedRan,
                isRouter: isRouterLink,
              });
              branchEndPoints.push({
                x: nx + nw,
                y: nestedY,
                center: nestedY,
                active: nstep.status === "completed",
              });
              maxX = Math.max(maxX, nx + nw);
              nx += nw + H_GAP;
            });
          });
        } else {
          branchEndPoints.push({
            x: bx + bw,
            y: branchY,
            center: branchY,
            active: bstep.status === "completed",
          });
          maxX = Math.max(maxX, bx + bw);
        }

        bx += bw + H_GAP;
      });
    });

    // Convergence point
    const convergeX = maxX + H_GAP * 2;
    const minCenter = Math.min(...branchEndPoints.map((p) => p.center));
    const maxCenter = Math.max(...branchEndPoints.map((p) => p.center));
    const convergeY = (minCenter + maxCenter) / 2;

    branchEndPoints.forEach((pt) => {
      links.push({
        type: "L",
        x1: pt.x,
        y1: pt.y,
        x2: convergeX,
        y2: pt.y,
        x3: convergeX,
        y3: convergeY,
        active: pt.active,
      });
    });

    // Final step
    if (postRouterSteps.length > 0) {
      const finalStep = postRouterSteps[0];
      const fw = textWidth(finalStep.name, finalStep.duration_s, false);
      const finalX = convergeX + H_GAP;
      const finalRan =
        finalStep.status === "completed" || finalStep.status === "running";
      nodes.push({
        ...finalStep,
        x: finalX,
        y: convergeY - NODE_H / 2,
        w: fw,
        h: NODE_H,
      });
      links.push({
        type: "h",
        x1: convergeX,
        y1: convergeY,
        x2: finalX,
        y2: convergeY,
        active: finalRan,
      });
      maxX = finalX + fw;
    }

    return {
      maxWidth: maxX + margin,
      maxHeight:
        centerY +
        (branchNames.length / 2) * (NODE_H + BRANCH_GAP) +
        NODE_H +
        margin,
    };
  }

  /**
   * Layout nodes vertically
   */
  function layoutVertical(mainSteps, branchesByParent, nodes, links, margin) {
    let y = margin;
    let maxWidth = 0;

    // Find router
    let routerIndex = -1;
    mainSteps.forEach((step, i) => {
      if (branchesByParent[step.name]) {
        routerIndex = i;
      }
    });

    const preRouterSteps = mainSteps.slice(0, routerIndex + 1);
    const postRouterSteps = mainSteps.slice(routerIndex + 1);

    const router_step = preRouterSteps[preRouterSteps.length - 1];
    const branches = branchesByParent[router_step?.name] || {};
    const branchNames = Object.keys(branches);

    // Calculate max nested width
    let maxNestedWidth = 0;
    branchNames.forEach((bname) => {
      const bsteps = branches[bname];
      bsteps.forEach((bstep) => {
        const nested = branchesByParent[bstep.name];
        if (nested) {
          const nestedNames = Object.keys(nested);
          maxNestedWidth = Math.max(
            maxNestedWidth,
            (nestedNames.length - 1) * 240
          );
        }
      });
    });

    const branchSpacing = Math.max(200, maxNestedWidth + 50);
    const totalBranchWidth = (branchNames.length - 1) * branchSpacing;
    const centerX = margin + Math.max(150, totalBranchWidth / 2 + 120);

    // Pre-router steps
    preRouterSteps.forEach((step, i) => {
      const isRouter = step.name.startsWith("route_");
      const w = textWidth(step.name, step.duration_s, isRouter);
      nodes.push({
        ...step,
        x: centerX - w / 2,
        y,
        w,
        h: NODE_H,
        isRouter,
      });
      if (i > 0) {
        const prev = nodes[nodes.length - 2];
        links.push({
          type: "v",
          x1: centerX,
          y1: prev.y + NODE_H,
          x2: centerX,
          y2: y,
          active: prev.status === "completed",
        });
      }
      y += NODE_H + V_GAP;
      maxWidth = Math.max(maxWidth, centerX + w / 2 + margin);
    });

    // Router and branches
    const router = nodes[nodes.length - 1];
    const branchEndPoints = [];
    let maxBranchY = y;

    const branchStartX = centerX - totalBranchWidth / 2;

    branchNames.forEach((bname, bi) => {
      const bsteps = branches[bname];
      const branchRan = branchHasActivity(bsteps, branchesByParent);
      const branchX = branchStartX + bi * branchSpacing;

      nodes.push({
        type: "label",
        name: bname,
        x: branchX,
        y: y - 22,
        active: branchRan,
        align: "middle",
      });

      let by = y;

      bsteps.forEach((bstep, si) => {
        const isRouter = bstep.name.startsWith("route_");
        const bw = textWidth(bstep.name, bstep.duration_s, isRouter);
        const bnode = {
          ...bstep,
          x: branchX - bw / 2,
          y: by,
          w: bw,
          h: NODE_H,
          isRouter,
        };
        nodes.push(bnode);

        if (si === 0) {
          const isRouterLink = router.isRouter && branchRan;
          links.push({
            type: "v",
            x1: centerX,
            y1: router.y + NODE_H,
            x2: branchX,
            y2: by,
            active: stepRan(router) && branchRan,
            isRouter: isRouterLink,
          });
        }

        // Handle nested branches
        const nested = branchesByParent[bstep.name];
        if (nested) {
          const nestedNames = Object.keys(nested);
          const nestedSpacing = 240;
          const nestedTotalWidth = (nestedNames.length - 1) * nestedSpacing;
          const nestedStartX = branchX - nestedTotalWidth / 2;
          let nestedY = by + NODE_H + V_GAP;

          nestedNames.forEach((nname, ni) => {
            const nsteps = nested[nname];
            const nestedRan = branchHasActivity(nsteps, branchesByParent);
            const nestedX = nestedStartX + ni * nestedSpacing;

            nodes.push({
              type: "label",
              name: nname,
              x: nestedX,
              y: nestedY - 22,
              active: nestedRan,
              align: "middle",
            });

            let ny = nestedY;
            nsteps.forEach((nstep) => {
              const nw = textWidth(nstep.name, nstep.duration_s, false);
              const nnode = {
                ...nstep,
                x: nestedX - nw / 2,
                y: ny,
                w: nw,
                h: NODE_H,
              };
              nodes.push(nnode);
              const isRouterLink = bnode.isRouter && nestedRan;
              links.push({
                type: "v",
                x1: branchX,
                y1: bnode.y + NODE_H,
                x2: nestedX,
                y2: ny,
                active: bnode.status === "completed" && nestedRan,
                isRouter: isRouterLink,
              });
              branchEndPoints.push({
                x: nestedX,
                y: ny + NODE_H,
                active: nstep.status === "completed",
              });
              maxBranchY = Math.max(maxBranchY, ny + NODE_H);
              maxWidth = Math.max(maxWidth, nestedX + nw / 2 + margin);
              ny += NODE_H + V_GAP;
            });
          });
          by = nestedY + NODE_H;
        } else {
          branchEndPoints.push({
            x: branchX,
            y: by + NODE_H,
            active: bstep.status === "completed",
          });
          maxBranchY = Math.max(maxBranchY, by + NODE_H);
        }

        maxWidth = Math.max(maxWidth, branchX + bw / 2 + margin);
        by += NODE_H + V_GAP;
      });
    });

    // Convergence and final step
    const convergeY = maxBranchY + V_GAP / 2;

    branchEndPoints.forEach((pt) => {
      links.push({
        type: "L",
        x1: pt.x,
        y1: pt.y,
        x2: pt.x,
        y2: convergeY,
        x3: centerX,
        y3: convergeY,
        active: pt.active,
      });
    });

    if (postRouterSteps.length > 0) {
      const finalStep = postRouterSteps[0];
      const fw = textWidth(finalStep.name, finalStep.duration_s, false);
      const finalY = convergeY + V_GAP / 2;
      const finalRan =
        finalStep.status === "completed" || finalStep.status === "running";
      nodes.push({
        ...finalStep,
        x: centerX - fw / 2,
        y: finalY,
        w: fw,
        h: NODE_H,
      });
      links.push({
        type: "v",
        x1: centerX,
        y1: convergeY,
        x2: centerX,
        y2: finalY,
        active: finalRan,
      });
      y = finalY + NODE_H + margin;
    } else {
      y = convergeY + margin;
    }

    maxWidth = Math.max(maxWidth, centerX + margin);

    return { maxWidth, maxHeight: y + margin, centerX };
  }

  /**
   * PipelineTree class
   */
  class PipelineTree {
    constructor(options) {
      this.svgSelector = options.svgSelector || "#tree-svg";
      this.dataSelector = options.dataSelector || "#steps-data";
      this.containerSelector = options.containerSelector || ".tree-container";
      this.onNodeClick = options.onNodeClick || function () {};
      this.layout = localStorage.getItem("pipelineLayout") || "vertical";
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
      localStorage.setItem("pipelineLayout", layout);
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
        bounds = layoutHorizontal(
          mainSteps,
          branchesByParent,
          nodes,
          links,
          margin
        );
      } else {
        bounds = layoutVertical(
          mainSteps,
          branchesByParent,
          nodes,
          links,
          margin
        );
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

  // Export to global
  global.PipelineTree = PipelineTree;
})(typeof window !== "undefined" ? window : this);
