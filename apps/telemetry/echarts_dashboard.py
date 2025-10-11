"""Professional BMW E46 telemetry dashboard using Apache ECharts for interactive charts.

This dashboard uses ECharts (client-side JavaScript) for interactive, Grafana-style charts:
- Smooth pan/zoom interaction (drag to pan, scroll to zoom)
- Data zoom sliders for time-series analysis
- Professional racing telemetry visualization
- BMW blue/white/gray color scheme
- Live telemetry metrics + historical analysis
"""

import threading
from typing import TYPE_CHECKING, Dict, List
from datetime import datetime

import pandas as pd
from flask import Flask, render_template_string, jsonify, Response

if TYPE_CHECKING:
    from apps.telemetry.main import TelemetryApp


# BMW Color Palette
BMW_BLUE = '#1C69D4'
BMW_GRAY = '#333333'
BMW_LIGHT_GRAY = '#F5F5F5'
BMW_WHITE = '#FFFFFF'
BMW_GOLD = '#FFD700'
BMW_GREEN = '#00FF00'


class SessionData:
    """Continuous telemetry storage with manual lap marking."""

    def __init__(self):
        self.telemetry = []  # Continuous list of telemetry samples
        self.lap_markers = []  # List of {timestamp, lap_num, note}
        self.session_start = None  # First sample timestamp
        self.session_complete = False
        self.lock = threading.Lock()
        self.live_data = {}  # Most recent telemetry sample for live display

    def add_telemetry_sample(self, sample: Dict):
        """
        Add telemetry sample to continuous buffer.

        Args:
            sample: Dict with keys: timestamp, speed_kph, rpm, coolant_temp, throttle, drs_active, brake
        """
        with self.lock:
            if self.session_complete:
                return

            # Set session start on first sample
            if self.session_start is None:
                self.session_start = sample.get('timestamp', 0)

            # Add elapsed time for easier plotting
            sample['elapsed'] = sample.get('timestamp', 0) - (self.session_start or 0)

            # Determine current lap based on markers
            current_lap = len(self.lap_markers) + 1
            sample['lap'] = current_lap

            self.telemetry.append(sample)
            self.live_data = sample

    def mark_lap(self, timestamp: float = None, note: str = ""):
        """
        Mark a lap completion point.

        Args:
            timestamp: Timestamp of lap marker (defaults to most recent sample)
            note: Optional note for this lap

        Returns:
            Dict with lap_num and timestamp
        """
        with self.lock:
            if not self.telemetry:
                return {"error": "No telemetry data yet"}

            # Use most recent sample timestamp if not provided
            if timestamp is None:
                timestamp = self.telemetry[-1].get('timestamp', 0)

            lap_num = len(self.lap_markers) + 1
            marker = {
                "lap_num": lap_num,
                "timestamp": timestamp,
                "elapsed": timestamp - (self.session_start or 0),
                "note": note,
            }
            self.lap_markers.append(marker)

            print(f"[SessionData] Lap {lap_num} marked at {timestamp:.2f}s (elapsed: {marker['elapsed']:.2f}s)")
            return marker

    def get_live_data(self) -> Dict:
        """Get most recent live telemetry data."""
        with self.lock:
            return self.live_data.copy() if self.live_data else {}

    def mark_complete(self):
        """Mark session as complete - stop accepting new data."""
        with self.lock:
            self.session_complete = True

    def get_telemetry_range(self, start_time: float = None, end_time: float = None, lap_num: int = None) -> List[Dict]:
        """
        Get telemetry samples for a time range or specific lap.

        Args:
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            lap_num: Get samples for specific lap number

        Returns:
            List of telemetry samples
        """
        with self.lock:
            if lap_num is not None:
                # Get samples for specific lap
                return [s for s in self.telemetry if s.get('lap') == lap_num]

            if start_time is None and end_time is None:
                # Return all data
                return self.telemetry.copy()

            # Filter by time range
            filtered = []
            for sample in self.telemetry:
                ts = sample.get('timestamp', 0)
                if start_time is not None and ts < start_time:
                    continue
                if end_time is not None and ts > end_time:
                    continue
                filtered.append(sample)
            return filtered

    def get_summary(self) -> Dict:
        """Get session summary statistics."""
        with self.lock:
            if not self.telemetry:
                return {
                    "duration": 0,
                    "total_samples": 0,
                    "total_laps": 0,
                    "max_speed": 0,
                    "drs_activations": 0,
                }

            # Calculate DRS activations by looking at state changes
            drs_count = 0
            for i in range(1, len(self.telemetry)):
                if self.telemetry[i].get('drs_active') and not self.telemetry[i-1].get('drs_active'):
                    drs_count += 1

            speeds = [s.get('speed_kph', 0) for s in self.telemetry]
            duration = self.telemetry[-1].get('elapsed', 0) if self.telemetry else 0

            return {
                "duration": round(duration, 1),
                "total_samples": len(self.telemetry),
                "total_laps": len(self.lap_markers),
                "max_speed": round(max(speeds) if speeds else 0, 1),
                "drs_activations": drs_count,
            }


class TelemetryDashboard:
    """Flask-based dashboard with ECharts interactive visualizations."""

    def __init__(self, telemetry_app: "TelemetryApp"):
        """Initialize dashboard."""
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
            return render_template_string(DASHBOARD_HTML)

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

        @self.app.route("/api/mark_lap", methods=["POST"])
        def mark_lap():
            """Mark a lap completion point."""
            from flask import request
            data = request.get_json() or {}
            note = data.get("note", "")

            result = self.session_data.mark_lap(note=note)
            return jsonify(result)

        @self.app.route("/api/laps")
        def get_laps():
            """Get list of lap markers."""
            return jsonify({
                "laps": self.session_data.lap_markers
            })

        @self.app.route("/api/chart/timeseries")
        def chart_timeseries():
            """Get time-series telemetry data for charting."""
            from flask import request

            # Get query parameters
            lap_num = request.args.get("lap", type=int)
            start_time = request.args.get("start_time", type=float)
            end_time = request.args.get("end_time", type=float)

            # Get telemetry range
            samples = self.session_data.get_telemetry_range(
                start_time=start_time,
                end_time=end_time,
                lap_num=lap_num
            )

            if not samples:
                return jsonify({
                    "elapsed": [],
                    "speed": [],
                    "rpm": [],
                    "coolant": [],
                    "throttle": [],
                    "drs_regions": [],
                    "lap_markers": []
                })

            # Extract data arrays
            elapsed = [s.get('elapsed', 0) for s in samples]
            speed = [s.get('speed_kph', 0) for s in samples]
            rpm = [s.get('rpm', 0) for s in samples]
            coolant = [s.get('coolant_temp', 0) for s in samples]
            throttle = [s.get('throttle', 0) for s in samples]

            # Find DRS active regions
            drs_regions = []
            drs_start = None
            for i, s in enumerate(samples):
                if s.get('drs_active'):
                    if drs_start is None:
                        drs_start = s.get('elapsed', 0)
                else:
                    if drs_start is not None:
                        drs_regions.append([drs_start, samples[i-1].get('elapsed', 0)])
                        drs_start = None

            # Close final DRS region if still active
            if drs_start is not None and samples:
                drs_regions.append([drs_start, samples[-1].get('elapsed', 0)])

            # Get lap markers in range
            markers_in_range = []
            for marker in self.session_data.lap_markers:
                marker_elapsed = marker.get('elapsed', 0)
                if start_time is not None and marker.get('timestamp', 0) < start_time:
                    continue
                if end_time is not None and marker.get('timestamp', 0) > end_time:
                    continue
                markers_in_range.append(marker_elapsed)

            return jsonify({
                "elapsed": elapsed,
                "speed": speed,
                "rpm": rpm,
                "coolant": coolant,
                "throttle": throttle,
                "drs_regions": drs_regions,
                "lap_markers": markers_in_range
            })

        @self.app.route("/export/csv")
        def export_csv():
            """Export all telemetry data as CSV with lap markers."""
            if not self.session_data.telemetry:
                return "No data available", 404

            # Build CSV with telemetry + lap marker rows
            lines = ["timestamp,elapsed_seconds,speed_kph,rpm,coolant_temp,throttle_pct,drs_active,brake,lap"]

            for sample in self.session_data.telemetry:
                lines.append(
                    f"{sample.get('timestamp', 0):.3f},"
                    f"{sample.get('elapsed', 0):.2f},"
                    f"{sample.get('speed_kph', 0):.1f},"
                    f"{sample.get('rpm', 0):.0f},"
                    f"{sample.get('coolant_temp', 0):.1f},"
                    f"{sample.get('throttle', 0):.1f},"
                    f"{sample.get('drs_active', False)},"
                    f"{sample.get('brake', False)},"
                    f"{sample.get('lap', 1)}"
                )

                # Insert lap marker comment after the marker timestamp
                for marker in self.session_data.lap_markers:
                    if abs(marker['timestamp'] - sample.get('timestamp', 0)) < 0.001:
                        note = f" - {marker['note']}" if marker['note'] else ""
                        lines.append(f"# LAP MARKER: Lap {marker['lap_num']} Complete - {marker['elapsed']:.2f}s{note}")

            csv_data = "\n".join(lines)

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=telemetry_session.csv"}
            )

    def run(self, host="0.0.0.0", port=5000, debug=False):
        """Run Flask server."""
        self.app.run(host=host, port=port, debug=debug, threaded=True)




# HTML Template with ECharts - Time Series Dashboard
DASHBOARD_HTML = """<html><head><meta charset="UTF-8"><title>Telemetry Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#f5f5f5;color:#333;padding:20px}
.header{background:#1C69D4;color:white;padding:20px;border-radius:8px;margin-bottom:20px;display:flex;justify-content:space-between}
.header h1{font-size:28px}
.header-info{text-align:right;font-size:14px}
.controls{background:white;padding:15px 20px;border-radius:8px;margin-bottom:20px;display:flex;gap:15px;border:2px solid #e0e0e0}
.btn{background:#1C69D4;color:white;border:none;padding:10px 20px;border-radius:4px;cursor:pointer}
select{padding:8px 12px;border:2px solid #e0e0e0;border-radius:4px;background:white}
.live-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:20px}
.metric-card{background:white;padding:20px;border-radius:8px;border:2px solid #e0e0e0}
.metric-card.active-drs{border-color:#00FF00;background:#f0fff0}
.metric-card.active-brake{border-color:#ff0000;background:#fff0f0}
.metric-label{font-size:12px;color:#666;text-transform:uppercase;margin-bottom:8px}
.metric-value{font-size:32px;font-weight:700;color:#1C69D4}
.metric-unit{font-size:16px;color:#999;margin-left:4px}
.charts-container{display:flex;flex-direction:column;gap:20px}
.chart-card{background:white;padding:20px;border-radius:8px;border:2px solid #e0e0e0}
.chart-title{font-size:18px;font-weight:600;margin-bottom:15px}
.chart{width:100%;height:300px}
.export-link{display:inline-block;padding:10px 20px;background:#333;color:white;text-decoration:none;border-radius:4px}
</style></head><body>
<div class="header"><h1>Telemetry Dashboard</h1>
<div class="header-info">
<div>Session Duration: <span id="session-duration">0.0s</span></div>
<div>Total Samples: <span id="total-samples">0</span></div>
</div></div>
<div class="controls">
<button class="btn" onclick="markLap()">Mark Lap</button>
<select id="lap-selector" onchange="loadLapData()"><option value="all">All Data</option></select>
<a href="/export/csv" class="export-link">Export CSV</a>
</div>
<div class="live-metrics">
<div class="metric-card" id="speed-card"><div class="metric-label">Speed</div><div class="metric-value"><span id="live-speed">0.0</span><span class="metric-unit">km/h</span></div></div>
<div class="metric-card" id="rpm-card"><div class="metric-label">RPM</div><div class="metric-value"><span id="live-rpm">0</span><span class="metric-unit">rpm</span></div></div>
<div class="metric-card" id="drs-card"><div class="metric-label">DRS</div><div class="metric-value"><span id="live-drs">INACTIVE</span></div></div>
<div class="metric-card" id="brake-card"><div class="metric-label">Brake</div><div class="metric-value"><span id="live-brake">OFF</span></div></div>
<div class="metric-card" id="coolant-card"><div class="metric-label">Coolant Temp</div><div class="metric-value"><span id="live-coolant">0.0</span><span class="metric-unit">°C</span></div></div>
<div class="metric-card" id="throttle-card"><div class="metric-label">Throttle</div><div class="metric-value"><span id="live-throttle">0.0</span><span class="metric-unit">%</span></div></div>
</div>
<div class="charts-container">
<div class="chart-card"><div class="chart-title">Speed</div><div id="speed-chart" class="chart"></div></div>
<div class="chart-card"><div class="chart-title">RPM</div><div id="rpm-chart" class="chart"></div></div>
<div class="chart-card"><div class="chart-title">Coolant Temperature</div><div id="coolant-chart" class="chart"></div></div>
<div class="chart-card"><div class="chart-title">Throttle Position</div><div id="throttle-chart" class="chart"></div></div>
</div>
<script>
let speedChart=echarts.init(document.getElementById('speed-chart'));
let rpmChart=echarts.init(document.getElementById('rpm-chart'));
let coolantChart=echarts.init(document.getElementById('coolant-chart'));
let throttleChart=echarts.init(document.getElementById('throttle-chart'));
echarts.connect([speedChart,rpmChart,coolantChart,throttleChart]);
let chartsInitialized=false;
function getInitOptions(t,y,minY,maxY){return{grid:{left:60,right:60,top:40,bottom:80},tooltip:{trigger:'axis'},toolbox:{feature:{dataZoom:{},restore:{},saveAsImage:{}}},xAxis:{type:'value',name:'Elapsed Time (s)',nameLocation:'middle',nameGap:30},yAxis:{type:'value',name:y,min:minY,max:maxY},dataZoom:[{type:'inside',xAxisIndex:0},{type:'slider',xAxisIndex:0}],series:[]}}
function getUpdateOptions(t,y,minY,maxY){return{yAxis:{min:minY,max:maxY},series:[]}}
function markLap(){fetch('/api/mark_lap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})}).then(r=>r.json()).then(d=>{if(d.error)alert(d.error);else{updateLapSelector();loadLapData()}})}
function updateLapSelector(){fetch('/api/laps').then(r=>r.json()).then(d=>{const s=document.getElementById('lap-selector');const c=s.value;s.innerHTML='<option value="all">All Data</option>';d.laps.forEach(lap=>{const o=document.createElement('option');o.value=lap.lap_num;o.textContent='Lap '+lap.lap_num;s.appendChild(o)});if(c!='all')s.value=c})}
function loadLapData(){const s=document.getElementById('lap-selector');const l=s.value=='all'?null:s.value;let u='/api/chart/timeseries';if(l)u+='?lap='+l;fetch(u).then(r=>r.json()).then(d=>updateCharts(d))}
function updateCharts(d){const drs=d.drs_regions.map(r=>[{xAxis:r[0],itemStyle:{color:'rgba(0,255,0,0.1)'}},{xAxis:r[1]}]);const laps=d.lap_markers.map(e=>({xAxis:e,lineStyle:{color:'#FFD700',width:2}}));if(!chartsInitialized){const so=getInitOptions('Speed','Speed (km/h)',0,'dataMax');so.series=[{name:'Speed',type:'line',data:d.elapsed.map((t,i)=>[t,d.speed[i]]),smooth:true,symbol:'none',lineStyle:{color:'#1C69D4',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];speedChart.setOption(so,true);const ro=getInitOptions('RPM','RPM',0,'dataMax');ro.series=[{name:'RPM',type:'line',data:d.elapsed.map((t,i)=>[t,d.rpm[i]]),smooth:true,symbol:'none',lineStyle:{color:'#FF6B6B',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];rpmChart.setOption(ro,true);const co=getInitOptions('Coolant','Coolant (°C)','dataMin','dataMax');co.series=[{name:'Coolant',type:'line',data:d.elapsed.map((t,i)=>[t,d.coolant[i]]),smooth:true,symbol:'none',lineStyle:{color:'#FF8C42',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];coolantChart.setOption(co,true);const to=getInitOptions('Throttle','Throttle (%)',0,100);to.series=[{name:'Throttle',type:'line',data:d.elapsed.map((t,i)=>[t,d.throttle[i]]),smooth:true,symbol:'none',lineStyle:{color:'#4ECDC4',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];throttleChart.setOption(to,true);chartsInitialized=true}else{const so=getUpdateOptions('Speed','Speed (km/h)',0,'dataMax');so.series=[{name:'Speed',type:'line',data:d.elapsed.map((t,i)=>[t,d.speed[i]]),smooth:true,symbol:'none',lineStyle:{color:'#1C69D4',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];speedChart.setOption(so);const ro=getUpdateOptions('RPM','RPM',0,'dataMax');ro.series=[{name:'RPM',type:'line',data:d.elapsed.map((t,i)=>[t,d.rpm[i]]),smooth:true,symbol:'none',lineStyle:{color:'#FF6B6B',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];rpmChart.setOption(ro);const co=getUpdateOptions('Coolant','Coolant (°C)','dataMin','dataMax');co.series=[{name:'Coolant',type:'line',data:d.elapsed.map((t,i)=>[t,d.coolant[i]]),smooth:true,symbol:'none',lineStyle:{color:'#FF8C42',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];coolantChart.setOption(co);const to=getUpdateOptions('Throttle','Throttle (%)',0,100);to.series=[{name:'Throttle',type:'line',data:d.elapsed.map((t,i)=>[t,d.throttle[i]]),smooth:true,symbol:'none',lineStyle:{color:'#4ECDC4',width:2},markArea:{data:drs},markLine:{data:laps,symbol:'none'}}];throttleChart.setOption(to)}}
function updateLiveMetrics(){fetch('/api/live').then(r=>r.json()).then(d=>{document.getElementById('live-speed').textContent=d.speed_kph.toFixed(1);document.getElementById('live-rpm').textContent=d.rpm;document.getElementById('live-coolant').textContent=d.coolant_temp.toFixed(1);document.getElementById('live-throttle').textContent=d.throttle.toFixed(1);const dc=document.getElementById('drs-card');const dv=document.getElementById('live-drs');if(d.drs_active){dc.classList.add('active-drs');dv.textContent='ACTIVE';dv.style.color='#00FF00'}else{dc.classList.remove('active-drs');dv.textContent='INACTIVE';dv.style.color='#999'}const bc=document.getElementById('brake-card');const bv=document.getElementById('live-brake');if(d.brake){bc.classList.add('active-brake');bv.textContent='ON';bv.style.color='#FF0000'}else{bc.classList.remove('active-brake');bv.textContent='OFF';bv.style.color='#999'}})}
function updateSummary(){fetch('/api/summary').then(r=>r.json()).then(d=>{document.getElementById('session-duration').textContent=d.duration.toFixed(1)+'s';document.getElementById('total-samples').textContent=d.total_samples})}
updateLapSelector();loadLapData();updateLiveMetrics();updateSummary();
setInterval(updateLiveMetrics,500);setInterval(updateSummary,2000);setInterval(loadLapData,500);setInterval(updateLapSelector,2000);
window.addEventListener('resize',()=>{speedChart.resize();rpmChart.resize();coolantChart.resize();throttleChart.resize()});
</script></body></html>
"""
