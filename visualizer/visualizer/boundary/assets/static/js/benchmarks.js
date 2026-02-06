/**
 * Benchmark Detail Page Charts
 * Uses ApexCharts for visualization
 */

(function () {
  // Chart instances (for cleanup)
  let charts = {
    time: null,
    memory: null,
    cpu: null,
    cpuPercent: null,
    correctness: null,
    summary: null,
  };

  // Color palette for charts (matches Tailwind)
  const colors = [
    "#3b82f6", // blue-500
    "#22c55e", // green-500
    "#f59e0b", // amber-500
    "#8b5cf6", // violet-500
    "#ef4444", // red-500
    "#06b6d4", // cyan-500
    "#ec4899", // pink-500
    "#14b8a6", // teal-500
    "#f97316", // orange-500
    "#6366f1", // indigo-500
  ];

  // Common chart options
  const commonOptions = {
    chart: {
      toolbar: { show: false },
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
    },
    colors: colors,
    tooltip: { theme: "light" },
    grid: {
      borderColor: "#e2e8f0",
      strokeDashArray: 4,
    },
    states: {
      hover: {
        filter: { type: "lighten", value: 0.1 },
      },
    },
  };

  // Format duration for display
  function formatDuration(seconds) {
    if (seconds == null || isNaN(seconds)) return "-";
    if (seconds < 0.001) return `${(seconds * 1000000).toFixed(0)}us`;
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(3)}s`;
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}m ${secs.toFixed(0)}s`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (secs > 0) return `${hours}h ${mins}m ${secs.toFixed(0)}s`;
    return `${hours}h ${mins}m`;
  }

  // Format memory for display
  function formatMemory(mb) {
    if (mb == null || isNaN(mb)) return "-";
    if (mb < 1) return `${(mb * 1024).toFixed(0)} KB`;
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  }

  // Destroy existing charts
  function destroyCharts() {
    Object.values(charts).forEach((chart) => {
      if (chart) chart.destroy();
    });
    charts = { time: null, memory: null, cpu: null, cpuPercent: null, correctness: null, summary: null };
  }

  // Load comparison data and render charts
  async function loadCharts() {
    if (typeof benchmarkId === "undefined" || typeof dbPath === "undefined") {
      console.error("Missing benchmarkId or dbPath");
      return;
    }

    try {
      const response = await fetch(
        `/api/benchmarks/${benchmarkId}/comparison?db=${encodeURIComponent(dbPath)}`
      );
      const data = await response.json();

      if (data.error) {
        console.error("API error:", data.error);
        return;
      }

      destroyCharts();
      renderTimeChart(data);
      renderMemoryChart(data);
      renderCpuChart(data);
      renderCpuPercentChart(data);
      renderCorrectnessChart(data);
      renderSummaryChart(data);
    } catch (error) {
      console.error("Failed to load benchmark data:", error);
    }
  }

  // Execution Time Chart (Grouped Bar)
  function renderTimeChart(data) {
    const container = document.getElementById("chart-time");
    if (!container) return;

    if (data.fixtures.length === 0 || data.implementations.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No time data available</p>';
      return;
    }

    const series = data.implementations.map((impl) => ({
      name: impl,
      data: data.time_data[impl] || [],
    }));

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
      },
      series: series,
      xaxis: {
        categories: data.fixtures,
        title: { text: "Fixture" },
      },
      yaxis: {
        title: { text: "Time (seconds)" },
        labels: {
          formatter: (val) => formatDuration(val),
        },
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: "70%",
          borderRadius: 2,
        },
      },
      dataLabels: { enabled: false },
      legend: {
        position: "top",
        horizontalAlign: "left",
        fontSize: "11px",
      },
      tooltip: {
        y: { formatter: (val) => formatDuration(val) },
      },
    };

    charts.time = new ApexCharts(container, options);
    charts.time.render();
  }

  // Memory Usage Chart (Grouped Bar)
  function renderMemoryChart(data) {
    const container = document.getElementById("chart-memory");
    if (!container) return;

    if (data.fixtures.length === 0 || data.implementations.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No memory data available</p>';
      return;
    }

    const series = data.implementations.map((impl) => ({
      name: impl,
      data: data.memory_data[impl] || [],
    }));

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
      },
      series: series,
      xaxis: {
        categories: data.fixtures,
        title: { text: "Fixture" },
      },
      yaxis: {
        title: { text: "Peak Memory (MB)" },
        labels: {
          formatter: (val) => formatMemory(val),
        },
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: "70%",
          borderRadius: 2,
        },
      },
      dataLabels: { enabled: false },
      legend: {
        position: "top",
        horizontalAlign: "left",
        fontSize: "11px",
      },
      tooltip: {
        y: { formatter: (val) => formatMemory(val) },
      },
    };

    charts.memory = new ApexCharts(container, options);
    charts.memory.render();
  }

  // CPU Time Chart (Grouped Bar)
  function renderCpuChart(data) {
    const container = document.getElementById("chart-cpu");
    if (!container) return;

    if (data.fixtures.length === 0 || data.implementations.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No CPU time data available</p>';
      return;
    }

    // Check if any CPU data exists
    const hasCpuData = data.implementations.some((impl) =>
      (data.cpu_data[impl] || []).some((v) => v > 0)
    );

    if (!hasCpuData) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No CPU time data available</p>';
      return;
    }

    const series = data.implementations.map((impl) => ({
      name: impl,
      data: data.cpu_data[impl] || [],
    }));

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
      },
      series: series,
      xaxis: {
        categories: data.fixtures,
        title: { text: "Fixture" },
      },
      yaxis: {
        title: { text: "CPU Time (seconds)" },
        labels: {
          formatter: (val) => formatDuration(val),
        },
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: "70%",
          borderRadius: 2,
        },
      },
      dataLabels: { enabled: false },
      legend: {
        position: "top",
        horizontalAlign: "left",
        fontSize: "11px",
      },
      tooltip: {
        y: { formatter: (val) => formatDuration(val) },
      },
    };

    charts.cpu = new ApexCharts(container, options);
    charts.cpu.render();
  }

  // CPU Utilization % Chart (Grouped Bar) - normalized by CPU count
  function renderCpuPercentChart(data) {
    const container = document.getElementById("chart-cpu-percent");
    if (!container) return;

    if (data.fixtures.length === 0 || data.implementations.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No CPU utilization data available</p>';
      return;
    }

    // Calculate CPU % for each fixture/implementation (raw, not normalized)
    // 100% = 1 full core, <100% = I/O bound, >100% = multi-core parallel
    const series = data.implementations.map((impl) => {
      const cpuTimes = data.cpu_data[impl] || [];
      const wallTimes = data.time_data[impl] || [];
      const cpuPercents = cpuTimes.map((cpu, i) => {
        const wall = wallTimes[i] || 0;
        if (cpu > 0 && wall > 0) {
          const pct = (cpu / wall) * 100;
          return parseFloat(pct < 1 ? pct.toFixed(2) : pct.toFixed(1));
        }
        return 0;
      });
      return {
        name: impl,
        data: cpuPercents,
      };
    });

    // Check if any CPU % data exists
    const hasCpuData = series.some((s) => s.data.some((v) => v > 0));

    if (!hasCpuData) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No CPU utilization data available</p>';
      return;
    }

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
      },
      series: series,
      xaxis: {
        categories: data.fixtures,
        title: { text: "Fixture" },
      },
      yaxis: {
        title: { text: "CPU % (100% = 1 core)" },
        labels: {
          formatter: (val) => val < 1 ? `${val.toFixed(2)}%` : `${val.toFixed(1)}%`,
        },
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: "70%",
          borderRadius: 2,
        },
      },
      dataLabels: { enabled: false },
      legend: {
        position: "top",
        horizontalAlign: "left",
        fontSize: "11px",
      },
      tooltip: {
        y: { formatter: (val) => val < 1 ? `${val.toFixed(2)}%` : `${val.toFixed(1)}%` },
      },
    };

    charts.cpuPercent = new ApexCharts(container, options);
    charts.cpuPercent.render();
  }

  // Correctness Chart (Grouped Bar)
  function renderCorrectnessChart(data) {
    const container = document.getElementById("chart-correctness");
    if (!container) return;

    if (data.fixtures.length === 0 || data.implementations.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No correctness data available</p>';
      return;
    }

    const series = data.implementations.map((impl) => ({
      name: impl,
      data: (data.correctness_data[impl] || []).map((v) => (v * 100).toFixed(1)),
    }));

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
      },
      series: series,
      xaxis: {
        categories: data.fixtures,
        title: { text: "Fixture" },
      },
      yaxis: {
        title: { text: "Correctness (%)"},
        min: 0,
        max: 100,
        labels: {
          formatter: (val) => `${val}%`,
        },
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: "70%",
          borderRadius: 2,
        },
      },
      dataLabels: { enabled: false },
      legend: {
        position: "top",
        horizontalAlign: "left",
        fontSize: "11px",
      },
      tooltip: {
        y: { formatter: (val) => `${val}%` },
      },
    };

    charts.correctness = new ApexCharts(container, options);
    charts.correctness.render();
  }

  // Summary Comparison Chart (Radar)
  function renderSummaryChart(data) {
    const container = document.getElementById("chart-summary");
    if (!container) return;

    if (data.implementations.length === 0) {
      container.innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No summary data available</p>';
      return;
    }

    // Calculate normalized scores for each implementation
    const summary = data.summary || {};
    const metrics = ["Speed", "Memory Efficiency", "CPU Efficiency", "Correctness"];

    // Find min values for ratio-based normalization (best performers)
    // For CPU efficiency, lower CPU% (cpu_time/wall_time) = more efficient
    let minTime = Infinity;
    let minMemory = Infinity;
    let minCpuPercent = Infinity;
    data.implementations.forEach((impl) => {
      const s = summary[impl] || {};
      const time = s.avg_wall_time_s || 0;
      const memory = s.avg_peak_mem_mb || 0;
      const cpuTime = s.avg_cpu_time_s || 0;
      // CPU% = cpu_time / wall_time (lower = more efficient, uses less CPU per second)
      const cpuPercent = time > 0 && cpuTime > 0 ? (cpuTime / time) * 100 : 0;
      if (time > 0 && time < minTime) minTime = time;
      if (memory > 0 && memory < minMemory) minMemory = memory;
      if (cpuPercent > 0 && cpuPercent < minCpuPercent) minCpuPercent = cpuPercent;
    });

    const series = data.implementations.map((impl) => {
      const s = summary[impl] || {};
      // Ratio-based: best performer = 100%, others = (best/theirs) * 100
      const time = s.avg_wall_time_s || 0;
      const memory = s.avg_peak_mem_mb || 0;
      const cpuTime = s.avg_cpu_time_s || 0;
      // CPU% = cpu_time / wall_time (lower = more efficient)
      const cpuPercent = time > 0 && cpuTime > 0 ? (cpuTime / time) * 100 : 0;
      const speedScore = time > 0 ? (minTime / time) * 100 : 0;
      const memoryScore = memory > 0 ? (minMemory / memory) * 100 : 0;
      // Lower CPU% = higher efficiency score
      const cpuScore = cpuPercent > 0 ? (minCpuPercent / cpuPercent) * 100 : 0;
      const correctnessScore = ((s.avg_correctness || 0) * 100);

      return {
        name: impl,
        data: [speedScore, memoryScore, cpuScore, correctnessScore],
      };
    });

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "radar",
        height: 320,
      },
      series: series,
      xaxis: {
        categories: metrics,
      },
      yaxis: {
        show: false,
      },
      stroke: {
        width: 2,
      },
      fill: {
        opacity: 0.2,
      },
      markers: {
        size: 4,
      },
      legend: {
        position: "top",
        horizontalAlign: "left",
        fontSize: "11px",
      },
      tooltip: {
        y: {
          formatter: (val) => `${val.toFixed(1)}%`,
        },
      },
    };

    charts.summary = new ApexCharts(container, options);
    charts.summary.render();
  }

  // Initialize charts when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadCharts);
  } else {
    loadCharts();
  }
})();
