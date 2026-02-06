/**
 * Layout algorithms for pipetree visualization
 */

import { NODE_H, H_GAP, V_GAP, BRANCH_GAP } from "./constants.js";
import { textWidth, stepRan, branchHasActivity } from "./utils.js";

/**
 * Layout nodes horizontally
 */
export function layoutHorizontal(mainSteps, branchesByParent, nodes, links, margin) {
  let x = margin;
  const centerY = margin + 100;

  // Find router index
  let routerIndex = -1;
  mainSteps.forEach((step, i) => {
    if (branchesByParent[step.name]) {
      routerIndex = i;
    }
  });

  // Handle linear pipelines (no branches)
  if (routerIndex === -1) {
    mainSteps.forEach((step, i) => {
      const w = textWidth(step.name, step.duration_s, false);
      nodes.push({ ...step, x, y: centerY - NODE_H / 2, w, h: NODE_H, isRouter: false });
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
    return {
      maxWidth: x + margin,
      maxHeight: centerY + NODE_H + margin,
    };
  }

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
    const branchY = centerY + (bi - (branchNames.length - 1) / 2) * (NODE_H + BRANCH_GAP);

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
          const nestedY = branchY + (ni - (nestedNames.length - 1) / 2) * (NODE_H + 24);

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
    const finalRan = finalStep.status === "completed" || finalStep.status === "running";
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
    maxHeight: centerY + (branchNames.length / 2) * (NODE_H + BRANCH_GAP) + NODE_H + margin,
  };
}

/**
 * Layout nodes vertically
 */
export function layoutVertical(mainSteps, branchesByParent, nodes, links, margin) {
  let y = margin;
  let maxWidth = 0;

  // Find router
  let routerIndex = -1;
  mainSteps.forEach((step, i) => {
    if (branchesByParent[step.name]) {
      routerIndex = i;
    }
  });

  // Handle linear pipelines (no branches)
  if (routerIndex === -1) {
    const centerX = margin + 150;
    mainSteps.forEach((step, i) => {
      const w = textWidth(step.name, step.duration_s, false);
      nodes.push({ ...step, x: centerX - w / 2, y, w, h: NODE_H, isRouter: false });
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
      maxWidth = Math.max(maxWidth, centerX + w / 2 + margin);
      y += NODE_H + V_GAP;
    });
    return { maxWidth, maxHeight: y + margin, centerX };
  }

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
        maxNestedWidth = Math.max(maxNestedWidth, (nestedNames.length - 1) * 240);
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
    const finalRan = finalStep.status === "completed" || finalStep.status === "running";
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
