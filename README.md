# Treasury Yield Spread vs Asset Price Performance

Interactive visualization comparing the 10-Year minus 2-Year Treasury yield spread against 6-month percent changes in major asset classes (S&P 500, NASDAQ, Gold, Silver).

## Features

### Multi-Asset Comparison
- S&P 500, NASDAQ, Gold, and Silver 6-month rolling returns
- 10Y-2Y Treasury yield spread overlay on secondary axis
- Toggle visibility via legend clicks

### Economic Context Overlays
- NBER recession periods (red shading)
- Yield curve inversion periods (yellow shading) — historically a leading recession indicator

### Correlation Analysis
- 12-month rolling correlation between NASDAQ returns and yield spread
- Absolute correlation magnitude to identify the extent of relationships regardless of direction

### Interactive Charts

> **Note:** To benefit from interactive features, run the notebook in Jupyter. The static HTML hosted on GitHub does not support interaction.

- Hover tooltips with precise values
- Zoom and pan with synchronized axes
- Responsive layout for different screen sizes

## Data Sources

| Data | Source |
|------|--------|
| Equities | Yahoo Finance (NASDAQ, S&P 500) |
| Commodities | World Bank + Yahoo Finance (Gold, Silver) |
| Treasury Yields | FRED (Federal Reserve Economic Data) |
| Recession Indicators | FRED (NBER recession dates) |

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Launch Jupyter
jupyter lab yield_spread_vs_prices.ipynb
```
