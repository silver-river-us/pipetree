/**
 * Utility functions for pipetree visualization
 */

import { MAX_NODE_WIDTH, MIN_NODE_WIDTH } from "./constants.js";

/**
 * Calculate node width based on content
 */
export function textWidth(name, durationS, isRouter) {
  const nameWidth = name.length * 7.5;
  const durationWidth = durationS != null && !isRouter ? 50 : 0;
  const padding = 50;
  const calculated = nameWidth + durationWidth + padding;
  return Math.min(MAX_NODE_WIDTH, Math.max(MIN_NODE_WIDTH, calculated));
}

/**
 * Truncate name with ellipsis
 */
export function truncateName(name, maxChars) {
  if (name.length <= maxChars) return name;
  return name.substring(0, maxChars - 1) + "…";
}

/**
 * Check if a step has run
 */
export function stepRan(step) {
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
export function branchHasActivity(steps, branchesMap) {
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
export function formatDuration(seconds) {
  if (seconds < 1) {
    return Math.round(seconds * 1000) + "ms";
  }
  return seconds.toFixed(1) + "s";
}
