import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from pyppeteer import launch
import os
import requests
import plotly.io as pio


INTERVALS = {
    '1m': '60',
    '3m': '180',
    '5m': '300',
    '15m': '900',
    '30m': '1800',
    '1h': '3600',
    '2h': '7200',
    '4h': '14400',
    '6h': '21600',
    '12h': '43200',
    '1d': '86400',
    '3d': '259200',
    '1w': '604800',
}

class Chart:
    """
    Class that prints charts of ohlcv type with a specific date period
    and interval. Buy/Sell points can be added on top of the candlestick
    chart. It can display the chart in the selected browser or saved it
    as an html or png file.
    """

    def __init__(self, pair, start = '', end = '', interval = ''):
        """
        Creates a Figure object with the relevant candlestick and volume data. It does
        so by making a request to the Cryptowatch API. Dates are formated to POSIX
        time.

        :param pair:         Symbol of the cripto-coin pair '<crypto>eur'
        :type pair:          str
        :param start:        Start date for the chart 'dd/mm/YYYY'
        :type start:         str
        :param end:          End date for the chart 'dd/mm/YYYY'
        :type end:           str
        :param interval:     Interval of the candlesticks
        :type interval:      str
        :returns:            None

        If only the pair is given, the chart created is of the last day
        """

        format = '%d/%m/%Y'
        local = 'Europe/Madrid'

        # By default, yesterday
        start_date = (
            pd.to_datetime(start, format=format).tz_localize(local)
            if start else
            pd.Timestamp.today(tz=local).floor('s') - pd.Timedelta('1d')
        )

        # By default, today
        end_date = (
            pd.to_datetime(end, format=format).tz_localize(local)
            if end else
            pd.Timestamp.today(tz=local).floor('s')
        )

        # Change POSIX time from nanoseconds to seconds
        start_posix = start_date.value // (10 ** 9)
        end_posix = end_date.value // (10 ** 9)

        data = _get_ohlcv_data(pair, interval, start_posix, end_posix)

        # Create the folder where files will be saved
        folder_path = os.path.realpath('./archivos')
        if (not os.path.isdir(folder_path)):
            os.mkdir(folder_path)
    
        self.__local = local
        self.__file_path = '{}/{}_{}_{}'.format(
            folder_path,
            pair,
            start_date.strftime('%d-%m-%Y'),
            end_date.strftime('%d-%m-%Y')
        )
        self.__pair = pair
        self.__start_date = start_date
        self.__end_date = end_date
        self.__fig = self.__create_figure(data)

    def get_pair(self):
        """
        Returns the crypto pair
        """
        return self.__pair

    def get_start_date(self):
        """
        Returns the start date of the cart

        :returns:  Timestamp
        """

        return self.__start_date

    def get_end_date(self):
        """
        Returns the end date of the cart

        :returns:  Timestamp
        """
        return self.__end_date   
           
    def add_buy_sell_point(self, label, quantity, price, date):
        """
        Adds a buy/sell point over the candlestick chart, specifying the quantity
        of crypto buyed/sold, the price and the date. It also creates an hover box
        with the data.

        :param label:       Symbol of buy or sell 'b'/'s'
        :type label:        str
        :param quantity:    Quantity of the bought/sold coin
        :type quantity:     float
        :param price:       Price of the coin at the moment of purchase or sale
        :type price:        float
        :param date:        Date of the purchase/sale
        :type date:         str
        :returns:           None

        Points out of range are discarded
        """
        point_date = pd.to_datetime(
            date,
            format='%d/%m/%Y %H:%M'
        ).tz_localize(self.__local)

        # Check if point is in range
        if (point_date < self.__start_date or point_date > self.__end_date):
            return

        coin = self.__pair[:-3].upper()
        annotation = '{} {} {} at {} € <br> {}'.format(
            label.capitalize(),
            quantity, 
            coin, 
            price, 
            date
        )
        
        point = {
            'price': price, 
            'date': point_date, 
            'annotation': annotation
        }

        # Creates a scatter chart with just one point
        color_point = (
            '#bbdc86'
            if label == 'b' or label == 'B' else
            '#e70039'
        )
        figure_point = go.Scatter(
            x=[point['date']],
            y=[point['price']],
            mode='markers+text',
            showlegend=False,
            marker={
                "color": color_point,
                "line": {
                    "width": 1
                },
                "size": 7
            },
        )

        self.__fig.append_trace(figure_point, row=1, col=1)

        pos = self.__get_note_position_x(point_date)
        self.__fig.add_annotation(
            x=point['date'],
            y=point['price'],
            text=point['annotation'],
            showarrow=True,
            font=dict(
                family="Courier New, monospace",
                size=12,
                color="#000000"
            ),
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#636363",
            ax=pos,
            bordercolor="#c7c7c7",
            borderwidth=1,
            borderpad=1,
            bgcolor="#ff7f0e",
            opacity=0.6,
        )

    def delete_buy_sell_points(self):
        """
        Delete all buy/sell points and annotations associated with them.

        The Plotly library doesn't have functionality to delete subparts of
        a chart nor annotations, this is why it is need to modify the 'fig'
        object directly.
        
        This method has two assumptions:
            1) The fig.data list has three elements and the last one
               corresponds to the buy/sell points
            2) The only annotations in 'fig' are the ones corresponding
               to the buy/sell points
        """

        self.__fig.data = [self.__fig.data[0], self.__fig.data[1]]
        self.__fig.layout.annotations = []


    def show_chart(self):
        """
        Show the chart in the selected browser.
        """

        # Select default browser (firefox, chrome, chromium, etc)
        pio.renderers.default = "browser"

        self.__set_chart_layout()
        config = {'scrollZoom': True}

        self.__fig.show(config=config)


    def save_chart_as_html(self):
        """
        Save the chart in an html file in the specified path

        :returns:  str  Returns the html file path
        """

        self.__set_chart_layout()

        config = dict({'scrollZoom': True})
        
        html_path = "{}.html".format(self.__file_path)
        self.__fig.write_html(html_path, config=config)

        return html_path

    def save_chart_as_png(self):
        """
        This method converts the chart saved in the html file
        to a png file. Since the pyppeteer library uses asynchronous
        functions, I prefer to 'encapsulate' the function here so it
        can be called like a normal method.
        """

        asyncio.run(self.__save_image_async())
        

    # Private methods
    def __get_note_position_x(self, point_date):
        """
        The annotation of the buy/sell points can be near the edgeds of the
        chart. This method adjusts the position in the X axe and displaces
        it to the center if it is too near the edge.
        
        :param point_date:  Date of the buy/sell point
        :type point_date:   Datetime
        :returns:           int       Returns the X position of the annotation
        """
        start_posix = self.__start_date.value // (10 ** 9)
        end_posix = self.__end_date.value // (10 ** 9)
        point_difference = end_posix - point_date.value // (10 ** 9)
        difference = end_posix - start_posix
        percentage = point_difference / difference
        
        if(percentage > 0.9):
            return 100

        if(percentage < 0.1):
            return -100

        return 20

    async def __save_image_async(self):
        """
        Launchs the chromium browser in the background and makes
        a snapshot of the viewport.
        """
        html_path = self.save_chart_as_html()
        image_path = "{}.png".format(self.__file_path)

        browser = await launch({'headless': True, 'defaultViewport': {'width': 1920, 'height': 1080}})
        chart_page = await browser.newPage()

        await chart_page.goto('file://{}'.format(html_path))
        await chart_page.screenshot({
            'path': '{}'.format(image_path),
            'fullPage': 'true'
        })
        
        await browser.close()

    def __create_figure(self, data):
        """
        Creates the fig object that will store all the data related to the
        charts, templates, styles, annotations, etc.

        :param data:        Contains all the candlestick and volume data
        :type data:         Dictionary
        :returns:           Figure       Returns a Figure object from Plotly library
        """
        extract_data = lambda x : [single_data[x] for single_data in data]

        # Convert POSIX timestamps to local time
        dates = pd.to_datetime(
            extract_data(0),
            unit='s',
            utc=True
        ).tz_convert(self.__local)

        data_frame = pd.DataFrame({
            'dates':           dates,
            'open':   extract_data(1),
            'close':     extract_data(4),
            'maximum':     extract_data(2),
            'minimum':     extract_data(3),
            'volumes':        extract_data(5)
        })

        # Creates subplot (candlesticks/points and volume)
        fig = make_subplots(
            rows=2,
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03,
            row_width=[0.2, 0.7],
        )

        # Creates chart of candlesticks in the upper trace
        candlesticks = go.Candlestick(
            x=data_frame['dates'],
            open=data_frame['open'], 
            high=data_frame['maximum'],
            low=data_frame['minimum'], 
            close=data_frame['close'],
            showlegend=False
        )

        fig.append_trace(candlesticks, row=1, col=1)

        # Volume chart in the lower trace
        volumen = go.Bar(
            x=data_frame['dates'],
            y=data_frame['volumes'],
            showlegend=False,
            marker={
                "color": "#EF553B",
            },
        )

        fig.append_trace(volumen, row=2, col=1)

        return fig

    def __set_chart_layout(self):
        """
        Adds legends, range and other characteristics of the final chart
        """
        delta = (self.__end_date - self.__start_date ) * 0.005

        title = '{}: {} - {}'.format(
            self.__pair,
            self.__start_date.strftime('%d-%m-%Y'),
            self.__end_date.strftime('%d-%m-%Y')
        )

        # Don't show the slider
        self.__fig.update_layout(
            xaxis_rangeslider_visible=False,
            yaxis1_title = 'Price (€)',
            yaxis2_title = 'Volume',
            xaxis2_title = 'Time',
            xaxis_range=[self.__start_date - delta, self.__end_date + delta],
            title={
                'text': title,
                'y':0.94,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'},
            font=dict(
                family="Courier New, monospace",
                size=15,
            )
        )


def _get_ohlcv_data(pair, interval, after, before):
    """
    Makes a request to the Cryptowatch API to obtain the histocal candles
    ando volume in the Kraken market.


    :param par:         Symbolf of the crypto-coin pair '<crypto>eur'
    :type par:          str
    :param interval:    Candlestick interval
    :type interval:     str
    :param after:       Date after which data is obtained (POSIX)
    :type after:        Timestamp
    :param before:      Date before which data is obtained (POSIX)
    :type before:       Timestamp
    :returns:           List of candles and volume data
    
    API has the form: 'https://api.cryptowat.ch/markets/:exchange/:pair/ohlc'.
        + Mandatory parameters:
            - exchange:
            - pair:     
        + Optional parameters:
            - before:   (Time POSIX)
            - after:    (Time POSIX)
            - periods:  (list)
            
    The API doesn't allow small intervals for old dates
    """

    market = 'kraken'
    url_base_api = 'https://api.cryptowat.ch/markets'
    url_candlesticks = '{}/{}/{}/ohlc'.format(url_base_api, market, pair)

    # The interval is not included in the request so all intervals
    # of a time period are returned and the selected the optimal one
    query_string = {
        'before': before,
        'after': after
    }

    # Returns a Response object with the JSON data and if it fails, an
    # exception is thrown
    response = requests.get(url_candlesticks, params=query_string)
    response.raise_for_status()

    # Extract relevant candlesticks and volumes data
    data = response.json() # Has two properties, 'result' and 'allowance'

    optimal_interval =  _get_optimal_interval(interval, data)

    if (optimal_interval == None):
        raise Exception('The intervals in the response are empty!')
    
    relevant_data = data['result']['{}'.format(optimal_interval)]
    return relevant_data


def _get_optimal_interval(time, data):
    """
    Calculates the optimal interval of a data set, it uses and 'ideal'
    number of points to display in the chart and selects accordingly.
    If time parameters is not empty, the function is stopped.

    :param time:   Candlesticks interval
    :type time:    str
    :param data:   Content of the response
    :type data:    list           
    :returns:      int    Optinmal interval, if it doesn't exist, None
    """
    # Interval defined by user
    if (time):
        return time

    optimal_size = 500

    # Sort intervals by number of points
    intervals = {}
    for interval in data['result']:
        size = len(data['result'][interval])
        intervals[interval] = size

    sorted_intervals = dict(sorted(intervals.items(), key=lambda x: x[1]))

    # Search the first interval which number of points is greater than the
    # optimal size
    for interval in sorted_intervals:
        size = sorted_intervals[interval]

        if optimal_size  < size:
            return interval

    # If not found, and the last one has no points, returns 0
    interval, size = list(sorted_intervals.items())[-1]
    if size == 0:
        return None

    return interval


if (__name__ == '__main__'):
    chart = Chart('btceur', '20/01/2018')
    chart.add_buy_sell_point('b', 0.0002, 40000, '01/02/2018 22:13')
    chart.add_buy_sell_point('s', 0.0002, 40000, '22/04/2021 22:13')
    chart.add_buy_sell_point('b', 0.003, 52000, '01/03/2021 05:22')
    # chart.delete_buy_sell_points()
    chart.show_chart()
    chart.save_chart_as_png()