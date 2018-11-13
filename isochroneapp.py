
import collections
import time

import arrow
import ipyleaflet as ipl
import ipywidgets as widgets
import requests
import toml


# See readme.md for credentials.toml formatting
cred = toml.load('credentials.toml')
appid = cred['api']['here']['appid']
appcode = cred['api']['here']['appcode']


modes = {'Walk ': ('pedestrian', 13),
         'Bike ': ('bicycle', 10),
         'Drive ': ('car', 8),
         }

crd = []
shapes = {}

def address_to_coord(address_string):
    """Return a tuple of the Lat/Long of the address."""
    raw_address = '+'.join(address_string.replace(',', ' ').split(' '))
    formatted_address = raw_address.replace('++', '+')

    url = "https://geocoder.api.here.com/6.2/geocode.json" +\
        "?app_id=" +\
        appid +\
        "&app_code=" +\
        appcode +\
        "&searchtext=" +\
        formatted_address

    response = requests.get(url)

    data = response.json()
    lat_long = data['Response']['View'][0]['Result'][0]['Location']['NavigationPosition'][0]
    point = coord_to_tuple(lat_long)
    crd = [point]
    
    return point


def get_isochrome(coordinates, timestamp, mode='car', rangetype="time",
                  ranges=[600, 1200, 1800, 2400, 3000, 3600], points="2000"):
    """Format the Here.com API call, return the json response."""
    # Time ranges in seconds, Distance ranges in meters

    # Ensure ranges are strings instead of integers
    range_strings = list(map(str, ranges))
    ranges = ','.join(range_strings)

    # Ensure coordinates are a string
    coordinates = coord_to_string(coordinates)

    url = "https://isoline.route.cit.api.here.com/routing/" +\
        "7.2/calculateisoline.json?app_id=" +\
        appid +\
        "&app_code=" +\
        appcode +\
        "&mode=shortest;" +\
        mode +\
        ";traffic:enabled&start=geo!" +\
        coordinates + "&maxpoints=" +\
        points + "&range=" +\
        ranges +\
        "&rangetype=" +\
        rangetype +\
        "&jsonAttributes=41"

    response = requests.get(url)

    data = response.json()

    return data


def array_to_points(points):
    """Transform an array of floats into a list of 2 tuples."""
    point_list = []

    array = collections.deque(points)
    while array:
        lat = array.popleft()
        long = array.popleft()
        point = (lat, long)
        point_list.append(point)

    return point_list


def drive_time_shapes(drive_time):
    """Simplify JSON response into a dictionary of point lists."""
    isochrones = {}
    try:
        
        for shape in drive_time['response']['isoline']:
            uid = str(int(shape['range'] / 60)) + ' minutes'

            points = shape['component'][0]['shape']

            point_list = array_to_points(points)

            isochrones[uid] = point_list
            shapes[uid] = point_list
    except:
        print(drive_time)
        
        
    return isochrones


def coord_to_tuple(coordinates):
    """Transform coordinates to a 2 tuple."""
    if type(coordinates) == str:
        center = tuple(map(float, coordinates.split(',')))

    elif type(coordinates) == dict:
        center = tuple(coordinates.values())

    elif type(coordinates) == tuple:
        center = coordinates

    elif (type(coordinates) == list) and (len(coordinates) == 2):
        center = tuple(coordinates)

    else:
        print('invalid coordinate type')
        center = None

    return center


def coord_to_string(coordinates):
    """Transform coordinates into a string for API"""
    if type(coordinates) == tuple:
        string = ','.join(list(map(str, coordinates)))

    elif type(coordinates) == dict:
        string = ','.join(list(map(str, coordinates.values())))

    elif (type(coordinates) == list) and (len(coordinates) == 2):
        string = ','.join(list(map(str, coordinates)))

    elif type(coordinates) == str:
        string = coordinates

    else:
        print('invalid coordinate type')
        string = None

    return string


def plot_isochrones(coordinates, isochrones, zoom_level=8):
    '''Initiate map and plot isochrones centered on coordinates.'''

    center = coord_to_tuple(coordinates)

    layer_color = 'brown'
    fill_color = 'orange'
    m = ipl.Map(center=center, zoom=zoom_level)
    for key in isochrones.keys():

        item = ipl.Polygon(
            locations=isochrones[key],
            color=layer_color,
            weight=1,
            fill_color=fill_color,
            fill_opacity=0.2,
            name=key)
        m.add_layer(item)

    m.add_control(ipl.LayersControl())

    return m


def demo_basemaps(location, base_demo):

    strava = ipl.basemap_to_tiles(ipl.basemaps.Strava.Winter)
    carto_dark = ipl.basemap_to_tiles(ipl.basemaps.CartoDB.DarkMatter)
    mapnik = ipl.basemap_to_tiles(ipl.basemaps.OpenStreetMap.Mapnik)
    black_white = ipl.basemap_to_tiles(ipl.basemaps.OpenStreetMap.BlackAndWhite)
    osm_hot = ipl.basemap_to_tiles(ipl.basemaps.OpenStreetMap.HOT)
    esri_image = ipl.basemap_to_tiles(ipl.basemaps.Esri.WorldImagery)
    esri_topo = ipl.basemap_to_tiles(ipl.basemaps.Esri.WorldTopoMap)
    esri_world = ipl.basemap_to_tiles(ipl.basemaps.Esri.NatGeoWorldMap)
    water_color = ipl.basemap_to_tiles(ipl.basemaps.Stamen.Watercolor)


    layer_demo = [strava, carto_dark, mapnik,
                  black_white, osm_hot, esri_image,
                  esri_topo, esri_world, water_color]

    for show_layer in layer_demo:

        base_demo.add_layer(show_layer)

        time.sleep(.95)
        base_demo.remove_layer(base_demo.layers[0])

    time.sleep(1.2)
    base_demo.add_layer(mapnik)
    base_demo.add_control(ipl.LayersControl())
    
    
    

def create_map(coordinates=None, timestamp=None, address=None, mode='Drive '):

    transport_type, zoom_level = modes[mode]

    if not timestamp:
        timestamp = str(arrow.now().floor('second')).split('+')[0] + 'Z'

    if address:
        coordinates = address_to_coord(address)

    elif coordinates:
        coordinates = coord_to_string(coordinates)
        
    else:
        print('Please include valid address or coordinates (Latitude, Longitude)')

        return None

    drive_time = get_isochrome(coordinates, timestamp, transport_type)

    isochrones = drive_time_shapes(drive_time)

    m = plot_isochrones(coordinates, isochrones, zoom_level)

    return m


def display_results(x):

    out.clear_output(wait=True)
    map_result = create_map(address=address_box.value,
                            mode=method.value)
    with out:
        display(box, map_result)


address_box = widgets.Text(
    value='1234 Main Street, Anytown, MA, 12345',
    placeholder='1234 Main Street, Anytown, MA, 12345',
    description='Address:',
    layout=widgets.Layout(width='auto'),
    disabled=False
)

inprog = widgets.IntProgress(
    value=7,
    min=0,
    max=10,
    step=1,
    description='Loading:',
    bar_style='success',  # 'success', 'info', 'warning', 'danger' or ''
    orientation='horizontal'
)

method = widgets.ToggleButtons(
    options=['Walk ', 'Drive '],
    description='Method:',
    disabled=False,
    value='Drive ',
    button_style='success',  # 'success', 'info', 'warning', 'danger' or ''
    tooltips=['Walking Distance', 'Driving Distance'],
    icons=['blind', 'car']
)
submit = widgets.Button(
    description='Submit',
    disabled=False,
    button_style='',  # 'success', 'info', 'warning', 'danger' or ''
    tooltip='Submit',
    icon=''
)


w = [address_box, method, submit]

box_layout = widgets.Layout(display='flex',
                            flex_flow='column',
                            align_items='stretch',
                            border='dash',
                            width='70%')

box = widgets.Box(children=w, layout=box_layout)
out = widgets.Output()

with out:
    display(box)


submit.on_click(display_results)


out