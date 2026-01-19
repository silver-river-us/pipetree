/**
 * Benchmarks Dashboard Charts
 * Uses ApexCharts for visualization
 */

(function () {
  // Chart instances (for cleanup on re-render)
  let charts = {
    runTrend: null,
    stepDurations: null,
    throughput: null,
    avgSteps: null,
  };

  // Store data for click navigation
  let chartData = {
    trends: [],
    runs: [],
    throughput: [],
  };

  // Navigate to run detail page
  function navigateToRun(fullRunId, dbPath) {
    if (fullRunId && dbPath) {
      window.location.href = `/runs/${fullRunId}?db=${encodeURIComponent(dbPath)}`;
    }
  }

  // DOM elements
  const pipelineSelect = document.getElementById("pipeline-select");
  const runLimitSelect = document.getElementById("run-limit");
  const chartsContainer = document.getElementById("charts-container");
  const emptyState = document.getElementById("empty-state");
  const loadingState = document.getElementById("loading-state");
  const noDataState = document.getElementById("no-data-state");

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
    stroke: { curve: "smooth" },
    tooltip: { theme: "light" },
    grid: {
      borderColor: "#e2e8f0",
      strokeDashArray: 4,
    },
    states: {
      hover: {
        filter: { type: "lighten", value: 0.1 },
      },
      active: {
        filter: { type: "darken", value: 0.1 },
      },
    },
  };

  // Format duration for display
  function formatDuration(seconds) {
    if (seconds == null || isNaN(seconds)) return "-";
    if (seconds < 0.001) return `${(seconds * 1000000).toFixed(0)}us`;
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(2)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toFixed(1)}s`;
  }

  // Show/hide states
  function showState(state) {
    chartsContainer.classList.add("hidden");
    emptyState.classList.add("hidden");
    loadingState.classList.add("hidden");
    noDataState.classList.add("hidden");

    if (state === "charts") chartsContainer.classList.remove("hidden");
    else if (state === "empty") emptyState.classList.remove("hidden");
    else if (state === "loading") loadingState.classList.remove("hidden");
    else if (state === "no-data") noDataState.classList.remove("hidden");
  }

  // Destroy existing charts
  function destroyCharts() {
    Object.values(charts).forEach((chart) => {
      if (chart) chart.destroy();
    });
    charts = {
      runTrend: null,
      stepDurations: null,
      throughput: null,
      avgSteps: null,
    };
  }

  // Fetch data and render charts
  async function loadBenchmarks() {
    const pipeline = pipelineSelect.value;
    const limit = parseInt(runLimitSelect.value);

    if (!pipeline) {
      showState("empty");
      destroyCharts();
      return;
    }

    showState("loading");

    try {
      // Fetch all data in parallel
      const [stepDurationsRes, trendsRes, throughputRes] = await Promise.all([
        fetch(
          `/api/benchmarks/step-durations?pipeline=${encodeURIComponent(pipeline)}&limit=${limit}`
        ),
        fetch(
          `/api/benchmarks/run-trends?pipeline=${encodeURIComponent(pipeline)}&limit=${limit}`
        ),
        fetch(
          `/api/benchmarks/throughput?pipeline=${encodeURIComponent(pipeline)}&limit=${limit}`
        ),
      ]);

      const stepDurationsData = await stepDurationsRes.json();
      const trendsData = await trendsRes.json();
      const throughputData = await throughputRes.json();

      // Check if there's any data
      if (
        trendsData.trends.length === 0 &&
        stepDurationsData.runs.length === 0
      ) {
        showState("no-data");
        destroyCharts();
        return;
      }

      // Store data for click navigation
      chartData.trends = trendsData.trends;
      chartData.runs = stepDurationsData.runs;
      chartData.throughput = throughputData.throughput;

      destroyCharts();
      showState("charts");

      renderRunTrendChart(trendsData.trends);
      renderStepDurationsChart(
        stepDurationsData.runs,
        stepDurationsData.step_names
      );
      renderThroughputChart(throughputData.throughput);
      renderAvgStepsChart(stepDurationsData.runs, stepDurationsData.step_names);
      renderSummaryStats(trendsData.trends, throughputData.throughput);
    } catch (error) {
      console.error("Failed to load benchmarks:", error);
      showState("empty");
    }
  }

  // Run Duration Trend (Line Chart)
  function renderRunTrendChart(trends) {
    if (trends.length === 0) {
      document.getElementById("chart-run-trend").innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No trend data available</p>';
      return;
    }

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "line",
        height: 320,
        events: {
          dataPointSelection: function (event, chartContext, config) {
            const dataIndex = config.dataPointIndex;
            const trend = trends[dataIndex];
            if (trend) {
              navigateToRun(trend.full_run_id, trend.db_path);
            }
          },
        },
      },
      series: [
        {
          name: "Duration",
          data: trends.map((t) => ({
            x: t.started_at * 1000,
            y: t.duration_s ? parseFloat(t.duration_s.toFixed(2)) : null,
          })),
        },
      ],
      xaxis: {
        type: "datetime",
        labels: { datetimeUTC: false },
      },
      yaxis: {
        title: { text: "Duration (seconds)" },
        labels: {
          formatter: (val) => formatDuration(val),
        },
      },
      tooltip: {
        x: { format: "MMM dd, yyyy hh:mm tt" },
        y: { formatter: (val) => formatDuration(val) },
      },
      markers: {
        size: 4,
        hover: { size: 6 },
      },
    };

    charts.runTrend = new ApexCharts(
      document.getElementById("chart-run-trend"),
      options
    );
    charts.runTrend.render();
  }

  // Step Durations Stacked Bar Chart
  function renderStepDurationsChart(runs, stepNames) {
    if (runs.length === 0 || stepNames.length === 0) {
      document.getElementById("chart-step-durations").innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No step duration data available</p>';
      return;
    }

    const series = stepNames.map((stepName) => ({
      name: stepName,
      data: runs.map((r) =>
        r.steps[stepName] ? parseFloat(r.steps[stepName].toFixed(3)) : 0
      ),
    }));

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
        stacked: true,
        events: {
          dataPointSelection: function (event, chartContext, config) {
            const dataIndex = config.dataPointIndex;
            const run = runs[dataIndex];
            if (run) {
              navigateToRun(run.full_run_id, run.db_path);
            }
          },
        },
      },
      series: series,
      xaxis: {
        categories: runs.map((r) => r.run_id),
        title: { text: "Run ID" },
        labels: {
          rotate: -45,
          rotateAlways: runs.length > 10,
        },
      },
      yaxis: {
        title: { text: "Duration (seconds)" },
        labels: { formatter: (val) => formatDuration(val) },
      },
      legend: {
        position: "top",
        horizontalAlign: "left",
        fontSize: "11px",
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: "70%",
        },
      },
      dataLabels: { enabled: false },
      tooltip: {
        y: { formatter: (val) => formatDuration(val) },
      },
    };

    charts.stepDurations = new ApexCharts(
      document.getElementById("chart-step-durations"),
      options
    );
    charts.stepDurations.render();
  }

  // Throughput Chart (Bar)
  function renderThroughputChart(throughput) {
    // Filter runs that have throughput data
    const validThroughput = throughput.filter(
      (t) => t.items_per_second != null && t.items_per_second > 0
    );

    if (validThroughput.length === 0) {
      document.getElementById("chart-throughput").innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No throughput data available (no progress events recorded)</p>';
      return;
    }

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
        events: {
          dataPointSelection: function (event, chartContext, config) {
            const dataIndex = config.dataPointIndex;
            const item = validThroughput[dataIndex];
            if (item) {
              navigateToRun(item.full_run_id, item.db_path);
            }
          },
        },
      },
      series: [
        {
          name: "Items/Second",
          data: validThroughput.map((t) =>
            t.items_per_second ? parseFloat(t.items_per_second.toFixed(2)) : 0
          ),
        },
      ],
      xaxis: {
        categories: validThroughput.map((t) => t.run_id),
        title: { text: "Run ID" },
        labels: {
          rotate: -45,
          rotateAlways: validThroughput.length > 10,
        },
      },
      yaxis: {
        title: { text: "Items per Second" },
      },
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: "60%",
          borderRadius: 2,
        },
      },
      colors: ["#22c55e"],
      dataLabels: { enabled: false },
    };

    charts.throughput = new ApexCharts(
      document.getElementById("chart-throughput"),
      options
    );
    charts.throughput.render();
  }

  // Average Step Durations (Horizontal Bar)
  function renderAvgStepsChart(runs, stepNames) {
    if (runs.length === 0 || stepNames.length === 0) {
      document.getElementById("chart-avg-steps").innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No step data available</p>';
      return;
    }

    // Calculate averages
    const avgDurations = stepNames
      .map((stepName) => {
        const durations = runs
          .map((r) => r.steps[stepName])
          .filter((d) => d != null && d > 0);
        const avg =
          durations.length > 0
            ? durations.reduce((a, b) => a + b, 0) / durations.length
            : 0;
        return { name: stepName, avg: avg };
      })
      .filter((d) => d.avg > 0)
      .sort((a, b) => b.avg - a.avg);

    if (avgDurations.length === 0) {
      document.getElementById("chart-avg-steps").innerHTML =
        '<p class="text-gray-500 text-sm text-center py-8">No step timing data available</p>';
      return;
    }

    const options = {
      ...commonOptions,
      chart: {
        ...commonOptions.chart,
        type: "bar",
        height: 320,
      },
      series: [
        {
          name: "Avg Duration",
          data: avgDurations.map((d) => parseFloat(d.avg.toFixed(3))),
        },
      ],
      xaxis: {
        title: { text: "Seconds" },
        labels: { formatter: (val) => formatDuration(val) },
      },
      yaxis: {
        labels: {
          maxWidth: 150,
        },
      },
      plotOptions: {
        bar: {
          horizontal: true,
          barHeight: "60%",
          borderRadius: 2,
        },
      },
      labels: avgDurations.map((d) => d.name),
      colors: ["#8b5cf6"],
      dataLabels: { enabled: false },
      tooltip: {
        y: { formatter: (val) => formatDuration(val) },
      },
    };

    charts.avgSteps = new ApexCharts(
      document.getElementById("chart-avg-steps"),
      options
    );
    charts.avgSteps.render();
  }

  // Summary Statistics
  function renderSummaryStats(trends, throughput) {
    const container = document.getElementById("summary-stats");

    // Calculate stats
    const durations = trends.map((t) => t.duration_s).filter((d) => d != null);
    const avgDuration =
      durations.length > 0
        ? durations.reduce((a, b) => a + b, 0) / durations.length
        : 0;
    const minDuration = durations.length > 0 ? Math.min(...durations) : 0;
    const maxDuration = durations.length > 0 ? Math.max(...durations) : 0;

    const itemsPerSec = throughput
      .map((t) => t.items_per_second)
      .filter((v) => v != null && v > 0);
    const avgThroughput =
      itemsPerSec.length > 0
        ? itemsPerSec.reduce((a, b) => a + b, 0) / itemsPerSec.length
        : 0;

    const stats = [
      { label: "Total Runs", value: trends.length.toString() },
      { label: "Avg Duration", value: formatDuration(avgDuration) },
      { label: "Fastest Run", value: formatDuration(minDuration) },
      { label: "Slowest Run", value: formatDuration(maxDuration) },
    ];

    // Add throughput if available
    if (avgThroughput > 0) {
      stats.push({
        label: "Avg Throughput",
        value: avgThroughput.toFixed(2) + " items/s",
      });
    }

    container.innerHTML = stats
      .map(
        (stat) => `
            <div class="bg-gray-50 p-4 border border-gray-200 rounded-lg">
                <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">${stat.label}</div>
                <div class="text-2xl font-bold text-gray-900">${stat.value}</div>
            </div>
        `
      )
      .join("");
  }

  // Event listeners
  pipelineSelect.addEventListener("change", loadBenchmarks);
  runLimitSelect.addEventListener("change", loadBenchmarks);

  // Auto-select first pipeline if available
  if (pipelineSelect.options.length > 1) {
    pipelineSelect.selectedIndex = 1;
    loadBenchmarks();
  }
})();
