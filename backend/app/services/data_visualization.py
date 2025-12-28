"""Data Visualization Service for generating interactive chart data."""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import re
import math


class ChartType(str, Enum):
    """Supported chart types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    DOUGHNUT = "doughnut"
    AREA = "area"
    SCATTER = "scatter"
    RADAR = "radar"
    BUBBLE = "bubble"
    POLAR = "polar"
    TREEMAP = "treemap"


@dataclass
class ChartDataset:
    """A dataset for chart visualization."""
    label: str
    data: List[Union[int, float]]
    backgroundColor: Optional[List[str]] = None
    borderColor: Optional[str] = None
    borderWidth: int = 2
    fill: bool = False
    tension: float = 0.4  # For smooth curves


@dataclass
class ChartConfig:
    """Complete chart configuration for frontend."""
    type: ChartType
    labels: List[str]
    datasets: List[ChartDataset]
    title: str = ""
    subtitle: str = ""
    options: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        return {
            'type': self.type.value,
            'data': {
                'labels': self.labels,
                'datasets': [asdict(ds) for ds in self.datasets]
            },
            'options': self.options or self._default_options(),
            'title': self.title,
            'subtitle': self.subtitle
        }

    def _default_options(self) -> Dict:
        return {
            'responsive': True,
            'maintainAspectRatio': True,
            'animation': {
                'duration': 1000,
                'easing': 'easeOutQuart'
            },
            'plugins': {
                'legend': {
                    'display': True,
                    'position': 'bottom'
                },
                'tooltip': {
                    'enabled': True,
                    'mode': 'index',
                    'intersect': False
                }
            }
        }


class DataVisualizationService:
    """
    Generate beautiful, animated chart configurations for the frontend.

    Outputs Chart.js compatible configurations with professional styling.
    """

    # Professional color palettes
    PALETTES = {
        'default': [
            '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#FF6B6B', '#C44D58', '#556270'
        ],
        'ocean': [
            '#0077B6', '#00B4D8', '#90E0EF', '#CAF0F8',
            '#03045E', '#023E8A', '#0096C7', '#48CAE4'
        ],
        'sunset': [
            '#F72585', '#B5179E', '#7209B7', '#560BAD',
            '#480CA8', '#3A0CA3', '#3F37C9', '#4361EE'
        ],
        'forest': [
            '#2D6A4F', '#40916C', '#52B788', '#74C69D',
            '#95D5B2', '#B7E4C7', '#D8F3DC', '#1B4332'
        ],
        'warm': [
            '#FF6B35', '#F7C59F', '#EFEFD0', '#004E89',
            '#1A659E', '#FF9F1C', '#FFBF69', '#CBF3F0'
        ]
    }

    # Gradient configurations for area charts
    GRADIENTS = {
        'blue': {'start': 'rgba(69, 183, 209, 0.4)', 'end': 'rgba(69, 183, 209, 0.0)'},
        'teal': {'start': 'rgba(78, 205, 196, 0.4)', 'end': 'rgba(78, 205, 196, 0.0)'},
        'purple': {'start': 'rgba(114, 9, 183, 0.4)', 'end': 'rgba(114, 9, 183, 0.0)'},
        'orange': {'start': 'rgba(255, 107, 53, 0.4)', 'end': 'rgba(255, 107, 53, 0.0)'},
    }

    def __init__(self):
        self.default_palette = self.PALETTES['default']

    def create_line_chart(
        self,
        labels: List[str],
        datasets: List[Dict[str, Any]],
        title: str = "",
        smooth: bool = True,
        show_area: bool = False
    ) -> ChartConfig:
        """Create a line chart configuration."""
        chart_datasets = []

        for i, ds in enumerate(datasets):
            color = ds.get('color') or self.default_palette[i % len(self.default_palette)]
            chart_datasets.append(ChartDataset(
                label=ds.get('label', f'Series {i+1}'),
                data=ds.get('data', []),
                borderColor=color,
                backgroundColor=color.replace(')', ', 0.1)').replace('rgb', 'rgba') if 'rgb' in color else color + '1A',
                fill=show_area,
                tension=0.4 if smooth else 0
            ))

        return ChartConfig(
            type=ChartType.LINE,
            labels=labels,
            datasets=chart_datasets,
            title=title,
            options={
                'responsive': True,
                'interaction': {'mode': 'index', 'intersect': False},
                'animation': {
                    'duration': 1500,
                    'easing': 'easeOutQuart'
                },
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'grid': {'color': 'rgba(0, 0, 0, 0.05)'}
                    },
                    'x': {
                        'grid': {'display': False}
                    }
                },
                'plugins': {
                    'legend': {'position': 'bottom'},
                    'tooltip': {
                        'backgroundColor': 'rgba(0, 0, 0, 0.8)',
                        'titleColor': '#fff',
                        'bodyColor': '#fff',
                        'borderColor': 'rgba(255, 255, 255, 0.1)',
                        'borderWidth': 1
                    }
                }
            }
        )

    def create_bar_chart(
        self,
        labels: List[str],
        datasets: List[Dict[str, Any]],
        title: str = "",
        horizontal: bool = False,
        stacked: bool = False
    ) -> ChartConfig:
        """Create a bar chart configuration."""
        chart_datasets = []

        for i, ds in enumerate(datasets):
            colors = ds.get('colors') or [self.default_palette[i % len(self.default_palette)]] * len(labels)
            chart_datasets.append(ChartDataset(
                label=ds.get('label', f'Series {i+1}'),
                data=ds.get('data', []),
                backgroundColor=colors if isinstance(colors, list) else [colors],
                borderColor=ds.get('borderColor', 'transparent'),
                borderWidth=0
            ))

        options = {
            'responsive': True,
            'indexAxis': 'y' if horizontal else 'x',
            'animation': {
                'duration': 1200,
                'easing': 'easeOutBounce'
            },
            'scales': {
                'y': {
                    'beginAtZero': True,
                    'stacked': stacked,
                    'grid': {'color': 'rgba(0, 0, 0, 0.05)'}
                },
                'x': {
                    'stacked': stacked,
                    'grid': {'display': False}
                }
            },
            'plugins': {
                'legend': {'position': 'bottom'}
            },
            'borderRadius': 8
        }

        return ChartConfig(
            type=ChartType.BAR,
            labels=labels,
            datasets=chart_datasets,
            title=title,
            options=options
        )

    def create_pie_chart(
        self,
        labels: List[str],
        data: List[Union[int, float]],
        title: str = "",
        doughnut: bool = False
    ) -> ChartConfig:
        """Create a pie or doughnut chart configuration."""
        colors = self.default_palette[:len(labels)]

        dataset = ChartDataset(
            label='Distribution',
            data=data,
            backgroundColor=colors,
            borderColor='#ffffff',
            borderWidth=2
        )

        return ChartConfig(
            type=ChartType.DOUGHNUT if doughnut else ChartType.PIE,
            labels=labels,
            datasets=[dataset],
            title=title,
            options={
                'responsive': True,
                'animation': {
                    'animateRotate': True,
                    'animateScale': True,
                    'duration': 1500
                },
                'plugins': {
                    'legend': {
                        'position': 'right',
                        'labels': {'padding': 20}
                    }
                },
                'cutout': '60%' if doughnut else '0%'
            }
        )

    def create_radar_chart(
        self,
        labels: List[str],
        datasets: List[Dict[str, Any]],
        title: str = ""
    ) -> ChartConfig:
        """Create a radar chart configuration."""
        chart_datasets = []

        for i, ds in enumerate(datasets):
            color = ds.get('color') or self.default_palette[i % len(self.default_palette)]
            chart_datasets.append(ChartDataset(
                label=ds.get('label', f'Series {i+1}'),
                data=ds.get('data', []),
                backgroundColor=color.replace(')', ', 0.2)').replace('rgb', 'rgba') if 'rgb' in color else color + '33',
                borderColor=color,
                borderWidth=2
            ))

        return ChartConfig(
            type=ChartType.RADAR,
            labels=labels,
            datasets=chart_datasets,
            title=title,
            options={
                'responsive': True,
                'animation': {'duration': 1500},
                'scales': {
                    'r': {
                        'beginAtZero': True,
                        'grid': {'color': 'rgba(0, 0, 0, 0.1)'},
                        'pointLabels': {'font': {'size': 12}}
                    }
                },
                'plugins': {
                    'legend': {'position': 'bottom'}
                }
            }
        )

    def create_scatter_chart(
        self,
        datasets: List[Dict[str, Any]],
        title: str = ""
    ) -> ChartConfig:
        """Create a scatter plot configuration."""
        chart_datasets = []

        for i, ds in enumerate(datasets):
            color = ds.get('color') or self.default_palette[i % len(self.default_palette)]
            # Scatter data should be [{x, y}, ...]
            chart_datasets.append(ChartDataset(
                label=ds.get('label', f'Series {i+1}'),
                data=ds.get('data', []),
                backgroundColor=color,
                borderColor=color,
                borderWidth=1
            ))

        return ChartConfig(
            type=ChartType.SCATTER,
            labels=[],
            datasets=chart_datasets,
            title=title,
            options={
                'responsive': True,
                'animation': {'duration': 1500},
                'scales': {
                    'x': {
                        'type': 'linear',
                        'position': 'bottom',
                        'grid': {'color': 'rgba(0, 0, 0, 0.05)'}
                    },
                    'y': {
                        'beginAtZero': True,
                        'grid': {'color': 'rgba(0, 0, 0, 0.05)'}
                    }
                },
                'plugins': {
                    'legend': {'position': 'bottom'}
                }
            }
        )

    def auto_detect_chart(self, data: Any, title: str = "") -> Optional[ChartConfig]:
        """
        Automatically detect the best chart type for given data.

        Args:
            data: Can be dict, list of numbers, or list of dicts
            title: Optional chart title

        Returns:
            ChartConfig or None if data can't be visualized
        """
        if isinstance(data, dict):
            # Dict with numeric values -> bar chart
            if all(isinstance(v, (int, float)) for v in data.values()):
                return self.create_bar_chart(
                    labels=list(data.keys()),
                    datasets=[{'label': title or 'Values', 'data': list(data.values())}],
                    title=title
                )

            # Explicit chart configuration
            if 'type' in data and 'data' in data:
                return self._from_explicit_config(data)

        elif isinstance(data, list):
            if len(data) == 0:
                return None

            # List of numbers -> line chart
            if all(isinstance(v, (int, float)) for v in data):
                return self.create_line_chart(
                    labels=[str(i) for i in range(len(data))],
                    datasets=[{'label': title or 'Values', 'data': data}],
                    title=title
                )

            # List of dicts (tabular data)
            if all(isinstance(v, dict) for v in data):
                keys = list(data[0].keys())
                if len(keys) >= 2:
                    label_key = keys[0]
                    value_key = keys[1]
                    return self.create_bar_chart(
                        labels=[str(row.get(label_key, '')) for row in data],
                        datasets=[{
                            'label': value_key,
                            'data': [row.get(value_key, 0) for row in data]
                        }],
                        title=title
                    )

        return None

    def _from_explicit_config(self, config: Dict) -> ChartConfig:
        """Create chart from explicit configuration dict."""
        chart_type = config.get('type', 'bar')

        if chart_type == 'pie':
            return self.create_pie_chart(
                labels=config.get('labels', []),
                data=config.get('data', []),
                title=config.get('title', '')
            )
        elif chart_type == 'doughnut':
            return self.create_pie_chart(
                labels=config.get('labels', []),
                data=config.get('data', []),
                title=config.get('title', ''),
                doughnut=True
            )
        elif chart_type == 'line':
            return self.create_line_chart(
                labels=config.get('labels', []),
                datasets=[{'data': config.get('data', [])}],
                title=config.get('title', '')
            )
        elif chart_type == 'radar':
            return self.create_radar_chart(
                labels=config.get('labels', []),
                datasets=[{'data': config.get('data', [])}],
                title=config.get('title', '')
            )
        else:  # bar
            return self.create_bar_chart(
                labels=config.get('labels', []),
                datasets=[{'data': config.get('data', [])}],
                title=config.get('title', '')
            )

    def extract_visualizable_data(self, text: str) -> List[Dict]:
        """
        Extract data that can be visualized from text response.

        Looks for:
        - Tables in markdown
        - Lists of numbers
        - Comparisons
        - Statistics
        """
        visualizations = []

        # Look for markdown tables
        table_pattern = r'\|(.+)\|\n\|[-:\s|]+\|\n((?:\|.+\|\n?)+)'
        tables = re.findall(table_pattern, text)

        for header, body in tables:
            headers = [h.strip() for h in header.split('|') if h.strip()]
            rows = []
            for row in body.strip().split('\n'):
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if cells:
                    rows.append(dict(zip(headers, cells)))

            if rows and len(headers) >= 2:
                # Try to extract numeric data
                try:
                    labels = [str(row.get(headers[0], '')) for row in rows]
                    data = [float(row.get(headers[1], 0).replace(',', '').replace('%', '')) for row in rows]

                    chart = self.create_bar_chart(
                        labels=labels,
                        datasets=[{'label': headers[1], 'data': data}],
                        title=f"{headers[0]} vs {headers[1]}"
                    )
                    visualizations.append(chart.to_dict())
                except (ValueError, AttributeError):
                    pass

        # Look for bullet point lists with numbers
        bullet_pattern = r'[-*]\s+(.+?):\s*(\d+(?:\.\d+)?(?:%)?)'
        bullets = re.findall(bullet_pattern, text)

        if len(bullets) >= 3:
            labels = [b[0] for b in bullets]
            data = [float(b[1].replace('%', '')) for b in bullets]

            chart = self.create_pie_chart(
                labels=labels,
                data=data,
                title="Distribution",
                doughnut=True
            )
            visualizations.append(chart.to_dict())

        return visualizations

    def create_comparison_chart(
        self,
        items: List[str],
        metrics: Dict[str, List[float]],
        title: str = "Comparison"
    ) -> ChartConfig:
        """Create a comparison chart for multiple items across metrics."""
        datasets = []

        for i, (metric_name, values) in enumerate(metrics.items()):
            datasets.append({
                'label': metric_name,
                'data': values,
                'color': self.default_palette[i % len(self.default_palette)]
            })

        return self.create_bar_chart(
            labels=items,
            datasets=datasets,
            title=title
        )

    def create_trend_chart(
        self,
        timestamps: List[str],
        values: List[float],
        title: str = "Trend",
        show_area: bool = True
    ) -> ChartConfig:
        """Create a trend line chart for time series data."""
        return self.create_line_chart(
            labels=timestamps,
            datasets=[{'label': title, 'data': values}],
            title=title,
            smooth=True,
            show_area=show_area
        )


# Singleton instance
data_viz_service = DataVisualizationService()
