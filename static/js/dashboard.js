// ==========================================================
// 🌐 Dashboard de monitoreo - Cliente JavaScript
// ----------------------------------------------------------
// Carga datos desde el backend Flask y renderiza tres gráficos:
//  - CPU y RAM
//  - Tráfico de red (Enviado/Recibido)
//  - IPs bloqueadas (Fail2Ban)
// ==========================================================


// ===============================
// 🔧 Variables globales
// ===============================
let CpuRamChart = null;   // Referencia al gráfico de CPU/RAM
let NetChart = null;      // Referencia al gráfico de red
let bansChart = null;     // Referencia al gráfico de IPs bloqueadas
let FontSize = 13;        // Tamaño base de fuente
let TicksLimit = 24;      // Máximo de etiquetas visibles en eje X


// ==========================================================
// 📊 Cargar gráfico principal de métricas del sistema
// ----------------------------------------------------------
// Obtiene uso de CPU, RAM, red y los muestra en líneas continuas
// ==========================================================
async function loadDashboardData() {
  try {
    // 1️⃣ Solicita datos al endpoint del backend Flask
    const response = await fetch('/api/history');
    const data = await response.json();

    // 🧮 Extrae totales y promedios de CPU/RAM/red
    const totals = data.totals || {
      avg_cpu: data.summary.avg_cpu,
      avg_ram: data.summary.avg_ram,
      total_net_recv_MB: data.summary.total_net_recv_MB,
      total_net_sent_MB: data.summary.total_net_sent_MB
    };

    // Formatea etiquetas de tiempo (solo HH:mm)
    data.labels = data.labels.map(t => t.split(" ")[1].slice(0, 5));

    // 🔍 Debug opcional en consola
    //console.log("CPU (%)", data.datasets.cpu_usage);
    //console.log("RAM (%)", data.datasets.ram_usage);
    //console.log("Net Sent (MB)", data.datasets.net_sent);
    //console.log("Net Recv (MB)", data.datasets.net_recv);


    // ======================================================
    // 🧭 Gráfico 1: CPU / RAM
    // ======================================================
    const ctx1 = document.getElementById('CpuRamChart').getContext('2d');

    // Si no existe el gráfico, se crea
    if (!CpuRamChart) {
      CpuRamChart = new Chart(ctx1, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [
            {
              label: `CPU (${totals.avg_cpu}% promedio)`,
              data: data.datasets.cpu_usage,
              backgroundColor: 'red',
              borderColor: 'red',
              fill: false,
              pointRadius: 0,
              tension: 0.3
            },
            {
              label: `RAM (${totals.avg_ram}% promedio)`,
              data: data.datasets.ram_usage,
              backgroundColor: 'blue',
              borderColor: 'blue',
              fill: false,
              pointRadius: 0,
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            title: { display: false, text: 'Uso de CPU y RAM' },
            legend: {
              position: 'top',
              labels: {
                color: '#b0b0b0',
                font: { family: 'Segoe UI, sans-serif', size: FontSize }
              }
            }
          },
          scales: {
            x: {
              title: { display: true },
              grid: { color: 'rgba(150,150,150,0.2)', lineWidth: 1 },
              ticks: {
                autoSkip: true,
                maxTicksLimit: TicksLimit,
                color: '#b0b0b0',
                font: { family: 'Segoe UI, sans-serif', size: FontSize }
              }
            },
            y: {
              title: {
                display: false,
                text: 'Porcentaje (%)',
                color: '#cccccc',
                font: { family: 'Segoe UI, sans-serif', size: FontSize }
              },
              grid: { color: 'rgba(150,150,150,0.2)', lineWidth: 1 },
              ticks: {
                color: '#b0b0b0',
                font: { size: FontSize, family: 'Segoe UI, sans-serif' }
              }
            }
          }
        }
      });
    } else {
      // Si ya existe, actualiza datos
      CpuRamChart.data.labels = data.labels;
      CpuRamChart.data.datasets[0].data = data.datasets.cpu_usage;
      CpuRamChart.data.datasets[1].data = data.datasets.ram_usage;
      CpuRamChart.update();
    }


    // ======================================================
    // 🌐 Gráfico 2: Red (Net Sent / Net Recv)
    // ======================================================
    const ctx2 = document.getElementById('NetChart').getContext('2d');

    // Si no existe, crear gráfico
    if (!NetChart) {
      NetChart = new Chart(ctx2, {
        type: 'line',
        data: {
          labels: data.labels,
          datasets: [
            {
              label: `Net Sent (${totals.total_net_sent_MB} MB totales)`,
              data: data.datasets.net_sent,
              backgroundColor: 'green',
              borderColor: 'green',
              fill: false,
              pointRadius: 0,
              tension: 0.3
            },
            {
              label: `Net Recv (${totals.total_net_recv_MB} MB totales)`,
              data: data.datasets.net_recv,
              backgroundColor: 'orange',
              borderColor: 'orange',
              fill: false,
              pointRadius: 0,
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            title: { display: false, text: 'Uso de Red (MB)' },
            legend: {
              position: 'top',
              labels: {
                color: '#b0b0b0',
                font: { family: 'Segoe UI, sans-serif', size: FontSize }
              }
            }
          },
          scales: {
            x: {
              title: { display: true },
              grid: { color: 'rgba(150,150,150,0.2)', lineWidth: 1 },
              ticks: {
                autoSkip: true,
                maxTicksLimit: TicksLimit,
                color: '#b0b0b0',
                font: { family: 'Segoe UI, sans-serif', size: FontSize }
              }
            },
            y: {
              title: {
                display: false,
                text: 'MB enviados/recibidos',
                family: 'Segoe UI, sans-serif',
                color: '#cccccc'
              },
              grid: { color: 'rgba(150,150,150,0.2)', lineWidth: 1 },
              ticks: {
                color: '#b0b0b0',
                font: { family: 'Segoe UI, sans-serif', size: FontSize }
              }
            }
          }
        }
      });
    } else {
      // Actualiza datos existentes
      NetChart.data.labels = data.labels;
      NetChart.data.datasets[0].data = data.datasets.net_sent;
      NetChart.data.datasets[1].data = data.datasets.net_recv;
      NetChart.update();
    }

  } catch (error) {
    console.error("Error al cargar datos:", error);
  }
}


// ==========================================================
// 🚫 Cargar gráfico de IPs bloqueadas (Fail2Ban)
// ----------------------------------------------------------
// Muestra conteo de IPs IPv4 e IPv6 bloqueadas por minuto
// ==========================================================
async function loadBansTrend() {
  try {
    const response = await fetch('/api/bans-details');
    const result = await response.json();

    const data = result.data;
    const total_ipv4 = result.summary.total_ipv4;
    const total_ipv6 = result.summary.total_ipv6;

    //console.log("total_ipv4", total_ipv4);
    //console.log("total_ipv6", total_ipv6);

    // Prepara arrays con valores por minuto
    const labels = Object.keys(data).sort();
    const ipv4Counts = [];
    const ipv6Counts = [];
    const ipv4Details = [];
    const ipv6Details = [];

    labels.forEach(time => {
      ipv4Counts.push(data[time].ipv4.length);
      ipv6Counts.push(data[time].ipv6.length);
      ipv4Details.push(data[time].ipv4);
      ipv6Details.push(data[time].ipv6);
    });

    // Etiquetas reducidas a formato HH:mm
    const shortLabels = labels.map(t => t.split(" ")[1].slice(0, 5));

    const ctx = document.getElementById("bansTrendChart").getContext("2d");

    // Si el gráfico ya existe, solo actualizar
    if (bansChart) {
      bansChart.data.labels = shortLabels;
      bansChart.data.datasets[0].data = ipv4Counts;
      bansChart.data.datasets[1].data = ipv6Counts;
      bansChart.update();
      return;
    }

    // Crear nuevo gráfico tipo barra
    bansChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: shortLabels,
        datasets: [
          {
            label: `IPv4 bloqueadas ( ${total_ipv4} )`,
            data: ipv4Counts,
            backgroundColor: "rgba(231, 76, 60, 0.7)",
            borderColor: "rgba(231, 76, 60, 1)",
            borderWidth: 1
          },
          {
            label: `IPv6 bloqueadas ( ${total_ipv6} )`,
            data: ipv6Counts,
            backgroundColor: "rgba(52, 152, 219, 0.7)",
            borderColor: "rgba(52, 152, 219, 1)",
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            title: {
              display: true,
              color: "#cccccc",
              font: { family: "Segoe UI, sans-serif", size: FontSize }
            },
            grid: { color: "rgba(150,150,150,0.2)", lineWidth: 1 },
            ticks: {
              color: "#b0b0b0",
              font: { family: "Segoe UI, sans-serif", size: FontSize },
              autoSkip: true,
              maxTicksLimit: TicksLimit
            }
          },
          y: {
            beginAtZero: true,
            title: {
              display: false,
              text: "Cantidad de IPs bloqueadas",
              color: "#cccccc",
              //font: { family: "Segoe UI, sans-serif", size: FontSize }
            },
            grid: { color: "rgba(150,150,150,0.2)", lineWidth: 1 },
            ticks: {
              color: "#b0b0b0",
              font: { family: "Segoe UI, sans-serif", size: FontSize }
            }
          }
        },
        plugins: {
          title: {
            display: false,
            text: "IPs bloqueadas por minuto (últimas 24h)",
            color: "#b0b0b0",
            font: { family: "Segoe UI, sans-serif", size: FontSize }
          },
          legend: {
            position: "top",
            labels: {
              color: "#b0b0b0",
              font: { family: "Segoe UI, sans-serif", size: FontSize }
            }
          },
          tooltip: {
            callbacks: {
              // Tooltip personalizado: lista IPs bloqueadas por minuto
              afterBody: function (context) {
                let lines = [];

                context.forEach(ctx => {
                  const index = ctx.dataIndex;
                  const datasetIndex = ctx.datasetIndex;

                  // Dataset 0 = IPv4, Dataset 1 = IPv6
                  const ips = datasetIndex === 0
                    ? ipv4Details[index]
                    : ipv6Details[index];

                  if (ips && ips.length > 0) {
                    lines.push(`${ctx.dataset.label}:`);
                    lines.push(...ips.map(ip => `  • ${ip}`));
                  }
                });

                if (lines.length === 0) return "Sin IPs bloqueadas";
                return lines.join("\n");
              }
            }
          }
        }
      }
    });

  } catch (err) {
    console.error("Error al cargar datos de bloqueos:", err);
  }
}


// ==========================================================
// 🔁 Inicialización automática del dashboard
// ----------------------------------------------------------
// Ejecuta todas las funciones al cargar la página y actualiza
// cada 30 segundos los datos de métricas y bloqueos.
// ==========================================================
window.addEventListener('DOMContentLoaded', () => {
  // Cargar métricas del sistema
  loadDashboardData();

  // Cargar gráfico de IPs bloqueadas
  loadBansTrend();

  // Refrescar cada 30 segundos
  setInterval(() => {
    loadDashboardData();
    loadBansTrend();
  }, 30000);
});
