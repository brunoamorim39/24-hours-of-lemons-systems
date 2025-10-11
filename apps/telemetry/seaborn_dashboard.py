"""Professional BMW E46 telemetry dashboard using Seaborn for clean, publication-quality plots.

This dashboard uses Seaborn/Matplotlib to generate static analysis plots with a modern BMW theme.
Unlike the previous Plotly approach, this:
- Generates clean, professional plots
- Stops collecting data after laps complete
- Actually implements sector and lap analysis
- Uses BMW blue/white/gray color scheme (not retro green terminal)
"""

import io
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for web
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, render_template_string, send_file, jsonify, Response

if TYPE_CHECKING:
    from apps.telemetry.main import TelemetryApp


# BMW Color Palette
BMW_BLUE = '#1C69D4'
BMW_GRAY = '#333333'
BMW_LIGHT_GRAY = '#F5F5F5'
BMW_WHITE = '#FFFFFF'
BMW_GOLD = '#FFD700'  # For highlighting best lap
BMW_ORANGE = '#FF8C00'  # For warnings

# Configure Seaborn theme
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'figure.facecolor': BMW_LIGHT_GRAY,
    'axes.facecolor': BMW_WHITE,
    'axes.edgecolor': BMW_GRAY,
    'text.color': '#1A1A1A',
    'axes.labelcolor': '#1A1A1A',
    'xtick.color': '#1A1A1A',
    'ytick.color': '#1A1A1A',
    'grid.color': '#DDDDDD',
    'grid.alpha': 0.5,
})


class SessionData:
    """Organized storage for telemetry data."""

    def __init__(self):
        self.laps = {}  # {lap_num: DataFrame}
        self.lap_times = {}  # {lap_num: time_seconds}
        self.drs_events = []
        self.session_complete = False
        self.lock = threading.Lock()
        self.live_data = {}  # Most recent telemetry sample for live display

    def add_lap(self, lap_num: int, telemetry_list: List[Dict], lap_time: float):
        """
        Add complete lap data.

        Args:
            lap_num: Lap number
            telemetry_list: List of telemetry dicts
            lap_time: Total lap time in seconds
        """
        with self.lock:
            if self.session_complete:
                print(f"[SessionData] Ignoring lap {lap_num} - session complete")
                return  # Don't add more data after session ends

            print(f"[SessionData] Adding lap {lap_num} with {len(telemetry_list)} samples, time={lap_time:.2f}s")
            self.laps[lap_num] = pd.DataFrame(telemetry_list)
            self.lap_times[lap_num] = lap_time
            print(f"[SessionData] Now have {len(self.laps)} laps stored")

    def add_drs_event(self, event: Dict):
        """Add DRS activation/deactivation event."""
        with self.lock:
            if not self.session_complete:
                self.drs_events.append(event)

    def update_live_data(self, telemetry_entry: Dict):
        """
        Update live telemetry data for real-time display.

        Args:
            telemetry_entry: Latest telemetry sample dict
        """
        with self.lock:
            if not self.session_complete:
                self.live_data = telemetry_entry

    def get_live_data(self) -> Dict:
        """Get most recent live telemetry data."""
        with self.lock:
            return self.live_data.copy() if self.live_data else {}

    def mark_complete(self):
        """Mark session as complete - stop accepting new data."""
        with self.lock:
            self.session_complete = True

    def get_summary(self) -> Dict:
        """Get session summary statistics."""
        if not self.lap_times:
            return {
                "total_laps": 0,
                "best_lap": None,
                "max_speed": 0,
                "drs_count": 0,
            }

        all_speeds = []
        for df in self.laps.values():
            all_speeds.extend(df['speed_kph'].tolist())

        return {
            "total_laps": len(self.laps),
            "best_lap": min(self.lap_times.values()) if self.lap_times else None,
            "max_speed": max(all_speeds) if all_speeds else 0,
            "drs_count": len([e for e in self.drs_events if e['event'] == 'DRS_OPEN']),
        }


class TelemetryDashboard:
    """Flask-based dashboard serving Seaborn plots."""

    def __init__(self, telemetry_app: "TelemetryApp"):
        """
        Initialize dashboard.

        Args:
            telemetry_app: Telemetry app instance
        """
        self.telemetry_app = telemetry_app
        self.session_data = SessionData()

        # Create Flask app
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/")
        def index():
            """Main dashboard page."""
            summary = self.session_data.get_summary()

            return render_template_string(
                DASHBOARD_HTML,
                best_lap=f"{summary['best_lap']:.2f}" if summary['best_lap'] else "--",
                total_laps=summary['total_laps'],
                drs_count=summary['drs_count'],
                max_speed=f"{summary['max_speed']:.1f}" if summary['max_speed'] > 0 else "--",
                timestamp=datetime.now().timestamp(),  # Cache busting
                session_complete=self.session_data.session_complete,
            )

        @self.app.route("/plots/speed_trace.png")
        def plot_speed_trace():
            """Generate speed trace plot."""
            fig = self._generate_speed_trace()
            return self._serve_plot(fig)

        @self.app.route("/plots/lap_times.png")
        def plot_lap_times():
            """Generate lap times bar chart."""
            fig = self._generate_lap_times()
            return self._serve_plot(fig)

        @self.app.route("/plots/sector_heatmap.png")
        def plot_sector_heatmap():
            """Generate sector analysis heatmap."""
            fig = self._generate_sector_heatmap()
            return self._serve_plot(fig)

        @self.app.route("/plots/drs_analysis.png")
        def plot_drs_analysis():
            """Generate DRS effectiveness plot."""
            fig = self._generate_drs_analysis()
            return self._serve_plot(fig)

        @self.app.route("/export/csv")
        def export_csv():
            """Export all lap data as CSV."""
            if not self.session_data.laps:
                return "No data available", 404

            # Combine all laps into one DataFrame
            all_data = pd.concat(self.session_data.laps.values(), ignore_index=True)

            # Convert to CSV
            csv_data = all_data.to_csv(index=False)

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=telemetry_data.csv"}
            )

        @self.app.route("/api/summary")
        def api_summary():
            """Get session summary as JSON."""
            return jsonify(self.session_data.get_summary())

        @self.app.route("/api/live")
        def api_live():
            """Get live telemetry data as JSON."""
            live_data = self.session_data.get_live_data()

            if not live_data:
                return jsonify({
                    "speed_kph": 0,
                    "rpm": 0,
                    "coolant_temp": 0,
                    "throttle": 0,
                    "lap": 0,
                    "sector": "--",
                    "drs_active": False,
                    "brake": False,
                })

            return jsonify({
                "speed_kph": round(live_data.get("speed_kph", 0), 1),
                "rpm": int(live_data.get("rpm", 0)),
                "coolant_temp": round(live_data.get("coolant_temp", 0), 1),
                "throttle": round(live_data.get("throttle", 0), 1),
                "lap": live_data.get("lap", 0),
                "sector": live_data.get("sector", "--"),
                "drs_active": live_data.get("drs_active", False),
                "brake": live_data.get("brake", False),
            })

    def _generate_speed_trace(self):
        """Generate lap speed comparison plot using Seaborn."""
        fig, ax = plt.subplots(figsize=(14, 6))

        if not self.session_data.laps:
            ax.text(
                0.5, 0.5, "Waiting for lap data...",
                ha='center', va='center', fontsize=16, color=BMW_GRAY
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            return fig

        # Plot each lap
        colors = sns.color_palette("husl", len(self.session_data.laps))
        for i, (lap_num, df) in enumerate(self.session_data.laps.items()):
            sns.lineplot(
                data=df,
                x='position_m',
                y='speed_kph',
                label=f'Lap {lap_num}',
                linewidth=2.5,
                color=colors[i],
                ax=ax
            )

        # Mark DRS zones with shading
        ax.axvspan(800, 1000, alpha=0.15, color='yellow', label='DRS Zone', zorder=0)
        ax.axvspan(2200, 3602, alpha=0.15, color='yellow', zorder=0)

        ax.set_xlabel('Track Position (m)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Speed (km/h)', fontsize=13, fontweight='bold')
        ax.set_title('Speed Trace - Lap Comparison', fontsize=15, fontweight='bold', pad=15)
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.4, linestyle='--')

        plt.tight_layout()
        return fig

    def _generate_lap_times(self):
        """Generate lap times bar chart."""
        fig, ax = plt.subplots(figsize=(10, 6))

        if not self.session_data.lap_times:
            ax.text(
                0.5, 0.5, "Lap times will appear after first lap completes",
                ha='center', va='center', fontsize=14, color=BMW_GRAY
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            return fig

        laps = list(self.session_data.lap_times.keys())
        times = list(self.session_data.lap_times.values())

        # Create bars
        bars = ax.bar(laps, times, color=BMW_BLUE, edgecolor=BMW_GRAY, linewidth=2)

        # Highlight fastest lap in gold
        fastest_idx = times.index(min(times))
        bars[fastest_idx].set_color(BMW_GOLD)
        bars[fastest_idx].set_edgecolor(BMW_GRAY)

        ax.set_xlabel('Lap Number', fontsize=13, fontweight='bold')
        ax.set_ylabel('Lap Time (seconds)', fontsize=13, fontweight='bold')
        ax.set_title('Lap Times Comparison', fontsize=15, fontweight='bold', pad=15)
        ax.grid(axis='y', alpha=0.4, linestyle='--')

        # Add value labels on top of bars
        for i, (lap, time_val) in enumerate(zip(laps, times)):
            label = f'{time_val:.2f}s'
            if i == fastest_idx:
                label += ' ⭐'
            ax.text(lap, time_val + 0.5, label, ha='center', fontweight='bold', fontsize=11)

        plt.tight_layout()
        return fig

    def _generate_sector_heatmap(self):
        """Generate sector analysis heatmap."""
        fig, ax = plt.subplots(figsize=(14, 8))

        if not self.session_data.laps:
            ax.text(
                0.5, 0.5, "Sector analysis will appear after laps complete",
                ha='center', va='center', fontsize=14, color=BMW_GRAY
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            return fig

        # Calculate average speed per sector per lap
        sector_data = []
        for lap_num, df in self.session_data.laps.items():
            for sector in df['sector'].unique():
                sector_df = df[df['sector'] == sector]
                avg_speed = sector_df['speed_kph'].mean()
                sector_data.append({
                    'Lap': f'Lap {lap_num}',
                    'Sector': sector,
                    'Avg Speed': avg_speed
                })

        if not sector_data:
            ax.text(0.5, 0.5, "No sector data available", ha='center', va='center')
            ax.axis('off')
            return fig

        # Pivot for heatmap
        pivot_df = pd.DataFrame(sector_data).pivot(index='Lap', columns='Sector', values='Avg Speed')

        # Create heatmap
        sns.heatmap(
            pivot_df,
            annot=True,
            fmt='.1f',
            cmap='RdYlGn',
            cbar_kws={'label': 'Average Speed (km/h)'},
            linewidths=1,
            linecolor=BMW_GRAY,
            ax=ax
        )

        ax.set_title('Sector Speed Analysis (Heatmap)', fontsize=15, fontweight='bold', pad=15)
        ax.set_xlabel('Sector', fontsize=13, fontweight='bold')
        ax.set_ylabel('Lap', fontsize=13, fontweight='bold')
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        return fig

    def _generate_drs_analysis(self):
        """Generate DRS effectiveness analysis."""
        fig, ax = plt.subplots(figsize=(12, 6))

        drs_opens = [e for e in self.session_data.drs_events if e['event'] == 'DRS_OPEN']

        if not drs_opens:
            ax.text(
                0.5, 0.5, "DRS analysis will appear after DRS activations",
                ha='center', va='center', fontsize=14, color=BMW_GRAY
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            return fig

        # Extract data
        laps = [e['lap'] for e in drs_opens]
        speeds = [e['speed_kph'] for e in drs_opens]
        sectors = [e['sector'] for e in drs_opens]

        # Scatter plot of DRS activations
        scatter = ax.scatter(laps, speeds, s=150, c=speeds, cmap='viridis', edgecolors=BMW_GRAY, linewidth=2)

        ax.set_xlabel('Lap Number', fontsize=13, fontweight='bold')
        ax.set_ylabel('Activation Speed (km/h)', fontsize=13, fontweight='bold')
        ax.set_title('DRS Activation Analysis', fontsize=15, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.4, linestyle='--')

        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Speed (km/h)', fontsize=11, fontweight='bold')

        # Add average line
        if speeds:
            avg_speed = sum(speeds) / len(speeds)
            ax.axhline(avg_speed, color='red', linestyle='--', linewidth=2, label=f'Avg: {avg_speed:.1f} km/h')
            ax.legend()

        plt.tight_layout()
        return fig

    def _serve_plot(self, fig):
        """Convert matplotlib figure to PNG and serve."""
        img = io.BytesIO()
        fig.savefig(img, format='png', dpi=100, bbox_inches='tight')
        img.seek(0)
        plt.close(fig)  # Free memory

        return send_file(img, mimetype='image/png')

    def run(self, host="0.0.0.0", port=5000, debug=False):
        """
        Run Flask dashboard server.

        Args:
            host: Host to bind to
            port: Port to listen on
            debug: Enable debug mode
        """
        self.telemetry_app.logger.info(f"Starting BMW telemetry dashboard on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)


# HTML Template with BMW Styling
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMW E46 Telemetry Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #F5F5F5;
            color: #1A1A1A;
            padding: 0;
        }

        .header {
            background: linear-gradient(135deg, #1C69D4 0%, #0F4C9C 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .header p {
            font-size: 16px;
            opacity: 0.9;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .live-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .live-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            border: 3px solid #1C69D4;
            border-radius: 10px;
            padding: 20px 15px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(28, 105, 212, 0.3);
            transition: all 0.3s;
        }

        .live-card h3 {
            font-size: 11px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .live-card h1 {
            font-size: 56px;
            color: #1C69D4;
            font-weight: 800;
            margin: 5px 0;
            text-shadow: 0 0 20px rgba(28, 105, 212, 0.5);
        }

        .live-card h2 {
            font-size: 36px;
            color: #1C69D4;
            font-weight: 700;
            margin: 8px 0;
        }

        .live-card p {
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }

        #speed-card {
            grid-column: span 2;
            background: linear-gradient(135deg, #1C69D4 0%, #0F4C9C 100%);
        }

        #speed-card h1 {
            color: white;
            text-shadow: 0 0 30px rgba(255, 255, 255, 0.6);
        }

        #speed-card h3, #speed-card p {
            color: rgba(255, 255, 255, 0.8);
        }

        #drs-card-live.active {
            background: linear-gradient(135deg, #00FF00 0%, #00CC00 100%);
            border-color: #00FF00;
            box-shadow: 0 4px 20px rgba(0, 255, 0, 0.5);
        }

        #drs-card-live.active h2 {
            color: #000;
            font-weight: 900;
        }

        #drs-card-live.active h3 {
            color: #000;
        }

        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: white;
            border: 2px solid #333;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(28, 105, 212, 0.15);
        }

        .metric-card h3 {
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .metric-card h2 {
            font-size: 36px;
            color: #1C69D4;
            font-weight: 700;
        }

        .plot-container {
            background: white;
            padding: 25px;
            margin-bottom: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .plot-container h2 {
            font-size: 20px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #1C69D4;
        }

        .plot-container img {
            width: 100%;
            height: auto;
            border-radius: 4px;
        }

        .controls {
            text-align: center;
            margin: 30px 0;
        }

        .btn {
            background: #1C69D4;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s;
            box-shadow: 0 2px 5px rgba(28, 105, 212, 0.3);
        }

        .btn:hover {
            background: #0F4C9C;
            box-shadow: 0 4px 10px rgba(28, 105, 212, 0.4);
        }

        .status-banner {
            background: #FFD700;
            color: #333;
            padding: 15px;
            text-align: center;
            font-weight: 600;
            margin-bottom: 20px;
            border-radius: 6px;
        }

        {% if not session_complete %}
        .refresh-notice {
            background: #E3F2FD;
            color: #1C69D4;
            padding: 12px;
            text-align: center;
            border-radius: 6px;
            margin-bottom: 20px;
            border-left: 4px solid #1C69D4;
        }
        {% endif %}
    </style>
    <script>
        // Update live telemetry metrics
        function updateLiveMetrics() {
            fetch('/api/live')
                .then(response => response.json())
                .then(data => {
                    // Update values
                    document.getElementById('live-speed').textContent = data.speed_kph || '--';
                    document.getElementById('live-rpm').textContent = data.rpm || '--';
                    document.getElementById('live-coolant').textContent = data.coolant_temp ? data.coolant_temp.toFixed(1) : '--';
                    document.getElementById('live-throttle').textContent = data.throttle ? data.throttle.toFixed(0) : '--';
                    document.getElementById('live-lap').textContent = data.lap || '--';
                    document.getElementById('live-sector').textContent = data.sector || '--';

                    // Update DRS with color coding
                    const drsCard = document.getElementById('drs-card-live');
                    const drsText = document.getElementById('live-drs');
                    if (data.drs_active) {
                        drsCard.classList.add('active');
                        drsText.textContent = 'ACTIVE';
                    } else {
                        drsCard.classList.remove('active');
                        drsText.textContent = 'OFF';
                    }

                    // Update brake status
                    const brakeText = document.getElementById('live-brake');
                    if (data.brake) {
                        brakeText.textContent = 'ON';
                        brakeText.style.color = '#FF4444';
                    } else {
                        brakeText.textContent = 'OFF';
                        brakeText.style.color = '#1C69D4';
                    }
                })
                .catch(err => console.log('Live data fetch error:', err));
        }

        // Update session summary metrics
        function updateSummary() {
            fetch('/api/summary')
                .then(response => response.json())
                .then(data => {
                    // Update summary cards (if elements exist)
                    const bestLapEl = document.querySelector('.metric-card:nth-child(1) h2');
                    const totalLapsEl = document.querySelector('.metric-card:nth-child(2) h2');
                    const drsCountEl = document.querySelector('.metric-card:nth-child(3) h2');
                    const maxSpeedEl = document.querySelector('.metric-card:nth-child(4) h2');

                    if (bestLapEl) bestLapEl.textContent = data.best_lap ? data.best_lap.toFixed(2) + 's' : '--s';
                    if (totalLapsEl) totalLapsEl.textContent = data.total_laps || '0';
                    if (drsCountEl) drsCountEl.textContent = data.drs_count || '0';
                    if (maxSpeedEl) maxSpeedEl.textContent = data.max_speed > 0 ? data.max_speed.toFixed(1) + ' km/h' : '-- km/h';
                })
                .catch(err => console.log('Summary fetch error:', err));
        }

        // Update plot images without page reload
        function updatePlots() {
            const timestamp = new Date().getTime();
            const plots = document.querySelectorAll('.plot-container img');
            plots.forEach(img => {
                const baseSrc = img.src.split('?')[0];
                img.src = baseSrc + '?t=' + timestamp;
            });
        }

        // Update live metrics every 500ms
        setInterval(updateLiveMetrics, 500);

        // Update summary metrics every 2 seconds
        setInterval(updateSummary, 2000);

        {% if not session_complete %}
        // Update plots every 5 seconds while session is running
        setInterval(updatePlots, 5000);
        {% endif %}

        // Initial fetch
        updateLiveMetrics();
        updateSummary();
    </script>
</head>
<body>
    <div class="header">
        <h1>🏁 BMW E46 Telemetry Dashboard</h1>
        <p>Laguna Seca - Race Session Analysis</p>
    </div>

    <div class="container">
        {% if session_complete %}
        <div class="status-banner">
            ✅ Session Complete - Data Locked
        </div>
        {% else %}
        <div class="refresh-notice">
            🔄 Live Session - Auto-refreshing...
        </div>
        {% endif %}

        <!-- Live Telemetry Readout -->
        <div style="margin-bottom: 30px;">
            <h2 style="color: #333; font-size: 22px; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 3px solid #1C69D4;">
                🚗 Live Telemetry
            </h2>
            <div class="live-metrics">
                <div class="live-card" id="speed-card">
                    <h3>SPEED</h3>
                    <h1 id="live-speed">--</h1>
                    <p>km/h</p>
                </div>
                <div class="live-card">
                    <h3>RPM</h3>
                    <h2 id="live-rpm">--</h2>
                </div>
                <div class="live-card" id="drs-card-live">
                    <h3>DRS</h3>
                    <h2 id="live-drs">--</h2>
                </div>
                <div class="live-card">
                    <h3>BRAKE</h3>
                    <h2 id="live-brake">--</h2>
                </div>
                <div class="live-card">
                    <h3>COOLANT</h3>
                    <h2 id="live-coolant">--</h2>
                    <p>°C</p>
                </div>
                <div class="live-card">
                    <h3>THROTTLE</h3>
                    <h2 id="live-throttle">--</h2>
                    <p>%</p>
                </div>
                <div class="live-card">
                    <h3>CURRENT LAP</h3>
                    <h2 id="live-lap">--</h2>
                </div>
                <div class="live-card">
                    <h3>SECTOR</h3>
                    <h2 id="live-sector">--</h2>
                </div>
            </div>
        </div>

        <!-- Session Summary -->
        <h2 style="color: #333; font-size: 22px; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 3px solid #1C69D4;">
            📊 Session Summary
        </h2>
        <div class="metrics">
            <div class="metric-card">
                <h3>Best Lap Time</h3>
                <h2>{{ best_lap }}s</h2>
            </div>
            <div class="metric-card">
                <h3>Total Laps</h3>
                <h2>{{ total_laps }}</h2>
            </div>
            <div class="metric-card">
                <h3>DRS Activations</h3>
                <h2>{{ drs_count }}</h2>
            </div>
            <div class="metric-card">
                <h3>Max Speed</h3>
                <h2>{{ max_speed }} km/h</h2>
            </div>
        </div>

        <div class="plot-container">
            <h2>Speed Trace - All Laps</h2>
            <img src="/plots/speed_trace.png?t={{ timestamp }}" alt="Speed Trace">
        </div>

        <div class="plot-container">
            <h2>Lap Times Comparison</h2>
            <img src="/plots/lap_times.png?t={{ timestamp }}" alt="Lap Times">
        </div>

        <div class="plot-container">
            <h2>Sector Speed Analysis</h2>
            <img src="/plots/sector_heatmap.png?t={{ timestamp }}" alt="Sector Heatmap">
        </div>

        <div class="plot-container">
            <h2>DRS Effectiveness</h2>
            <img src="/plots/drs_analysis.png?t={{ timestamp }}" alt="DRS Analysis">
        </div>

        <div class="controls">
            <a href="/export/csv" class="btn">📥 Download CSV Data</a>
        </div>
    </div>
</body>
</html>
"""
