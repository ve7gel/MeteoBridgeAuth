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
import urllib.error
import urllib.request
import write_profile
import uom

LOGGER = polyinterface.LOGGER
"""
polyinterface has a LOGGER that is created by default and logs to:
logs/debug.log
You can use LOGGER.info, LOGGER.warning, LOGGER.debug, LOGGER.error levels as needed.
"""
global temperature, dewpoint, mintemp, maxtemp, rh, minrh, maxrh, wind, solarradiation, et0, rain_today, \
    pressure, pressure_trend, windchill, rain_rate, rain_yesterday, rain_month, wind_gust, wind_dir, uv, sl_pressure, stn_pressure, \
    battery,mbstation,mbstationnum


class MBAuthController(polyinterface.Controller):
    #global temperature, dewpoint, mintemp, maxtemp, rh, minrh, maxrh, wind, solarradiation, et0, rain_today, \
       # pressure, windchill, rain_rate, rain_yesterday, wind_gust, wind_dir

    def __init__(self, polyglot):
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

        # read data
        if self.ip == "":
            return

        mb_url, mb_handler = self.create_url()
        self.getstationdata(mb_url, mb_handler)

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
        self.nodes['light'].setDriver(
            uom.LITE_DRVS['solar_radiation'], solarradiation
        )
        self.nodes['light'].setDriver(
            uom.LITE_DRVS['uv'], uv
        )
        if mbstation == "Vantage":
            self.nodes['light'].setDriver(
                uom.LITE_DRVS['evapotranspiration'], et0
            )
        else:
            LOGGER.info("Evapotranspiration not available (Davis Vantage stations only)")

        self.nodes['pressure'].setDriver(
            uom.PRES_DRVS['station'], stn_pressure
        )
        self.nodes['pressure'].setDriver(
            uom.PRES_DRVS['sealevel'], sl_pressure
        )
        self.nodes['pressure'].setDriver(
            uom.PRES_DRVS['trend'], pressure_trend
        )
        self.nodes['humidity'].setDriver(
            uom.HUMD_DRVS['main'], rh
        )
        if mbstation == "Vantage":
          self.setDriver('GV0', battery)
          # value 0 = Ok, 1 = Replace

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

        node = HumidityNode(self, self.address, 'humidity', 'Humidity')
        node.SetUnits(self.units);
        for d in self.humidity_list:
            node.drivers.append(
                    {
                        'driver': uom.HUMD_DRVS[d],
                        'value': 0,
                        'uom': uom.UOM[self.humidity_list[d]]
                        })
        self.addNode(node)

        node = PressureNode(self, self.address, 'pressure', 'Barometric Pressure')
        node.SetUnits(self.units);
        for d in self.pressure_list:
            node.drivers.append(
                    {
                        'driver': uom.PRES_DRVS[d],
                        'value': 0,
                        'uom': uom.UOM[self.pressure_list[d]]
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

        node = LightNode(self, self.address, 'light', 'Illumination')
        node.SetUnits(self.units);
        for d in self.light_list:
            node.drivers.append(
                    {
                        'driver': uom.LITE_DRVS[d],
                        'value': 0,
                        'uom': uom.UOM[self.light_list[d]]
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
        global mbstation
        # Configure the units for each node driver
        self.temperature_list['main'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['dewpoint'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['windchill'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['tempmax'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.temperature_list['tempmin'] = 'I_TEMP_F' if units == 'us' else 'I_TEMP_C'
        self.humidity_list['main'] = 'I_HUMIDITY'
        self.pressure_list['station'] = 'I_INHG' if units == 'us' else 'I_MB'
        self.pressure_list['sealevel'] = 'I_INHG' if units == 'us' else 'I_MB'
        self.pressure_list['trend'] = 'I_TREND'
        self.wind_list['windspeed'] = 'I_MPS' if units == 'metric' else 'I_MPH'
        self.wind_list['gustspeed'] = 'I_MPS' if units == 'metric' else 'I_MPH'
        self.wind_list['winddir'] = 'I_DEGREE'
        self.rain_list['rate'] = 'I_MMHR' if units == 'metric' else 'I_INHR'
        self.rain_list['daily'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.rain_list['yesterday'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.rain_list['monthly'] = 'I_MM' if units == 'metric' else 'I_INCHES'
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
        {'driver': 'GV0', 'value': 0, 'uom': '25'},
    ]

    def create_url(self):
        # top_level_url = "http://meteobridge.internal.home/"
        top_level_url = "http://" + self.ip + "/"
        # create a password manager
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()

        # Add the username and password.
        password_mgr.add_password(None, top_level_url, self.username, self.password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

        url = top_level_url + "cgi-bin/template.cgi?template="

        values = str(Create_Template())

        return url + values, handler

    def getstationdata(self,url,handler):

        global temperature, dewpoint, mintemp, maxtemp, rh, minrh, maxrh, wind, solarradiation, et0, rain_today, \
            pressure, pressure_trend, windchill, rain_rate, rain_yesterday, rain_month, wind_gust, wind_dir, uv, sl_pressure, stn_pressure, \
            battery, mbstation, mbstationnum

        try:
            # create "opener" (OpenerDirector instance)
            opener = urllib.request.build_opener(handler)

            # use the opener to fetch a URL
            u = opener.open(url)
            mbrdata = u.read().decode('utf-8')
            #LOGGER.debug(url)
            #LOGGER.debug(mbrdata)

        except urllib.error.HTTPError as e:
            LOGGER.error(e, e.headers)
            LOGGER.error("Unable to connect to your MeteoBridge hub")

        mbrarray = mbrdata.split(" ")

        temperature = float(mbrarray[0])
        maxtemp = float(mbrarray[1])
        mintemp = float(mbrarray[2])
        dewpoint = float(mbrarray[3])
        windchill = float(mbrarray[4])

        rh = float(mbrarray[5])
        maxrh = float(mbrarray[6])
        minrh = float(mbrarray[7])

        stn_pressure = float(mbrarray[8])
        sl_pressure = float(mbrarray[9])
        pressure_trend = float(mbrarray[10])
        pressure_trend = pressure_trend + 1 # Meteobridge reports -1, 0, +1 for trends,converted for ISY

        solarradiation = float(mbrarray[11])  # conversion from watt/sqm*h to Joule/sqm
        # if solarradiation is not None:
        #    solarradiation *= 0.0864
        uv = float(mbrarray[12])
        et0 = float(mbrarray[13])

        wind = float(mbrarray[14])
        # wind = wind * 3.6 # the Meteobridge reports in mps, this is conversion to kph
        wind_gust = float(mbrarray[15])
        wind_dir = mbrarray[16]

        rain_rate = float(mbrarray[17])
        rain_today = float(mbrarray[18])
        rain_yesterday = float(mbrarray[19])
        rain_month = float(mbrarray[20])

        mbstation = mbrarray[21]
        mbstationnum = float(mbrarray[22])
        battery = round(float(mbrarray[23]),0)

        timestamp = int(mbrarray[24])

        #LOGGER.debug(str(temperature) + " " + str(et0) + " " + str(mintemp) + " " + str(maxtemp) +
        #          " " + str(rh) + " " + str(wind) + " " + str(solarradiation) + " " + str(pressure_trend))



class Create_Template():

    def __str__(self):
        mbtemplate = ""
        mbtemplatelist = [
            "[th0temp-act]", #0, current outdoor temperature
            "[th0temp-dmax]",  #1, max outdoor temp today
            "[th0temp-dmin]",  #2, min outdoor temp today
            "[th0dew-act]",  #3, current outdoor dewpoint
            "[wind0chill-act]",  #4 current windchill as calculated by MeteoBridge

            "[th0hum-act]",  #5 current outdoor relative humidity
            "[th0hum-dmax]",  #6 max outdoor relative humidity today
            "[th0hum-dmin]",  #7 min outddor relative humidity today

            "[thb0press-act]", #8 current station pressure
            "[thb0seapress-act]",  #9 current sealevel barometric pressure
            "[thb0press-delta60=barotrend]", #10 pressure trend
            
            "[sol0rad-act]",  #11 current solar radiation
            "[uv0index-act]",  #12 current UV index
            "[sol0evo-daysum]", #13 today's evapotranspiration - Davis Vantage only

            "[wind0avgwind-act]", #14 average wind (depends on particular station)
            "[wind0wind-max10]", #15 10 minute wind gust
            "[wind0dir-act]", #16 current wind direction

            "[rain0rate-act]",  # 17 current rate of rainfall
            "[rain0total-daysum]", #18 rain accumulation for today
            "[rain0total-ydmax]",  # 19 total rainfall yesterday
            "[rain0total-monthsum]",  # 20 rain accumulation for this month

            "[mbsystem-station]",  #21 station id
            "[mbsystem-stationnum]",  #22 meteobridge station number
            "[thb0lowbat-act]" #23 Station battery status (0=Ok, 1=Replace)

            "[UYYYY][UMM][UDD][Uhh][Umm][Uss]",  #24 current observation time
            "[epoch]",  #25 current unix time
        ]

        for tempstr in mbtemplatelist:
                mbtemplate = mbtemplate + tempstr + "%20"

        return mbtemplate


class Create_Url():

    def __str__(self):
        # top_level_url = "http://meteobridge.internal.home/"
        top_level_url = "http://" + self.ip + "/"
        # create a password manager
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()

        # Add the username and password.
        password_mgr.add_password(None, top_level_url, self.username, self.password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

        url = top_level_url + "cgi-bin/template.cgi?template="

        values = str(Create_Template())

        return url + values, handler

class TemperatureNode(polyinterface.Node):
    id = 'temperature'
    hint = 0xffffff
    units = 'metric'
    drivers = [ ]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        if (self.units == "us"):
            value = (value * 1.8) + 32  # convert to F

        super(TemperatureNode, self).setDriver(driver, round(value, 1), report=True, force=True)

class PrecipitationNode(polyinterface.Node):
    id = 'precipitation'
    hint = 0xffffff
    units = 'metric'
    drivers = [ ]

    def SetUnits(self, u):
        self.units = u

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


class LightNode(polyinterface.Node):
    id = 'light'
    units = 'metric'
    hint = 0xffffff
    drivers = [ ]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        super(LightNode, self).setDriver(driver, value, report=True, force=True)


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
