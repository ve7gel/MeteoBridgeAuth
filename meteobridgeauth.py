#!/usr/bin/env python3
"""
This is a NodeServer template for Polyglot v2 written in Python2/3
by Einstein.42 (James Milne) milne.james@gmail.com

Based on MeteoBridge nodeserver (meteobridgepoly) authored by Bob Paauwe
Customized to use template queries from MeteoBridge by Gordon Larsen
"""
import urllib

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import time
import struct
import datetime
import threading
import math
import urllib3
import urllib.error
import urllib.request
import requests
import write_profile
import uom

from getstationdata import extract

LOGGER = polyinterface.LOGGER
"""
polyinterface has a LOGGER that is created by default and logs to:
logs/debug.log
You can use LOGGER.info, LOGGER.warning, LOGGER.debug, LOGGER.error levels as needed.
"""

class MBAuthController(polyinterface.Controller):

    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        super(MBAuthController, self).__init__(polyglot)
        self.hb = 0
        self.name = 'MeteoBridgeAuth'
        self.address = 'mbwxauth'
        self.primary = self.address
        self.password = ""
        self.username = ""
        self.ip = ""
        self.units = ""
        self.temperature_list = {}
        self.humidity_list = {}
        self.pressure_list = {}
        self.wind_list = {}
        self.rain_list = {}
        self.light_list = {}
        self.lightning_list = {}
        self.myConfig = {}  # custom parameters

        self.poly.onConfig(self.process_config)

    def start(self):
        LOGGER.info('Started MeteoBridge Template NodeServer')
        self.check_params()
        self.discover()
        LOGGER.info('MeteoBridge Template Node Server Started.')

    def shortPoll(self):
        pass

    def longPoll(self):
        global mbrdata

        # read data
        if self.ip == "":
            return
        try:
            #top_level_url = "http://meteobridge.internal.home/"
            top_level_url = "http://" + self.ip + "/"
            # create a password manager
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()

            # Add the username and password.
            password_mgr.add_password(None, top_level_url, self.username, self.password)
            handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

            url = top_level_url + "cgi-bin/template.cgi?template="

            values = '[th0temp-act]%20[th0hum-act]%20[thb0press-act]%20[sol0evo-act]%20[mbsystem-latitude]%20' \
                     '[mbsystem-longitude]%20[th0temp-dmax]%20[th0temp-dmin]%20[th0hum-dmax]%20' \
                     '[th0hum-dmin]%20[wind0avgwind-davg]%20[sol0rad-act]%20[rain0total-daysum]%20' \
                     '[th0dew-act]%20[UYYYY][UMM][UDD][Uhh][Umm][Uss]%20[epoch]%20[wind0chill-act]%20' \
                     '[rain0rate-act]%20[rain0total-ydmax]%20[wind0wind-max10]%20[wind0dir-act]%20[rain0total-aavg]'

            try:
                # create "opener" (OpenerDirector instance)
                opener = urllib.request.build_opener(handler)

                # use the opener to fetch a URL
                u = opener.open(url + values)
                mbrdata = u.read().decode('utf-8')
                LOGGER.debug(url + values)
                LOGGER.debug(mbrdata)

            except urllib.error.HTTPError as e:
                LOGGER.error(e, e.headers)
        except:
            LOGGER.error("Failue attempting connect to MeteoBridge device")

            extract(mbrdata)

        LOGGER.info("Updated data from Meteobridge")

        self.nodes['temperature'].setDriver(
            uom.TEMP_DRVS['main'], temperature
        )
        self.nodes['temperature'].setDriver(
            uom.TEMP_DRVS['dewpoint'],dewpoint
        )
        self.nodes['temperature'].setDriver(
            uom.TEMP_DRVS['windchill'], windchill
        )
        self.nodes['temperature'].setDriver(
            uom.TEMP_DRVS['tempmax'], maxtemp
        )
        self.nodes['temperature'].setDriver(
            uom.TEMP_DRVS['tempmin'], mintemp
        )
        self.nodes['rain'].setDriver(
            uom.RAIN_DRVS['rate'], rain_rate
        )
        self.nodes['rain'].setDriver(
            uom.RAIN_DRVS['daily'], rain_today
        )
        self.nodes['rain'].setDriver(
            uom.RAIN_DRVS['yesterday'], rain_yesterday
        )
        self.nodes['wind'].setDriver(
            uom.WIND_DRVS['windspeed'], wind
        )
        self.nodes['wind'].setDriver(
            uom.WIND_DRVS['winddir'], wind_dir
        )
        self.nodes['wind'].setDriver(
            uom.WIND_DRVS['gustspeed'], wind_gust
        )
        return

    def query(self, command=None):
        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        """
        Add nodes for basic sensor type data
                - Temperature (temp, dewpoint, heat index, wind chill, feels)
                - Humidity
                - Pressure (abs, sealevel, trend)
                - Wind (speed, gust, direction, gust direction, etc.)
                - Precipitation (rate, hourly, daily, weekly, monthly, yearly)
                - Light (UV, solar radiation, lux)
                - Lightning (strikes, distance)
        The nodes need to have thier drivers configured based on the user
        supplied configuration. To that end, we should probably create the
        node, update the driver list, set the units and then add the node.
        """
        LOGGER.info("Creating nodes.")
        node = TemperatureNode(self, self.address, 'temperature', 'Temperatures')
        node.SetUnits(self.units);
        for d in self.temperature_list:
            node.drivers.append(
                {
                    'driver': uom.TEMP_DRVS[d],
                    'value': 0,
                    'uom': uom.UOM[self.temperature_list[d]]
                })
        self.addNode(node)

        node = PrecipitationNode(self, self.address, 'rain', 'Precipitation')
        node.SetUnits(self.units);
        for d in self.rain_list:
            node.drivers.append(
                    {
                        'driver': uom.RAIN_DRVS[d],
                        'value': 0,
                        'uom': uom.UOM[self.rain_list[d]]
                        })
        self.addNode(node)

        node = WindNode(self, self.address, 'wind', 'Wind')
        node.SetUnits(self.units);
        for d in self.wind_list:
            node.drivers.append(
                {
                    'driver': uom.WIND_DRVS[d],
                    'value': 0,
                    'uom': uom.UOM[self.wind_list[d]]
                })
        self.addNode(node)

    def delete(self):
        self.stopping = True
        LOGGER.info('Removing MeteoBridge Template nodeserver.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def process_config(self, config):
        if 'customParams' in config:
            if config['customParams'] != self.myConfig:
                # Configuration has changed, we need to handle it
                LOGGER.info('New configuration, updating configuration')
                self.set_configuration(config)
                self.setup_nodedefs(self.units)
                self.discover()
                self.myConfig = config['customParams']

                # Remove all existing notices
                self.removeNoticesAll()

                # Add notices about missing configuration
                if self.ip == "":
                    self.addNotice("IP address of the MeteoBridge device is required.")

    def check_params(self):
        self.set_configuration(self.polyConfig)
        self.setup_nodedefs(self.units)

        # Make sure they are in the params  -- does this cause a
        # configuration event?
        LOGGER.info("Adding configuration")
        self.addCustomParam({
            'IPAddress': self.ip,
            'Units': self.units,
            'Password': self.password,
            'Username': self.username
        })

        self.myConfig = self.polyConfig['customParams']

        # Remove all existing notices
        LOGGER.info("remove all notices")
        self.removeNoticesAll()

        # Add a notice?
        if self.ip == "":
            self.addNotice("IP address of the MeteoBridge device is required.")
        if self.username == "":
            self.addNotice("Username for the MeteoBridge device is required.")
        if self.password == "":
            self.addNotice("Password for MeteoBridge is required.")

    def set_configuration(self, config):
        default_ip = ""
        default_elevation = 0

        LOGGER.info("Check for existing configuration value")

        if 'IPAddress' in config['customParams']:
            self.ip = config['customParams']['IPAddress']
        else:
            self.ip = default_ip

        if 'Units' in config['customParams']:
            self.units = config['customParams']['Units'].lower()
        else:
            self.units = 'metric'

        if 'Password' in config['customParams']:
            self.password = config['customParams']['Password']
        else:
            self.password = ""

        if 'Username' in config['customParams']:
            self.username = config['customParams']['Username']
        else:
            self.username = ""

        return self.units

    def setup_nodedefs(self, units):

        # Configure the units for each node driver
        self.temperature_list['main'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['dewpoint'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['windchill'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['tempmax'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['tempmin'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.humidity_list['main'] = 'I_HUMIDITY'
        self.pressure_list['station'] = 'I_INHG' if units == 'us' else 'I_MB'
        self.pressure_list['sealevel'] = 'I_INHG' if units == 'us' else 'I_MB'
        self.wind_list['windspeed'] = 'I_MPS' if units == 'metric' else 'I_MPH'
        self.wind_list['gustspeed'] = 'I_MPS' if units == 'metric' else 'I_MPH'
        self.wind_list['winddir'] = 'I_DEGREE'
        self.rain_list['rate'] = 'I_MMHR' if units == 'metric' else 'I_INHR'
        self.rain_list['total'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.rain_list['daily'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.rain_list['yesterday'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.light_list['uv'] = 'I_UV'
        self.light_list['solar_radiation'] = 'I_RADIATION'
        self.light_list['evapotranspiration'] = 'I_MM' if units == 'metric' else 'I_INCHES'

        # Build the node definition
        LOGGER.info('Creating node definition profile based on config.')
        write_profile.write_profile(LOGGER, self.temperature_list,
                self.humidity_list, self.pressure_list, self.wind_list,
                self.rain_list, self.light_list, self.lightning_list)

        # push updated profile to ISY
        try:
            self.poly.installprofile()
        except:
            LOGGER.error('Failed to push profile to ISY')


    def remove_notices_all(self, command):
        LOGGER.info('remove_notices_all: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self, command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    def SetUnits(self, u):
        self.units = u

    id = 'MeteoBridgeAuth'
    name = 'MeteoBridgeAuth'
    address = 'mbwxauth'
    stopping = False
    hint = 0xffffff
    units = 'metric'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
    }
    # Hub status information here: battery and rssi values.
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 72},
    ]

class TemperatureNode(polyinterface.Node):
    id = 'temperature'
    hint = 0xffffff
    units = 'metric'
    drivers = [ ]

    def SetUnits(self, u):
        self.units = u

    def Dewpoint(self, t, h):
        b = (17.625 * t) / (243.04 + t)
        rh = h / 100.0
        c = math.log(rh)
        dewpt = (243.04 * (c + b)) / (17.625 - c - b)
        return round(dewpt, 1)

    def ApparentTemp(self, t, ws, h):
        wv = h / 100.0 * 6.105 * math.exp(17.27 * t / (237.7 + t))
        at =  t + (0.33 * wv) - (0.70 * ws) - 4.0
        return round(at, 1)

    def Windchill(self, t, ws):
        # really need temp in F and speed in MPH
        tf = (t * 1.8) + 32
        mph = ws / 0.44704

        wc = 35.74 + (0.6215 * tf) - (35.75 * math.pow(mph, 0.16)) + (0.4275 * tf * math.pow(mph, 0.16))

        if (tf <= 50.0) and (mph >= 5.0):
            return round((wc - 32) / 1.8, 1)
        else:
            return t

    def Heatindex(self, t, h):
        tf = (t * 1.8) + 32
        c1 = -42.379
        c2 = 2.04901523
        c3 = 10.1433127
        c4 = -0.22475541
        c5 = -6.83783 * math.pow(10, -3)
        c6 = -5.481717 * math.pow(10, -2)
        c7 = 1.22874 * math.pow(10, -3)
        c8 = 8.5282 * math.pow(10, -4)
        c9 = -1.99 * math.pow(10, -6)

        hi = (c1 + (c2 * tf) + (c3 * h) + (c4 * tf * h) + (c5 * tf *tf) + (c6 * h * h) + (c7 * tf * tf * h) + (c8 * tf * h * h) + (c9 * tf * tf * h * h))

        if (tf < 80.0) or (h < 40.0):
            return t
        else:
            return round((hi - 32) / 1.8, 1)

    def setDriver(self, driver, value):
        if (self.units == "us"):
            value = (value * 1.8) + 32  # convert to F

        super(TemperatureNode, self).setDriver(driver, round(value, 1), report=True, force=True)

class PrecipitationNode(polyinterface.Node):
    id = 'precipitation'
    hint = 0xffffff
    units = 'metric'
    drivers = [ ]
    hourly_rain = 0
    daily_rain = 0
    weekly_rain = 0
    monthly_rain = 0
    yearly_rain = 0

    prev_hour = 0
    prev_day = 0
    prev_week = 0

    def SetUnits(self, u):
        self.units = u

    def hourly_accumulation(self, r):
        current_hour = datetime.datetime.now().hour
        if (current_hour != self.prev_hour):
            self.prev_hour = current_hour
            self.hourly = 0

        self.hourly_rain += r
        return self.hourly_rain

    def daily_accumulation(self, r):
        current_day = datetime.datetime.now().day
        if (current_day != self.prev_day):
            self.prev_day = current_day
            self.daily_rain = 0

        self.daily_rain += r
        return self.daily_rain

    def weekly_accumulation(self, r):
        current_week = datetime.datetime.now().day
        if (current_weekday != self.prev_weekday):
            self.prev_week = current_weekday
            self.weekly_rain = 0

        self.weekly_rain += r
        return self.weekly_rain

    def setDriver(self, driver, value):
        if (self.units == 'us'):
            value = round(value * 0.03937, 2)
        super(PrecipitationNode, self).setDriver(driver, round(value,1), report=True, force=True)

class HumidityNode(polyinterface.Node):
    id = 'humidity'
    hint = 0xffffff
    units = 'metric'
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 22}]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        super(HumidityNode, self).setDriver(driver, value, report=True, force=True)

class PressureNode(polyinterface.Node):
    id = 'pressure'
    hint = 0xffffff
    units = 'metric'
    drivers = [ ]
    mytrend = []


    def SetUnits(self, u):
        self.units = u

    # convert station pressure in millibars to sealevel pressure
    def toSeaLevel(self, station, elevation):
        i = 287.05
        a = 9.80665
        r = 0.0065
        s = 1013.35 # pressure at sealevel
        n = 288.15

        l = a / (i * r)
        c = i * r / a
        u = math.pow(1 + math.pow(s / station, c) * (r * elevation / n), l)

        return (round((station * u), 3))

    # track pressures in a queue and calculate trend
    def updateTrend(self, current):
        t = 0
        past = 0

        if len(self.mytrend) == 180:
            past = self.mytrend.pop()

        if self.mytrend != []:
            past = self.mytrend[0]

        # calculate trend
        if ((past - current) > 1):
            t = -1
        elif ((past - current) < -1):
            t = 1

        self.mytrend.insert(0, current)
        return t

    # We want to override the SetDriver method so that we can properly
    # convert the units based on the user preference.
    def setDriver(self, driver, value):
        if (self.units == 'us'):
            value = round(value * 0.02952998751, 3)
        super(PressureNode, self).setDriver(driver, value, report=True, force=True)


class WindNode(polyinterface.Node):
    id = 'wind'
    hint = 0xffffff
    units = 'metric'
    drivers = [ ]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        if (driver == 'ST' or driver == 'GV1' or driver == 'GV3'):
            # Metric value is meters/sec (not KPH)
            if (self.units != 'metric'):
                value = round(value * 2.23694, 2)
        super(WindNode, self).setDriver(driver, value, report=True, force=True)

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('MeteoBridgeAuth')
        """
        Instantiates the Interface to Polyglot.
        """
        polyglot.start()
        """
        Starts MQTT and connects to Polyglot.
        """
        control = MBAuthController(polyglot)
        """
        Creates the Controller Node and passes in the Interface
        """
        control.runForever()
        """
        Sits around and does nothing forever, keeping your program running.
        """
    except (KeyboardInterrupt, SystemExit):
        LOGGER.warning("Received interrupt or exit...")
        """
        Catch SIGTERM or Control-C and exit cleanly.
        """
        polyglot.stop()
    except Exception as err:
        LOGGER.error('Exception: {0}'.format(err), exc_info=True)
    sys.exit(0)
