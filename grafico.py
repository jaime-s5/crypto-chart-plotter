import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from pyppeteer import launch
import os
import requests


INTERVALOS = {
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

class Grafico:
    """
    Clase para imprimir gráficos de tipo ohlcv con un período e
    intervalo determinados. Se pueden añadir puntos de compra y venta
    superpuestos y con leyenda. Permite también mostrar el gráfico en el
    navegador y guardarlo en formato imagen o html.
    """

    def __init__(self, par, inicial = '', final = '', intervalo = ''):
        """
        Crea un objeto Figure con los datos relevantes de las velas y el volumen de la 
        petición a la API de Cryptowatch. Se formatean las fechas a tiempo POSIX
        y se realiza la petición.

        :param par:         Símbolo del par cripto-moneda '<crypto>eur'
        :type par:          str
        :param inicial:     Fecha a partir de la cual se obtienen las velas 'dd/mm/YYYY'
        :type inicial:      str
        :param final:       Fecha hasta la cual se obtienen las velas 'dd/mm/YYYY'
        :type final:        str
        :param intervalo:   Intervalo de las velas
        :type intervalo:    str
        :returns:           None

        Si solo se le pasa el par, por defecto crea un gráfico del último día.
        """

        formato = '%d/%m/%Y'
        local = 'Europe/Madrid'

        # Por defecto ayer
        fecha_inicial = (
            pd.to_datetime(inicial, format=formato).tz_localize(local)
            if inicial else
            pd.Timestamp.today(tz=local).floor('s') - pd.Timedelta('1d')
        )

        # Por defecto hoy
        fecha_final = (
            pd.to_datetime(final, format=formato).tz_localize(local)
            if final else
            pd.Timestamp.today(tz=local).floor('s')
        )

        # Cambiar tiempo POSIX de nanosegundos a segundos
        posix_inicial = fecha_inicial.value // (10 ** 9)
        posix_final = fecha_final.value // (10 ** 9)

        datos = _obtener_datos_ohlcv(par, intervalo, posix_inicial, posix_final)

        # Crear carpeta donde guardar html e imagen
        ruta_carpeta = os.path.realpath('./archivos')
        if (not os.path.isdir(ruta_carpeta)):
            os.mkdir(ruta_carpeta)
    
        self.__local = local
        self.__ruta_archivo = '{}/{}_{}_{}'.format(
            ruta_carpeta,
            par,
            fecha_inicial.strftime('%d-%m-%Y'),
            fecha_final.strftime('%d-%m-%Y')
        )
        self.__par = par
        self.__fecha_inicial = fecha_inicial
        self.__fecha_final = fecha_final
        self.__fig = self.__crear_figura(datos)

    def obtener_par(self):
        """
        Devuelve el par
        """
        return self.__par

    def obtener_fecha_inicial(self):
        """
        Devuelve la fecha inicial del gráfico

        :returns:  Timestamp
        """

        return self.__fecha_inicial

    def obtener_fecha_final(self):
        """
        Devuelve la fecha final del gráfico

        :returns:  Timestamp
        """
        return self.__fecha_final   
           
    def añadir_punto_compra_venta(self, etiqueta, cantidad, precio, fecha):
        """
        Añadir un punto de compra o venta sobre el gráfico de velas, especificando
        la cantidad, el precio y la fecha. A mayores añade un cuadrado con la
        información.

        :param etiqueta:    Símbolo de compra o venta 'c' o 'v'
        :type etiqueta:     str
        :param cantidad:    Cantidad de la moneda comprada/vendida
        :type cantidad:     float
        :param precio:      Precio de la moneda en el momento de la compra/venta
        :type precio:       float
        :param fecha:       Fecha de la compra/venta
        :type fecha:        str
        :returns:           None

        Los puntos fuera de rango se descartan.
        """
        fecha_punto = pd.to_datetime(
            fecha,
            format='%d/%m/%Y %H:%M'
        ).tz_localize(self.__local)

        # Comprueba si el punto se encuentra dentro del rango de fechas
        if (fecha_punto < self.__fecha_inicial or fecha_punto > self.__fecha_final):
            return

        moneda = self.__par[:-3].upper()
        anotacion = '{} {} {} a {} € <br> {}'.format(
            etiqueta.capitalize(),
            cantidad, 
            moneda, 
            precio, 
            fecha
        )
        
        punto = {
            'precio': precio, 
            'fecha': fecha_punto, 
            'anotacion': anotacion
        }

        # Crear un gráfico scatter con un solo punto
        color_punto = (
            '#bbdc86'
            if etiqueta == 'c' or etiqueta == 'C' else
            '#e70039'
        )
        figura_punto = go.Scatter(
            x=[punto['fecha']],
            y=[punto['precio']],
            mode='markers+text',
            showlegend=False,
            marker={
                "color": color_punto,
                "line": {
                    "width": 1
                },
                "size": 7
            },
        )

        self.__fig.append_trace(figura_punto, row=1, col=1)

        pos = self.__calculo_posicion_nota(fecha_punto)
        self.__fig.add_annotation(
            x=punto['fecha'],
            y=punto['precio'],
            text=punto['anotacion'],
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

    def borrar_puntos_compra_venta(self):
        """
        Borrar todos los puntos de compra y venta y las anotaciones asociadas
        a ellos.

        La librería no tiene funciones para borrar subpartes del gráfico
        o anotaciones, es por eso que hay que modificar directamente la 
        estructura 'fig' que contiene toda la información. 
        
        Esta función asume que:
            1) El arreglo 'fig.data' tiene tres elementos y que el último
               corresponde a los puntos de compra y venta.
            2) Las únicas anotaciones que hay son de los puntos de compra y
               venta.
        """

        self.__fig.data = [self.__fig.data[0], self.__fig.data[1]]
        self.__fig.layout.annotations = []


    def mostrar_grafico(self):
        """
        Muestra el gráfico en el navegador.
        """
        self.__configurar_disposicion_grafico()
        config = {'scrollZoom': True}

        self.__fig.show(config=config)


    def guardar_grafico_en_formato_html(self):
        """
        Guarda el gráfico en formato html en la ruta especificada

        :returns:  str  Devuelve la ruta del archivo html
        """

        self.__configurar_disposicion_grafico()

        config = dict({'scrollZoom': True})
        
        ruta_html = "{}.html".format(self.__ruta_archivo)
        self.__fig.write_html(ruta_html, config=config)

        return ruta_html

    def guardar_grafico_en_formato_imagen(self):
        """
        Transforma la figura en un archivo html y después
        lo guarda en formato imagen. La librería para crear
        la imagen usa métodos asíncronos.
        """

        asyncio.run(self.__guardar_imagen_asincrona())
        

    # Métodos privados
    def __calculo_posicion_nota(self, fecha_punto):
        """
        La anotación de los puntos de compra venta puede salirse del gráfico,
        esta función ajusta la posición en el eje X de la nota.
        
        :param fecha_punto: Fecha del punto de compra/venta
        :type fecha_punto:  Datetime
        :returns:           int       Devuelve la posición de la nota en el eje X
        """
        posix_inicial = self.__fecha_inicial.value // (10 ** 9)
        posix_final = self.__fecha_final.value // (10 ** 9)
        diferencia_punto = posix_final - fecha_punto.value // (10 ** 9)
        diferencia = posix_final - posix_inicial
        porcentaje = diferencia_punto / diferencia
        
        if(porcentaje > 0.9):
            return 100

        if(porcentaje < 0.1):
            return -100

        return 20

    async def __guardar_imagen_asincrona(self):
        """
        Lanza el navegador chromium en segundo plano y realiza una
        captura de pantalla.
        """
        ruta_html = self.guardar_grafico_en_formato_html()
        ruta_imagen = "{}.png".format(self.__ruta_archivo)

        navegador = await launch({'headless': True, 'defaultViewport': {'width': 1920, 'height': 1080}})
        pagina_grafico = await navegador.newPage()

        await pagina_grafico.goto('file://{}'.format(ruta_html))
        await pagina_grafico.screenshot({
            'path': '{}'.format(ruta_imagen),
            'fullPage': 'true'
        })
        
        await navegador.close()

    def __crear_figura(self, datos):
        """
        Crea el objeto figura que guardará toda la información relacionada
        con los gráficos, plantilla, estilos y anotaciones.

        :param datos:       Contiene todos los datos de las velas y el volumen
        :type datos:        Dictionary
        :returns:           Figure          Devuelve un objeto tipo Figure de la librería Plotly
        """
        extraer_datos = lambda x : [dato[x] for dato in datos]

        # Convertir marcas de tiempo UNIX a tiempo local
        fechas = pd.to_datetime(
            extraer_datos(0),
            unit='s',
            utc=True
        ).tz_convert(self.__local)

        trama_de_datos = pd.DataFrame({
            'fechas':           fechas,
            'apertura_velas':   extraer_datos(1),
            'cierre_velas':     extraer_datos(4),
            'maximo_velas':     extraer_datos(2),
            'minimo_velas':     extraer_datos(3),
            'volumenes':        extraer_datos(5)
        })

        # Crear subgráficos (velas/puntos y volumen)
        fig = make_subplots(
            rows=2,
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03,
            row_width=[0.2, 0.7],
        )

        # Gráfico de velas en la traza superior
        velas = go.Candlestick(
            x=trama_de_datos['fechas'],
            open=trama_de_datos['apertura_velas'], 
            high=trama_de_datos['maximo_velas'],
            low=trama_de_datos['minimo_velas'], 
            close=trama_de_datos['cierre_velas'],
            showlegend=False
        )

        fig.append_trace(velas, row=1, col=1)

        # Gráfico de volumen en la traza inferior
        volumen = go.Bar(
            x=trama_de_datos['fechas'],
            y=trama_de_datos['volumenes'],
            showlegend=False,
            marker={
                "color": "#EF553B",
            },
        )

        fig.append_trace(volumen, row=2, col=1)

        return fig

    def __configurar_disposicion_grafico(self):
        """
        Añade leyendas, rangos y otras características del gráfico
        """
        delta = (self.__fecha_final - self.__fecha_inicial ) * 0.005

        title = '{}: {} - {}'.format(
            self.__par,
            self.__fecha_inicial.strftime('%d-%m-%Y'),
            self.__fecha_final.strftime('%d-%m-%Y')
        )

        # No mostrar el slider
        self.__fig.update_layout(
            xaxis_rangeslider_visible=False,
            yaxis1_title = 'Precio (€)',
            yaxis2_title = 'Volumen',
            xaxis2_title = 'Tiempo',
            xaxis_range=[self.__fecha_inicial - delta, self.__fecha_final + delta],
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


def _obtener_datos_ohlcv(par, intervalo, despues, antes):
    """
    Petición a la API de Cryptowatch para obtener los históricos de velas
    y el volumen en el mercado Kraken.

    :param par:         Símbolo del par cripto-moneda '<crypto>eur'
    :type par:          str
    :param intervalo:   Intervalo de las velas
    :type intervalo:    str
    :param despues:     Fecha a partir de la cual se obtienen las velas (POSIX)
    :type despues:      Timestamp
    :param antes:       Fecha hasta la cual se obtienen las velas (POSIX)
    :type antes:        Timestamp
    :returns:           Lista con los datos de velas y volumen
    
    API de la forma: 'https://api.cryptowat.ch/markets/:exchange/:pair/ohlc'.
        + Parámetros obligatorios:
            - exchange:
            - pair:     
        + Parámetros opcionales:
            - before:   (Tiempo POSIX)
            - after:    (Tiempo POSIX)
            - periods:  (list)
            
    La API no permite intervalos muy pequeños para períodos antiguos.
    """

    mercado = 'kraken'
    url_base_api = 'https://api.cryptowat.ch/markets'
    url_velas = '{}/{}/{}/ohlc'.format(url_base_api, mercado, par)

    # No se incluye el intervalo para que la respuesta contenga
    # todos los intervalos y luego itererar sobre ella
    cadena_de_consulta = {
        'before': antes,
        'after': despues
    }

    # Devuelve un objeto Response con el JSON y si falla, lanza una excepción
    respuesta = requests.get(url_velas, params=cadena_de_consulta)
    respuesta.raise_for_status()

    # Extrae los datos de las velas y volúmenes relevantes
    datos = respuesta.json() # Tiene dos propiedades 'result' y 'allowance'

    intervalo_optimo =  _calculo_intervalo_optimo(intervalo, datos)

    if (intervalo_optimo == None):
        raise Exception('Los intervalos en la respuesta están vacíos!')
    
    datos_relevantes = datos['result']['{}'.format(intervalo_optimo)]
    return datos_relevantes


def _calculo_intervalo_optimo(tiempo, datos):
    """
    Calcula el intervalo óptimo de un conjunto de datos, usando un
    tamaño especificado y un rango. Si el parámetro intervalo no está
    vacío se devuelve.

    :param intervalo:   Intervalo de las velas
    :type intervalo:    str
    :param datos:       Contenido de la respuesta en formato JSON
    :type datos:        list           
    :returns:           int    Intervalo óptimo, si no existe, None
    """
    # Intervalo definido por el usuario
    if (tiempo):
        return tiempo

    tamaño_optimo = 500

    # Ordenamos los intervalos por el tamaño de puntos
    intervalos = {}
    for intervalo in datos['result']:
        tamaño = len(datos['result'][intervalo])
        intervalos[intervalo] = tamaño

    intervalos_ordenados = dict(sorted(intervalos.items(), key=lambda x: x[1]))

    # Buscamos el primer intervalo cuyo número de puntos sea mayor al tamaño optimo
    for intervalo in intervalos_ordenados:
        tamaño = intervalos_ordenados[intervalo]

        if tamaño_optimo  < tamaño:
            return intervalo

    # Si no se encuentra ninguno, y el ultimo no tiene puntos, se devuelve 0
    intervalo, tamaño = list(intervalos_ordenados.items())[-1]
    if tamaño == 0:
        return None

    return intervalo


if (__name__ == '__main__'):
    grafico = Grafico('btceur', '20/01/2018', '20/02/2018')
    grafico.añadir_punto_compra_venta('c', 0.0002, 40000, '01/04/2020 22:13')
    grafico.añadir_punto_compra_venta('v', 0.0002, 40000, '22/04/2021 22:13')
    grafico.añadir_punto_compra_venta('c', 0.003, 52000, '01/03/2021 05:22')
    # grafico.borrar_puntos_compra_venta()
    grafico.mostrar_grafico()
    grafico.guardar_grafico_en_formato_imagen()