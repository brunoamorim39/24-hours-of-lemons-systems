"""Professional telemetry dashboard using Plotly Dash for interactive data analysis.

This dashboard provides high-quality interactive charts for analyzing race telemetry data,
similar to what professional racing teams use. Features include:
- Zoomable/pannable speed traces
- Lap-by-lap comparison
- Sector analysis
- DRS effectiveness tracking
- Full session data retention
- CSV export capabilities
"""

from pathlib import Path
from typing import TYPE_CHECKING, List, Dict
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

if TYPE_CHECKING:
    from apps.telemetry.main import TelemetryApp


class TelemetryDashboard:
    """Interactive Plotly Dash dashboard for race telemetry analysis."""

    def __init__(self, telemetry_app: "TelemetryApp"):
        """
        Initialize telemetry dashboard.

        Args:
            telemetry_app: TelemetryApp instance to query for data
        """
        self.telemetry_app = telemetry_app
        self.session_data = []  # Store full session telemetry data

        # Create Dash app
        self.app = dash.Dash(
            __name__,
            title="24 Hours of Lemons - Telemetry",
            update_title=None,  # Don't show "Updating..." in title
        )

        # Setup layout and callbacks
        self.app.layout = self._create_layout()
        self._setup_callbacks()

    def _create_layout(self):
        """Create dashboard layout."""
        return html.Div(
            [
                # Header
                html.Div(
                    [
                        html.H1(
                            "🏁 24 HOURS OF LEMONS - TELEMETRY ANALYSIS",
                            style={
                                "textAlign": "center",
                                "color": "#0f0",
                                "fontFamily": "Courier New, monospace",
                                "backgroundColor": "#1a1a1a",
                                "padding": "20px",
                                "border": "2px solid #0f0",
                                "marginBottom": "20px",
                            },
                        ),
                    ]
                ),
                # Live metrics row
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3("Speed", style={"color": "#888"}),
                                html.H2(
                                    id="live-speed",
                                    children="-- km/h",
                                    style={"color": "#0f0"},
                                ),
                            ],
                            style={
                                "textAlign": "center",
                                "backgroundColor": "#1a1a1a",
                                "padding": "15px",
                                "border": "2px solid #0f0",
                                "borderRadius": "5px",
                            },
                        ),
                        html.Div(
                            [
                                html.H3("RPM", style={"color": "#888"}),
                                html.H2(id="live-rpm", children="--", style={"color": "#0f0"}),
                            ],
                            style={
                                "textAlign": "center",
                                "backgroundColor": "#1a1a1a",
                                "padding": "15px",
                                "border": "2px solid #0f0",
                                "borderRadius": "5px",
                            },
                        ),
                        html.Div(
                            [
                                html.H3("DRS", style={"color": "#888"}),
                                html.H2(id="live-drs", children="--", style={"color": "#888"}),
                            ],
                            id="drs-card",
                            style={
                                "textAlign": "center",
                                "backgroundColor": "#1a1a1a",
                                "padding": "15px",
                                "border": "2px solid #888",
                                "borderRadius": "5px",
                            },
                        ),
                        html.Div(
                            [
                                html.H3("Coolant", style={"color": "#888"}),
                                html.H2(id="live-temp", children="-- °C", style={"color": "#0f0"}),
                            ],
                            style={
                                "textAlign": "center",
                                "backgroundColor": "#1a1a1a",
                                "padding": "15px",
                                "border": "2px solid #0f0",
                                "borderRadius": "5px",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "repeat(4, 1fr)",
                        "gap": "15px",
                        "marginBottom": "20px",
                    },
                ),
                # Controls row
                html.Div(
                    [
                        html.Label(
                            "Select Laps:",
                            style={"color": "#0f0", "marginRight": "10px"},
                        ),
                        dcc.Dropdown(
                            id="lap-selector",
                            multi=True,
                            placeholder="Select laps to compare...",
                            style={
                                "width": "300px",
                                "backgroundColor": "#1a1a1a",
                                "color": "#0f0",
                            },
                        ),
                        html.Button(
                            "Export CSV",
                            id="export-btn",
                            style={
                                "marginLeft": "20px",
                                "backgroundColor": "#0f0",
                                "color": "#000",
                                "border": "none",
                                "padding": "10px 20px",
                                "cursor": "pointer",
                                "fontWeight": "bold",
                            },
                        ),
                        dcc.Download(id="download-data"),
                    ],
                    style={"marginBottom": "20px", "display": "flex", "alignItems": "center"},
                ),
                # Main speed trace chart
                dcc.Graph(id="speed-trace", config={"scrollZoom": True}),
                # Second row: Lap times and sector analysis
                html.Div(
                    [
                        html.Div(
                            [dcc.Graph(id="lap-times")],
                            style={"width": "48%"},
                        ),
                        html.Div(
                            [dcc.Graph(id="sector-analysis")],
                            style={"width": "48%"},
                        ),
                    ],
                    style={"display": "flex", "justifyContent": "space-between"},
                ),
                # Engine telemetry
                dcc.Graph(id="engine-telemetry"),
                # DRS analysis
                dcc.Graph(id="drs-analysis"),
                # Auto-refresh interval for live data
                dcc.Interval(id="interval-component", interval=500, n_intervals=0),  # 500ms
                # Hidden div to store session data
                dcc.Store(id="session-store"),
            ],
            style={"backgroundColor": "#0a0a0a", "padding": "20px", "fontFamily": "monospace"},
        )

    def _setup_callbacks(self):
        """Setup Dash callbacks for interactivity."""

        @self.app.callback(
            [
                Output("live-speed", "children"),
                Output("live-rpm", "children"),
                Output("live-drs", "children"),
                Output("live-temp", "children"),
                Output("drs-card", "style"),
                Output("lap-selector", "options"),
                Output("lap-selector", "value"),
            ],
            [Input("interval-component", "n_intervals")],
            [State("lap-selector", "value")],
        )
        def update_live_metrics(n, current_selection):
            """Update live metrics and lap selector."""
            # Get latest telemetry
            data = self.telemetry_app.get_telemetry_data()

            # Store in session data
            if data.get("obd"):
                self.session_data.append(
                    {
                        "timestamp": data.get("timestamp", 0),
                        "speed": data["obd"].get("SPEED", 0),
                        "rpm": data["obd"].get("RPM", 0),
                        "coolant_temp": data["obd"].get("COOLANT_TEMP", 0),
                        "throttle": data["obd"].get("THROTTLE_POS", 0),
                        "engine_load": data["obd"].get("ENGINE_LOAD", 0),
                        "drs_active": data.get("custom", {}).get("drs", {}).get("active", False),
                    }
                )

            # Update live metrics
            speed = f"{data.get('obd', {}).get('SPEED', 0):.1f} km/h"
            rpm = f"{data.get('obd', {}).get('RPM', 0):.0f}"
            temp = f"{data.get('obd', {}).get('COOLANT_TEMP', 0):.1f} °C"

            drs_active = data.get("custom", {}).get("drs", {}).get("active", False)
            drs_text = "ACTIVE" if drs_active else "IDLE"
            drs_style = {
                "textAlign": "center",
                "backgroundColor": "#2a2a00" if drs_active else "#1a1a1a",
                "padding": "15px",
                "border": f"2px solid {'#ff0' if drs_active else '#888'}",
                "borderRadius": "5px",
                "boxShadow": "0 0 20px #ff0" if drs_active else "none",
            }

            # Get available laps (placeholder - will come from simulation)
            lap_options = []  # Will be populated by simulation data

            return speed, rpm, drs_text, temp, drs_style, lap_options, current_selection

        @self.app.callback(
            Output("speed-trace", "figure"),
            [Input("lap-selector", "value"), Input("interval-component", "n_intervals")],
        )
        def update_speed_trace(selected_laps, n):
            """Update speed trace chart."""
            fig = go.Figure()

            if not self.session_data:
                fig.add_annotation(
                    text="Waiting for telemetry data...",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font={"size": 20, "color": "#0f0"},
                )
            else:
                # Plot recent data (last 2 minutes)
                df = pd.DataFrame(self.session_data[-240:])  # 240 samples at 2Hz

                fig.add_trace(
                    go.Scatter(
                        x=list(range(len(df))),
                        y=df["speed"],
                        name="Speed",
                        mode="lines",
                        line={"color": "#0f0", "width": 2},
                        hovertemplate="<b>%{y:.1f} km/h</b><extra></extra>",
                    )
                )

                # Highlight DRS activations
                drs_active = df["drs_active"].values
                for i in range(1, len(drs_active)):
                    if drs_active[i] and not drs_active[i - 1]:
                        # DRS activated
                        fig.add_vline(
                            x=i, line_color="#ff0", line_width=1, line_dash="dash", opacity=0.5
                        )

            fig.update_layout(
                title={
                    "text": "Live Speed Trace (Last 2 Minutes)",
                    "font": {"color": "#0f0", "size": 20},
                },
                xaxis_title="Time",
                yaxis_title="Speed (km/h)",
                plot_bgcolor="#0a0a0a",
                paper_bgcolor="#1a1a1a",
                font={"color": "#0f0"},
                xaxis={"gridcolor": "#333"},
                yaxis={"gridcolor": "#333"},
                height=500,
                hovermode="x unified",
            )

            return fig

        @self.app.callback(
            Output("lap-times", "figure"), [Input("interval-component", "n_intervals")]
        )
        def update_lap_times(n):
            """Update lap times bar chart."""
            fig = go.Figure()

            # Placeholder - will be populated with actual lap data
            fig.add_annotation(
                text="Lap data will appear after first lap completes",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 14, "color": "#888"},
            )

            fig.update_layout(
                title={"text": "Lap Times", "font": {"color": "#0f0"}},
                plot_bgcolor="#0a0a0a",
                paper_bgcolor="#1a1a1a",
                font={"color": "#0f0"},
                height=300,
            )

            return fig

        @self.app.callback(
            Output("sector-analysis", "figure"), [Input("interval-component", "n_intervals")]
        )
        def update_sector_analysis(n):
            """Update sector analysis chart."""
            fig = go.Figure()

            # Placeholder
            fig.add_annotation(
                text="Sector analysis will appear after sectors are defined",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 14, "color": "#888"},
            )

            fig.update_layout(
                title={"text": "Sector Analysis", "font": {"color": "#0f0"}},
                plot_bgcolor="#0a0a0a",
                paper_bgcolor="#1a1a1a",
                font={"color": "#0f0"},
                height=300,
            )

            return fig

        @self.app.callback(
            Output("engine-telemetry", "figure"), [Input("interval-component", "n_intervals")]
        )
        def update_engine_telemetry(n):
            """Update engine telemetry trends."""
            fig = make_subplots(
                rows=2,
                cols=1,
                subplot_titles=("Coolant Temperature", "Engine Load"),
                vertical_spacing=0.15,
            )

            if self.session_data:
                df = pd.DataFrame(self.session_data)

                # Coolant temp
                fig.add_trace(
                    go.Scatter(
                        x=list(range(len(df))),
                        y=df["coolant_temp"],
                        name="Coolant Temp",
                        line={"color": "#f80"},
                        hovertemplate="<b>%{y:.1f} °C</b><extra></extra>",
                    ),
                    row=1,
                    col=1,
                )

                # Engine load
                fig.add_trace(
                    go.Scatter(
                        x=list(range(len(df))),
                        y=df["engine_load"],
                        name="Engine Load",
                        line={"color": "#0af"},
                        hovertemplate="<b>%{y:.1f}%</b><extra></extra>",
                    ),
                    row=2,
                    col=1,
                )

            fig.update_layout(
                title={"text": "Engine Telemetry (Full Session)", "font": {"color": "#0f0"}},
                plot_bgcolor="#0a0a0a",
                paper_bgcolor="#1a1a1a",
                font={"color": "#0f0"},
                showlegend=False,
                height=500,
            )

            fig.update_xaxes(gridcolor="#333")
            fig.update_yaxes(gridcolor="#333")

            return fig

        @self.app.callback(
            Output("drs-analysis", "figure"), [Input("interval-component", "n_intervals")]
        )
        def update_drs_analysis(n):
            """Update DRS effectiveness analysis."""
            fig = go.Figure()

            # Placeholder
            fig.add_annotation(
                text="DRS analysis will show speed gain and optimal activation points",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 14, "color": "#888"},
            )

            fig.update_layout(
                title={"text": "DRS Effectiveness", "font": {"color": "#0f0"}},
                plot_bgcolor="#0a0a0a",
                paper_bgcolor="#1a1a1a",
                font={"color": "#0f0"},
                height=400,
            )

            return fig

        @self.app.callback(
            Output("download-data", "data"),
            [Input("export-btn", "n_clicks")],
            prevent_initial_call=True,
        )
        def export_csv(n_clicks):
            """Export session data to CSV."""
            if self.session_data:
                df = pd.DataFrame(self.session_data)
                return dcc.send_data_frame(df.to_csv, "telemetry_data.csv", index=False)
            return None

    def run(self, host="0.0.0.0", port=5000, debug=False):
        """
        Run the Dash dashboard server.

        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
        """
        self.telemetry_app.logger.info(f"Starting Plotly dashboard on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)
