#!/usr/bin/env python3
"""
NodeServer to extract weather data from the MeteoBridge Hub.  Designed around a DAVIS VP2+ weather station. May work
others, not tested.  At the moment, only DAVIS stations provide ET0 readings.

Based on MeteoBridge nodeserver (meteobridgepoly) authored by Bob Paauwe
Customized to use template queries from MeteoBridge by Gordon Larsen

Copyright 2010 Robert Paauwe and Gordon Larsen, MIT License
"""
#import urllib

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

class MBAuthController(polyinterface.Controller):

    def __init__(self, polyglot):
        super(MBAuthController, self).__init__(polyglot)
        self.hb = 0
        self.name = 'MeteoBridgeAuth'
        self.address = 'mbwxauth'
        self.primary = self.address
        self.password = ""
        self.username = "meteobridge"
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
        self.mb_url, self.mb_handler = self.create_url()

        LOGGER.info('MeteoBridge Template Node Server Started.')

    def shortPoll(self):
        pass

    def longPoll(self):

        # read data
        if self.ip == "":
            return

        self.getstationdata(self.mb_url, self.mb_handler)

        LOGGER.info("Updated data from Meteobridge")

        try:
            self.nodes['temperature'].setDriver(
                uom.TEMP_DRVS['main'], self.temperature
            )
            self.nodes['temperature'].setDriver(
                uom.TEMP_DRVS['dewpoint'],self.dewpoint
            )
            self.nodes['temperature'].setDriver(
                uom.TEMP_DRVS['windchill'], self.windchill
            )
            self.nodes['temperature'].setDriver(
                uom.TEMP_DRVS['tempmax'], self.maxtemp
            )
            self.nodes['temperature'].setDriver(
                uom.TEMP_DRVS['tempmin'], self.mintemp
            )
            self.nodes['rain'].setDriver(
                uom.RAIN_DRVS['rate'], self.rain_rate
            )
            self.nodes['rain'].setDriver(
                uom.RAIN_DRVS['daily'], self.rain_today
            )
            self.nodes['rain'].setDriver(
                uom.RAIN_DRVS['24hour'], self.rain_24hour
            )
            self.nodes['rain'].setDriver(
                uom.RAIN_DRVS['yesterday'], self.rain_yesterday
            )
            self.nodes['rain'].setDriver(
                uom.RAIN_DRVS['monthly'], self.rain_month
            )
            self.nodes['rain'].setDriver(
                uom.RAIN_DRVS['yearly'], self.rain_year
            )
            self.nodes['wind'].setDriver(
                uom.WIND_DRVS['windspeed'], self.wind
            )
            self.nodes['wind'].setDriver(
                uom.WIND_DRVS['winddir'], self.wind_dir
            )
            self.nodes['wind'].setDriver(
                uom.WIND_DRVS['gustspeed'], self.wind_gust
            )
            self.nodes['light'].setDriver(
                uom.LITE_DRVS['solar_radiation'], self.solarradiation
            )
            self.nodes['light'].setDriver(
                uom.LITE_DRVS['uv'], self.uv
            )
            if self.mbstation == "Vantage":
                et0_conv = self.et0
                if self.units == 'us':
                    et0_conv = round(et0_conv / 25.4, 3)

                self.nodes['light'].setDriver(
                    uom.LITE_DRVS['evapotranspiration'], et0_conv
                )
            else:
                LOGGER.info("Evapotranspiration not available (Davis Vantage stations only)")

            self.nodes['pressure'].setDriver(
                uom.PRES_DRVS['station'], self.stn_pressure
            )
            self.nodes['pressure'].setDriver(
                uom.PRES_DRVS['sealevel'], self.sl_pressure
            )
            self.nodes['pressure'].setDriver(
                uom.PRES_DRVS['trend'], self.pressure_trend
            )
            self.nodes['humidity'].setDriver(
                uom.HUMD_DRVS['main'], self.rh
            )
            self.setDriver('GV0', self.battery)
              # value 0 = Ok, 1 = Replace

        except:
            pass

    def query(self, command=None):
        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):

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
        LOGGER.info('NodeServer stopped.')

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
            })

        self.myConfig = self.polyConfig['customParams']

        # Remove all existing notices
        LOGGER.info("remove all notices")
        self.removeNoticesAll()

        # Add a notice?
        if self.ip == "":
            self.addNotice("IP address of the MeteoBridge device is required.")
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
        self.rain_list['24hour'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.rain_list['yesterday'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.rain_list['monthly'] = 'I_MM' if units == 'metric' else 'I_INCHES'
        self.rain_list['yearly'] = 'I_MM' if units == 'metric' else 'I_INCHES'
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
        {'driver': 'GV0', 'value': 0, 'uom': 25},
    ]

    def create_url(self):
        # top_level_url
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

        try:
            # create "opener" (OpenerDirector instance)
            opener = urllib.request.build_opener(handler)

            # use the opener to fetch a URL
            u = opener.open(url)
            mbrdata = u.read().decode('utf-8')

        except urllib.error.HTTPError as e:
            LOGGER.error("Unable to connect to your MeteoBridge hub")

        mbrarray = mbrdata.split(" ")

        try:
            self.temperature = float(mbrarray[0])
            self.maxtemp = float(mbrarray[1])
            self.mintemp = float(mbrarray[2])
            self.dewpoint = float(mbrarray[3])
            self.windchill = float(mbrarray[4])

            self.rh = float(mbrarray[5])
            self.maxrh = float(mbrarray[6])
            self.minrh = float(mbrarray[7])

            self.stn_pressure = float(mbrarray[8])
            self.sl_pressure = float(mbrarray[9])
            self.pressure_trend = float(mbrarray[10])
            self.pressure_trend = self.pressure_trend + 1 # Meteobridge reports -1, 0, +1 for trends,converted for ISY

            self.solarradiation = float(mbrarray[11])  # conversion from watt/sqm*h to Joule/sqm
            # if solarradiation is not None:
            #    solarradiation *= 0.0864
            self.uv = float(mbrarray[12])
            self.et0 = float(mbrarray[13])

            self.wind = float(mbrarray[14])
            # wind = wind * 3.6 # the Meteobridge reports in mps, this is conversion to kph
            self.wind_gust = float(mbrarray[15])
            self.wind_dir = mbrarray[16]

            self.rain_rate = float(mbrarray[17])
            self.rain_today = float(mbrarray[18])
            self.rain_24hour = float(mbrarray[19])
            self.rain_yesterday = float(mbrarray[20])
            self.rain_month = float(mbrarray[21])
            self.rain_year = float(mbrarray[22])


            self.mbstation = mbrarray[23]
            self.mbstationnum = float(mbrarray[24])
            self.battery = round(float(mbrarray[25]),0)

            self.timestamp = int(mbrarray[26])

        except:
            LOGGER.debug("Invalid value")
            LOGGER.debug(mbrarray)


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
            "[thb0press-delta3h=barotrend]", #10 pressure trend
            
            "[sol0rad-act]",  #11 current solar radiation
            "[uv0index-act]",  #12 current UV index
            "[sol0evo-daysum]", #13 today's cumulative evapotranspiration - Davis Vantage only

            "[wind0avgwind-act]", #14 average wind (depends on particular station)
            "[wind0wind-max10]", #15 10 minute wind gust
            "[wind0dir-act]", #16 current wind direction

            "[rain0rate-act]",  # 17 current rate of rainfall
            "[rain0total-daysum]", #18 rain accumulation for today
            "[rain0total-sum24h]", #19 rain over the last 24 hours
            "[rain0total-ydmax]",  # 20 total rainfall yesterday
            "[rain0total-monthsum]",  # 21 rain accumulation for this month
            "[rain0total-yearsum]", #22 rain accumulation year-to-date

            "[mbsystem-station]",  #23 station id
            "[mbsystem-stationnum]",  #24 meteobridge station number
            "[thb0lowbat-act]" #25 Station battery status (0=Ok, 1=Replace)

            "[UYYYY][UMM][UDD][Uhh][Umm][Uss]",  #26 current observation time
            "[epoch]",  #27 current unix time
        ]

        for tempstr in mbtemplatelist:
                mbtemplate = mbtemplate + tempstr + "%20"

        return mbtemplate

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
        super(PrecipitationNode, self).setDriver(driver, round(value,2), report=True, force=True)

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

    def SetUnits(self, u):
        self.units = u

    # We want to override the SetDriver method so that we can properly
    # convert the units based on the user preference.
    def setDriver(self, driver, value):
        if driver != 'GV1':
            if (self.units == 'us'):
                        value = round(value * 0.02952998751, 2)

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
