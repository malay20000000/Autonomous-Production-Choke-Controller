let isRunning = false;
let time = 0;
let stableCount = 0; // Tracks how long we've been at the target
let totalRevenue = 0; // Tracks cumulative INR revenue
let simDataLog = []; // Accumulate data for CSV export

// Chart.js Setup
Chart.defaults.color = 'rgba(255, 255, 255, 0.7)'; // text-on-surface
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.05)';

const ctxFlow = document.getElementById('flowChart').getContext('2d');
const ctxPressure = document.getElementById('pressureChart').getContext('2d');

const flowChart = new Chart(ctxFlow, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Target Flow Rate (Q)',
                data: [],
                borderColor: 'rgba(255, 255, 255, 0.4)', // white translucent
                borderDash: [5, 5],
                borderWidth: 2,
                pointRadius: 0,
                tension: 0
            },
            {
                label: 'Actual Flow Rate (Q)',
                data: [],
                borderColor: 'rgba(255, 255, 255, 1)', // white solid
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.3
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false }
        },
        scales: {
            y: { min: 0 }
        }
    }
});

const pressureChart = new Chart(ctxPressure, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'WHP (psi)',
                data: [],
                borderColor: 'rgba(255, 255, 255, 0.9)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3
            },
            {
                label: 'FLP (psi)',
                data: [],
                borderColor: 'rgba(255, 255, 255, 0.5)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3
            },
            {
                label: 'BHP (psi)',
                data: [],
                borderColor: 'rgba(255, 255, 255, 0.2)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { 
                display: true,
                position: 'bottom',
                labels: {
                    usePointStyle: true,
                    boxWidth: 8
                }
            }
        },
        scales: {
            y: { min: 0 }
        }
    }
});

// Controls
document.getElementById('start-btn').addEventListener('click', () => {
    if (isRunning) {
        isRunning = false;
        document.getElementById('start-btn').innerText = 'Start Simulation';
        document.getElementById('start-btn').className = 'btn primary';
    } else {
        isRunning = true;
        // Ensure the box has a value
        const targetInput = document.getElementById('target-q');
        if (targetInput.value === '') {
            targetInput.value = '100';
        }
        
        // Always sync the backend with the UI box when starting
        fetch('/api/target', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: parseFloat(targetInput.value) })
        });
        
        simulationLoop(); // Start the robust async loop
        document.getElementById('start-btn').innerText = 'Pause Simulation';
        document.getElementById('start-btn').className = 'btn danger';
    }
});

document.getElementById('reset-btn').addEventListener('click', async () => {
    // Stop the simulation if it is running
    if (isRunning) {
        document.getElementById('start-btn').click();
    }

    await fetch('/api/reset', { method: 'POST' });
    time = 0;
    totalRevenue = 0;
    document.getElementById('val-rev').innerText = '₹0';
    
    document.getElementById('health-val').innerText = '100%';
    document.getElementById('health-bar-fill').style.width = '100%';
    document.getElementById('health-bar-fill').className = 'h-full bg-white w-[100%] shadow-[0_0_10px_rgba(255,255,255,0.8)] transition-all duration-300';
    document.getElementById('health-val').className = 'text-white font-medium text-lg';
    
    // Clear the input box to make it mandatory to fill
    document.getElementById('target-q').value = '';
    
    // Reset Charts
    flowChart.data.labels = [];
    flowChart.data.datasets[0].data = [];
    flowChart.data.datasets[1].data = [];
    flowChart.update();

    pressureChart.data.labels = [];
    pressureChart.data.datasets.forEach(ds => ds.data = []);
    pressureChart.update();

    updateMetrics(0, 0, 329, 218);
    
    // Clear Event Log & CSV Data
    simDataLog = [];
    const logDiv = document.getElementById('event-log');
    if (logDiv) {
        logDiv.innerHTML = '<div class="py-1 text-on-surface-variant">System reset. Waiting to start simulation...</div>';
    }
});

// Auto-reset on page load to ensure clean state
window.addEventListener('load', async () => {
    await document.getElementById('reset-btn').click();
});

// Download Report
document.getElementById('download-btn').addEventListener('click', () => {
    if (simDataLog.length === 0) {
        alert("No data to download yet. Run the simulation first.");
        return;
    }
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Time_hr,Target_Q,Actual_Q,Choke_pct,WHP_psi,FLP_psi,BHP_psi,Cumulative_Revenue_INR\n";
    
    simDataLog.forEach(row => {
        csvContent += `${row.time},${row.target_q},${row.q.toFixed(2)},${row.choke_pct.toFixed(2)},${row.whp.toFixed(2)},${row.flp.toFixed(2)},${row.bhp.toFixed(2)},${row.revenue.toFixed(0)}\n`;
    });
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "Simulation_Report.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});


async function updateTarget() {
    const targetInput = document.getElementById('target-q');
    const newTarget = parseFloat(targetInput.value);
    
    // Visually update the chart immediately for feedback
    const lastLabel = flowChart.data.labels.length > 0 ? flowChart.data.labels[flowChart.data.labels.length-1] : 0;
    flowChart.data.datasets[0].data[flowChart.data.datasets[0].data.length - 1] = newTarget;
    flowChart.update();

    await fetch('/api/target', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: newTarget })
    });
    
    stableCount = 0;
}

document.getElementById('update-target-btn').addEventListener('click', updateTarget);
document.getElementById('target-q').addEventListener('change', updateTarget);
document.getElementById('target-q').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') updateTarget();
});

async function simulationLoop() {
    if (!isRunning) return;
    await stepSimulation();
    if (isRunning) {
        setTimeout(simulationLoop, 1000); // Schedule next frame only AFTER current finishes
    }
}

async function stepSimulation() {
    const res = await fetch('/api/step');
    const data = await res.json();
    
    time += 1;
    
    // Calculate Revenue & Maintenance
    const oilPrice = parseFloat(document.getElementById('oil-price').value) || 6500;
    totalRevenue += (data.q * oilPrice);
    
    // Format large numbers elegantly
    const formatter = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
    document.getElementById('val-rev').innerText = formatter.format(totalRevenue);

    // Update Health Bar
    const healthScore = data.health_score || 100;
    document.getElementById('health-val').innerText = healthScore.toFixed(0) + '%';
    document.getElementById('health-bar-fill').style.width = healthScore + '%';
    
    // Dynamic Health Colors
    if (healthScore > 80) {
        document.getElementById('health-val').className = 'text-white font-medium text-lg';
        document.getElementById('health-bar-fill').className = 'h-full bg-white transition-all duration-300 shadow-[0_0_10px_rgba(255,255,255,0.8)]';
    } else if (healthScore > 50) {
        document.getElementById('health-val').className = 'text-white/70 font-medium text-lg';
        document.getElementById('health-bar-fill').className = 'h-full bg-white/70 transition-all duration-300 shadow-[0_0_10px_rgba(255,255,255,0.5)]';
    } else {
        document.getElementById('health-val').className = 'text-white/40 font-medium text-lg';
        document.getElementById('health-bar-fill').className = 'h-full bg-white/40 transition-all duration-300 shadow-[0_0_5px_rgba(255,255,255,0.2)]';
    }

    // Log data for CSV
    simDataLog.push({
        time: time,
        target_q: data.target_q,
        q: data.q,
        choke_pct: data.choke_pct,
        whp: data.whp,
        flp: data.flp,
        bhp: data.bhp,
        revenue: totalRevenue
    });
    
    updateMetrics(data.q, data.choke_pct, data.whp, data.flp);

    // Update Event Log
    if (data.status_message) {
        const logDiv = document.getElementById('event-log');
        if (logDiv) {
            const entry = document.createElement('div');
            entry.className = 'py-1 border-b border-white/5 ';
            
            // Format log entry color
            if (data.status_message.includes('WARNING') || data.status_message.includes('Limit')) {
                entry.className += 'text-white/80 font-semibold';
            } else if (data.status_message.includes('achieved')) {
                entry.className += 'text-white';
            } else {
                entry.className += 'text-white/50';
            }
            
            const timeStr = `[Hr ${time.toString().padStart(2, '0')}] `;
            entry.innerText = timeStr + data.status_message;
            logDiv.appendChild(entry);
            
            // Auto scroll to bottom
            logDiv.scrollTop = logDiv.scrollHeight;
        }
    }
    
    // Update Charts
    flowChart.data.labels.push(time);
    flowChart.data.datasets[0].data.push(data.target_q);
    flowChart.data.datasets[1].data.push(data.q);
    
    pressureChart.data.labels.push(time);
    pressureChart.data.datasets[0].data.push(data.whp);
    pressureChart.data.datasets[1].data.push(data.flp);
    pressureChart.data.datasets[2].data.push(data.bhp);

    // Keep last 60 points
    if (flowChart.data.labels.length > 60) {
        flowChart.data.labels.shift();
        flowChart.data.datasets.forEach(ds => ds.data.shift());
        
        pressureChart.data.labels.shift();
        pressureChart.data.datasets.forEach(ds => ds.data.shift());
    }

    flowChart.update();
    pressureChart.update();

    // Auto-pause logic
    if (Math.abs(data.q - data.target_q) < 0.2) {
        stableCount++;
        if (stableCount >= 5 && isRunning) {
            document.getElementById('start-btn').click(); // Auto-pause
        }
    } else {
        stableCount = 0;
    }
}

function updateMetrics(q, choke, whp, flp) {
    document.getElementById('val-q').innerText = q.toFixed(1);
    document.getElementById('val-choke').innerText = choke.toFixed(1);
    document.getElementById('val-whp').innerText = whp.toFixed(0);
    document.getElementById('val-flp').innerText = flp.toFixed(0);
}



