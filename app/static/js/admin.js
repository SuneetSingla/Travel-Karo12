// Admin dashboard charts (Chart.js). Data comes from window.TK_CHARTS.
(function () {
  if (typeof Chart === "undefined" || !window.TK_CHARTS) return;

  var PURPLE = "#59309a";
  var LAVENDER = "#7e52c4";
  var PINK = "#e46fb2";
  var palette = ["#59309a", "#7e52c4", "#9d7ad4", "#e46fb2", "#bca8e4", "#45256f", "#f0a9cf"];

  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = "#6b5f80";

  var m = window.TK_CHARTS.months;
  new Chart(document.getElementById("chartMonths"), {
    type: "line",
    data: {
      labels: m.labels,
      datasets: [{
        data: m.values, label: "Enquiries",
        borderColor: PURPLE, backgroundColor: "rgba(89,48,154,0.12)",
        fill: true, tension: 0.35, pointBackgroundColor: PURPLE, borderWidth: 2,
      }],
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });

  var s = window.TK_CHARTS.status;
  new Chart(document.getElementById("chartStatus"), {
    type: "doughnut",
    data: { labels: s.labels, datasets: [{ data: s.values, backgroundColor: palette, borderWidth: 0 }] },
    options: { plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } } }, cutout: "60%" },
  });

  var sv = window.TK_CHARTS.service;
  new Chart(document.getElementById("chartService"), {
    type: "bar",
    data: { labels: sv.labels, datasets: [{ data: sv.values, backgroundColor: LAVENDER, borderRadius: 6 }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { ticks: { font: { size: 10 } } } } },
  });
})();
