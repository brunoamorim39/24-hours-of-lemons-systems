// 24 Hours of Lemons - Telemetry Dashboard JavaScript

// Socket.IO connection
const socket = io();

// Chart.js setup
const ctx = document.getElementById('historyChart').getContext('2d');
const maxDataPoints = 60;  // Keep last 60 data points
const historyData = {
    labels: [],
    speed: [],
    rpm: []
};

const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: historyData.labels,
        datasets: [
            {
                label: 'Speed (km/h)',
                data: historyData.speed,
                borderColor: '#0f0',
                backgroundColor: 'rgba(0, 255, 0, 0.1)',
                yAxisID: 'y-speed',
                tension: 0.4
            },
            {
                label: 'RPM',
                data: historyData.rpm,
                borderColor: '#0af',
                backgroundColor: 'rgba(0, 170, 255, 0.1)',
                yAxisID: 'y-rpm',
                tension: 0.4
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,  // Disable animation for real-time updates
        scales: {
            x: {
                display: false  // Hide time labels for cleaner look
            },
            'y-speed': {
                type: 'linear',
                position: 'left',
                title: {
                    display: true,
                    text: 'Speed (km/h)',
                    color: '#0f0'
                },
                ticks: {
                    color: '#0f0'
                },
                grid: {
                    color: '#1a3a1a'
                }
            },
            'y-rpm': {
                type: 'linear',
                position: 'right',
                title: {
                    display: true,
                    text: 'RPM',
                    color: '#0af'
                },
                ticks: {
                    color: '#0af'
                },
                grid: {
                    display: false
                }
            }
        },
        plugins: {
            legend: {
                labels: {
                    color: '#0f0'
                }
            }
        }
    }
});

// Connection handlers
socket.on('connect', () => {
    console.log('Connected to telemetry server');
    updateConnectionStatus(true);
});

socket.on('disconnect', () => {
    console.log('Disconnected from telemetry server');
    updateConnectionStatus(false);
});

socket.on('status', (data) => {
    console.log('Status:', data.message);
});

// Telemetry update handler
socket.on('telemetry_update', (data) => {
    updateDashboard(data);
});

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    if (connected) {
        statusEl.textContent = 'Connected';
        statusEl.className = 'connection-status connected';
    } else {
        statusEl.textContent = 'Disconnected';
        statusEl.className = 'connection-status disconnected';
    }
}

function updateDashboard(data) {
    // OBD data
    if (data.obd) {
        updateMetric('speed', data.obd.SPEED, 1);
        updateMetric('rpm', data.obd.RPM, 0);
        updateMetric('coolant', data.obd.COOLANT_TEMP, 1, getCoolantClass);
        updateMetric('throttle', data.obd.THROTTLE_POS, 1);
        updateMetric('engineLoad', data.obd.ENGINE_LOAD, 1);

        // Update chart
        updateChart(data.obd.SPEED, data.obd.RPM);
    }

    // DRS status
    if (data.custom && data.custom.drs) {
        updateDRSStatus(data.custom.drs);
    }
}

function updateMetric(id, value, decimals, classFunc) {
    const el = document.getElementById(id);
    if (value !== null && value !== undefined) {
        el.textContent = value.toFixed(decimals);

        // Apply warning/danger classes if provided
        if (classFunc) {
            el.className = 'metric-value ' + classFunc(value);
        }
    } else {
        el.textContent = '--';
        el.className = 'metric-value';
    }
}

function getCoolantClass(temp) {
    if (temp > 100) return 'danger';
    if (temp > 95) return 'warning';
    return '';
}

function updateDRSStatus(drsData) {
    const cardEl = document.getElementById('drsCard');
    const statusEl = document.getElementById('drsStatus');

    if (drsData.active) {
        cardEl.className = 'drs-card active';
        statusEl.textContent = 'ACTIVE';
    } else {
        cardEl.className = 'drs-card';
        statusEl.textContent = drsData.state.toUpperCase();
    }
}

function updateChart(speed, rpm) {
    // Add new data point
    const timestamp = new Date().toLocaleTimeString();
    historyData.labels.push(timestamp);
    historyData.speed.push(speed || 0);
    historyData.rpm.push(rpm || 0);

    // Keep only last N points
    if (historyData.labels.length > maxDataPoints) {
        historyData.labels.shift();
        historyData.speed.shift();
        historyData.rpm.shift();
    }

    // Update chart
    chart.update();
}

// Fallback: Poll REST API if WebSocket fails
let pollInterval = null;

function startPolling() {
    if (pollInterval) return;

    console.log('Starting REST API polling fallback');
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/telemetry');
            if (response.ok) {
                const data = await response.json();
                updateDashboard(data);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 1000);  // Poll every second
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Use WebSocket by default, fallback to polling if connection fails
socket.on('connect_error', () => {
    console.log('WebSocket connection failed, falling back to polling');
    startPolling();
});

socket.on('connect', () => {
    stopPolling();
});
