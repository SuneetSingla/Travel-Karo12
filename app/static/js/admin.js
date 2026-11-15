// Admin dashboard charts (Chart.js). Data comes from window.TK_CHARTS.
// Each chart renders only if its <canvas> exists on the page.
(function () {
  if (typeof Chart === "undefined" || !window.TK_CHARTS) return;

  var PURPLE = "#7c3aed", LAVENDER = "#a855f7", PINK = "#ec4899";
  var palette = ["#7c3aed", "#a855f7", "#c084fc", "#ec4899", "#f0abfc", "#6b3cb0", "#f9a8d4"];
  Chart.defaults.font.family = "Poppins, system-ui, sans-serif";
  Chart.defaults.color = "#6b6880";

  function el(id) { return document.getElementById(id); }

  if (el("chartViews")) {
    var v = window.TK_CHARTS.views;
    new Chart(el("chartViews"), {
      type: "line",
      data: { labels: v.labels, datasets: [{ data: v.values, label: "Visits",
        borderColor: PINK, backgroundColor: "rgba(236,72,153,.12)", fill: true,
        tension: 0.35, pointBackgroundColor: PINK, borderWidth: 2 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  }

  if (el("chartMonths")) {
    var m = window.TK_CHARTS.months;
    new Chart(el("chartMonths"), {
      type: "line",
      data: { labels: m.labels, datasets: [{ data: m.values, label: "Enquiries",
        borderColor: PURPLE, backgroundColor: "rgba(124,58,237,.12)", fill: true,
        tension: 0.35, pointBackgroundColor: PURPLE, borderWidth: 2 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  }

  if (el("chartStatus")) {
    var s = window.TK_CHARTS.status;
    new Chart(el("chartStatus"), {
      type: "doughnut",
      data: { labels: s.labels, datasets: [{ data: s.values, backgroundColor: palette, borderWidth: 0 }] },
      options: { plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } } }, cutout: "60%" },
    });
  }

  if (el("chartService")) {
    var sv = window.TK_CHARTS.service;
    new Chart(el("chartService"), {
      type: "bar",
      data: { labels: sv.labels, datasets: [{ data: sv.values, backgroundColor: LAVENDER, borderRadius: 6 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { ticks: { font: { size: 10 } } } } },
    });
  }
})();
