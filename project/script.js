const charts = [
  ["#awareness-chart", "js/awareness.vg.json"],
  ["#intake-chart", "js/intake.vg.json"],
  ["#fastfood-map", "js/fastfood_map.vg.json"],
  ["#bubble-map", "js/bubble_map.vg.json"],
  ["#streamgraph", "js/streamgraph.vg.json"],
  ["#sankey", "js/sankey.vg.json"],
  ["#heatmap", "js/heatmap.vg.json"],
  ["#obesity-map", "js/obesity_map.vg.json"],
  ["#scatter", "js/scatter.vg.json"],
  ["#dumbbell", "js/dumbbell.vg.json"],
  ["#lollipop", "js/lollipop.vg.json"],
];

const embedOptions = {
  actions: false,
  renderer: "svg",
  config: {
    background: "transparent",
  },
};

async function renderCharts() {
  await Promise.all(
    charts.map(async ([selector, spec]) => {
      const element = document.querySelector(selector);
      if (!element) return;
      try {
        await vegaEmbed(selector, spec, embedOptions);
      } catch (error) {
        element.innerHTML = `<p class="chart-error">Chart could not be loaded: ${spec}</p>`;
        console.error(error);
      }
    }),
  );
}

renderCharts();
