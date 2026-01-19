/**
 * Run Telemetry Charts
 * Uses ApexCharts for single-run visualization
 */

(function () {
  // Chart instances
  let charts = {
    stepDurations: null,
    stepMemory: null,
  };

  // Color palette
  const colors = {
    completed: "#22c55e", // green-500
    failed: "#ef4444", // red-500
    running: "#3b82f6", // blue-500
    skipped: "#9ca3af", // gray-400
    pending: "#d1d5db", // gray-300
  };

  // Common chart options
  const commonOptions = {
    chart: {
      toolbar: { show: false },
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
    },
    stroke: { curve: "smooth" },
    tooltip: { theme: "light" },
    grid: {
      borderColor: "#e2e8f0",
      strokeDashArray: 4,
    },
  };

  // Format duration for display
  function formatDuration(seconds) {
    if (seconds == null || isNaN(seconds)) return "-";
    if (seconds < 0.001) return `${(seconds * 1000000).toFixed(0)}us`;
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(2)}s`;
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}m ${secs.toFixed(0)}s`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  }

  // Format memory for display
  function formatMemory(mb) {
    if (mb == null || isNaN(mb)) return "-";
    if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  }

  // Get color based on step status
  function getStepColor(status) {
    return colors[status] || colors.pending;
  }

  // Render Step Durations Chart (horizontal bar)
  function renderStepDurationsChart(steps) {
    const container = document.getElementById("chart-step-durations");
    if (!container) return;

    const stepsWithDuration = steps.filter(
      (s) => s.duration_s != null && s.duration_s > 0
    );

    if (stepsWithDuration.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No duration data available</p>';
      return;
    }

    const stepColors = stepsWithDuration.map((s) => getStepColor(s.status));

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: Math.max(320, stepsWithDuration.length * 35),
      },
      series: [
        {
          name: "Duration",
          data: stepsWithDuration.map((s) =>
            parseFloat(s.duration_s.toFixed(3))
          ),
        },
      ],
      plotOptions: {
        bar: {
          horizontal: true,
          barHeight: "60%",
          borderRadius: 2,
          distributed: true,
        },
      },
      colors: stepColors,
      xaxis: {
        title: { text: "Duration" },
        labels: { formatter: (val) => formatDuration(val) },
      },
      yaxis: {
        labels: {
          maxWidth: 200,
        },
      },
      labels: stepsWithDuration.map((s) => s.name),
      legend: { show: false },
      dataLabels: {
        enabled: true,
        formatter: (val) => formatDuration(val),
        style: {
          fontSize: "11px",
          colors: ["#374151"],
        },
        offsetX: 5,
      },
      tooltip: {
        y: { formatter: (val) => formatDuration(val) },
      },
    };

    if (charts.stepDurations) {
      charts.stepDurations.destroy();
    }

    charts.stepDurations = new ApexCharts(container, options);
    charts.stepDurations.render();
  }

  // Render Step Memory Chart (horizontal bar)
  function renderStepMemoryChart(steps) {
    const container = document.getElementById("chart-step-memory");
    if (!container) return;

    const stepsWithMemory = steps.filter(
      (s) => s.peak_mem_mb != null && s.peak_mem_mb > 0
    );

    if (stepsWithMemory.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No memory data available</p>';
      return;
    }

    const stepColors = stepsWithMemory.map((s) => getStepColor(s.status));

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: Math.max(320, stepsWithMemory.length * 35),
      },
      series: [
        {
          name: "Peak Memory",
          data: stepsWithMemory.map((s) =>
            parseFloat(s.peak_mem_mb.toFixed(2))
          ),
        },
      ],
      plotOptions: {
        bar: {
          horizontal: true,
          barHeight: "60%",
          borderRadius: 2,
          distributed: true,
        },
      },
      colors: stepColors,
      xaxis: {
        title: { text: "Peak Memory" },
        labels: { formatter: (val) => formatMemory(val) },
      },
      yaxis: {
        labels: {
          maxWidth: 200,
        },
      },
      labels: stepsWithMemory.map((s) => s.name),
      legend: { show: false },
      dataLabels: {
        enabled: true,
        formatter: (val) => formatMemory(val),
        style: {
          fontSize: "11px",
          colors: ["#374151"],
        },
        offsetX: 5,
      },
      tooltip: {
        y: { formatter: (val) => formatMemory(val) },
      },
    };

    if (charts.stepMemory) {
      charts.stepMemory.destroy();
    }

    charts.stepMemory = new ApexCharts(container, options);
    charts.stepMemory.render();
  }

  // Update total memory stat
  function updateTotalMemory(steps) {
    const totalMemoryEl = document.getElementById("total-memory");
    if (!totalMemoryEl) return;

    const totalMemory = steps
      .filter((s) => s.peak_mem_mb != null)
      .reduce((sum, s) => sum + s.peak_mem_mb, 0);

    if (totalMemory > 0) {
      totalMemoryEl.textContent = formatMemory(totalMemory);
    }
  }

  // Initialize
  function init() {
    if (typeof stepsData === "undefined" || !Array.isArray(stepsData)) {
      console.warn("No steps data available");
      return;
    }

    renderStepDurationsChart(stepsData);
    renderStepMemoryChart(stepsData);
    updateTotalMemory(stepsData);
  }

  // Run on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
