# Crypto chart plotter

## About the project

A Python module that creates a chart of a crypto coin from data in the Kraken market.

## Installation

First, create an environment and start it:

```bash
python -m venv env
source bin/activate
```

Then install all the requirements needed for the module:

```bash
pip install -r requirements.txt
```

## Documentation

### Chart(pair, [, options])

Creates a chart with the given crypto pair, if no optional parameters are given, it will default to the last day, if no interval is given, it will select it automatically.

The chart has two subtraces, in the upper trace, the candlestick chart and in the
lower trace, the volume chart.

- `pair`: `<str>` Symbol of the cripto-coin pair '\<crypto>eur'
- `options`:
  - `start_date`: `<str>` Start date for the chart 'dd/mm/YYYY'
  - `end_date`: `<str>`End date for the chart 'dd/mm/YYYY'
  - `interval`: `<str>`Interval of the candlesticks
- `returns`: `<chart>`

### Chart.add_buy_sell_point(label, quantity, price, time)

Adds a buy/sell point to the candlestick trace chart. If out of bounds,
it will be discarded.

- `label`: `<str>` Symbol of buy or sell 'b'/'s'
- `quantity`: `<float>` Quantity of the bought/sold coin
- `price`: `<float>` Price of the coin at the moment of purchase or sale
- `time`: `<str>` Date of the purchase/sale
- `returns`: `<None>`

### Chart.delete_buy_sell_points()

Delete all buy/sell points

- `returns`: `<None>`

### Chart.show_chart()

Displays chart in selected browser

- `returns`: `<None>`

### Chart.save_chart_as_png()

Saves chart in a png file

- `returns`: `<None>`

### Chart.save_chart_as_html()

Saves chart in an html file

- `returns`: `<str>` Returns the html file path
