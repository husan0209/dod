/* Chart.js utilities for Prediction Markets */

function initPriceChart(chartData) {
    const ctx = document.getElementById('priceChart');
    if (!ctx) return;

    const labels = chartData.labels || [];
    const yesData = chartData.yes_prices || [];
    const noData = chartData.no_prices || [];

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'YES Price',
                    data: yesData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#10b981',
                },
                {
                    label: 'NO Price',
                    data: noData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ef4444',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 13, weight: '600' }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(31, 41, 55, 0.9)',
                    borderColor: '#e5e7eb',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y.toFixed(4);
                            return `${context.dataset.label}: $${value}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: 0,
                    max: 1,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    },
                    grid: {
                        color: '#e5e7eb'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Period selector
document.querySelectorAll('.period-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        const period = this.dataset.period;
        
        // Update active state
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        // Fetch new chart data
        const marketId = window.location.pathname.split('/')[3];
        fetch(`/predictions/api/chart/${marketId}/?period=${period}`)
            .then(r => r.json())
            .then(data => {
                // Reinit chart with new data
                const canvas = document.getElementById('priceChart');
                if (canvas && canvas.chart) {
                    canvas.chart.destroy();
                }
                initPriceChart(data);
            });
    });
});
