# !/usr/bin/env python3
"""
NodeServer to extract weather data from a Meteobridge Weather device.  Designed around a DAVIS VP2+ weather station. May work
others, not tested.  At the moment, only DAVIS stations provide ET0 readings.

Based on MeteoBridge nodeserver (meteobridgepoly) authored by Bob Paauwe
Customized to use template queries from MeteoBridge by Gordon Larsen

Copyright 2020 Robert Paauwe and Gordon Larsen, MIT License
"""

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import write_profile
import uom
import requests

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
        self.name = 'MeteoBridge Weather'
        self.address = 'mbweather'
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
        self.currentloglevel = 10
        self.loglevel = {
            0: 'None',
            10: 'Debug',
            20: 'Info',
            30: 'Error',
            40: 'Warning',
            50: 'Critical'
        }
        self.wind_card_dict = {
            'N': 0,
            'NNE': 1,
            'NE': 2,
            'ENE': 3,
            'E': 4,
            'ESE': 5,
            'SE': 6,
            'SSE': 7,
            'S': 8,
            'SSW': 9,
            'SW': 10,
            'WSW': 11,
            'W': 12,
            'WNW': 13,
            'NW': 14,
            'NNW': 15
        }

        self.poly.onConfig(self.process_config)
        self.vp2plus = False
        self.uvpresent = False
        self.lastgooddata = None

    def start(self):
        LOGGER.info('Started MeteoBridge Template NodeServer')
        self.check_params()

        self.discover()
        if self.ip is not "":
            self.getstationdata(self.ip, self.username, self.password)
            self.set_drivers()

    def shortPoll(self):
        pass

    def longPoll(self):

        # read data
        if self.ip is "":
            return

        self.getstationdata(self.ip, self.username, self.password)
        self.set_drivers()
        LOGGER.info("Updated data from Meteobridge")

    def set_drivers(self):
        try:
            self.nodes['temperature'].setDriver(
                uom.TEMP_DRVS['main'], self.temperature
            )
            self.nodes['temperature'].setDriver(
                uom.TEMP_DRVS['dewpoint'], self.dewpoint
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
            self.nodes['wind'].setDriver(
                uom.WIND_DRVS['windspeed1'], self.wind
            )
            self.nodes['wind'].setDriver(
                uom.WIND_DRVS['gustspeed1'], self.wind_gust
            )
            self.nodes['wind'].setDriver(
                uom.WIND_DRVS['winddircard'], self.wind_dir_cardinal
            )
            self.nodes['light'].setDriver(
                uom.LITE_DRVS['solar_radiation'], self.solarradiation
            )
            if self.uvpresent:
                self.nodes['light'].setDriver(uom.LITE_DRVS['uv'], self.uv
                                              )
            else:
                self.nodes['light'].setDriver(
                    uom.LITE_DRVS['uv'], 0
                )
            if self.vp2plus:
                et0_conv = self.et0
                if self.units == 'us':
                    et0_conv = round(et0_conv / 25.4, 3)

                self.nodes['light'].setDriver(
                    uom.LITE_DRVS['evapotranspiration'], et0_conv
                )
            else:
                self.nodes['light'].setDriver(uom.LITE_DRVS['evapotranspiration'], 0
                                              )
                LOGGER.info("Evapotranspiration not available (Davis Vantage stations with Solar Sensor only)")

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

            # Update controller drivers now
            self.setDriver('GV3', self.lastgooddata)
            self.setDriver('GV0', self.battery)
            self.setDriver('GV1', self.issbattery)
            # value 0 = Ok, 1 = Replace
            self.setDriver('GV2', self.timestamp)

            LOGGER.debug("Last good data: {} second(s) ago".format(self.lastgooddata))

        except ValueError as e:
            LOGGER.error("Error in assigning driver values from template: {}".format(e))

    def query(self, command=None):
        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):

        LOGGER.info("Creating nodes.")
        node = TemperatureNode(self, self.address, 'temperature', 'Temperatures')
        node.SetUnits(self.units)
        for d in self.temperature_list:
            node.drivers.append(
                {
                    'driver': uom.TEMP_DRVS[d],
                    'value': 0,
                    'uom': uom.UOM[self.temperature_list[d]]
                })
        self.addNode(node)

        node = HumidityNode(self, self.address, 'humidity', 'Humidity')
        node.SetUnits(self.units)
        for d in self.humidity_list:
            node.drivers.append(
                {
                    'driver': uom.HUMD_DRVS[d],
                    'value': 0,
                    'uom': uom.UOM[self.humidity_list[d]]
                })
        self.addNode(node)

        node = PressureNode(self, self.address, 'pressure', 'Barometric Pressure')
        node.SetUnits(self.units)
        for d in self.pressure_list:
            node.drivers.append(
                {
                    'driver': uom.PRES_DRVS[d],
                    'value': 0,
                    'uom': uom.UOM[self.pressure_list[d]]
                })
        self.addNode(node)

        node = WindNode(self, self.address, 'wind', 'Wind')
        node.SetUnits(self.units)
        for d in self.wind_list:
            node.drivers.append(
                {
                    'driver': uom.WIND_DRVS[d],
                    'value': 0,
                    'uom': uom.UOM[self.wind_list[d]]
                })
        self.addNode(node)
        LOGGER.debug("Wind nodes: {}".format(node.drivers))

        node = PrecipitationNode(self, self.address, 'rain', 'Precipitation')
        node.SetUnits(self.units)
        for d in self.rain_list:
            node.drivers.append(
                {
                    'driver': uom.RAIN_DRVS[d],
                    'value': 0,
                    'uom': uom.UOM[self.rain_list[d]]
                })
        self.addNode(node)

        node = LightNode(self, self.address, 'light', 'Illumination')
        node.SetUnits(self.units)
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
                if self.ip is "":
                    self.addNotice("IP address or hostname of the MeteoBridge device is required.")

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

        if 'Loglevel' in self.polyConfig['customData']:
            self.currentloglevel = self.polyConfig['customData']['Loglevel']
            LOGGER.debug(
                "Custom data: {0}, currentloglevel: {1}".format(self.polyConfig['customData'], self.currentloglevel))

            LOGGER.setLevel(int(self.currentloglevel))
            self.setDriver('GV4', self.currentloglevel)

        else:
            LOGGER.debug("Custom data: {}".format(self.polyConfig['customData']))
            self.currentloglevel = 10
            self.saveCustomData({
                'Loglevel': self.currentloglevel,  # set default loglevel to 'Debug'
            })
            LOGGER.setLevel(self.currentloglevel)
            self.setDriver('GV4', self.currentloglevel)

        # Remove all existing notices
        LOGGER.info("remove all notices")
        self.removeNoticesAll()

        # Add a notice?
        if self.ip is "":
            self.addNotice("IP address or hostname of your MeteoBridge device is required.")
        if self.password == "":
            self.addNotice("Password for your MeteoBridge is required.")

    def set_configuration(self, config):

        LOGGER.info("Check for existing configuration value")

        if 'IPAddress' in config['customParams']:
            self.ip = config['customParams']['IPAddress']
        else:
            self.ip = ""

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
        self.wind_list['winddircard'] = 'I_CARDINAL'
        if units == 'metric':
            self.wind_list['windspeed1'] = 'I_KPH'
            self.wind_list['gustspeed1'] = 'I_KPH'

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

    def set_loglevel(self, command):
        LOGGER.info("Received command {} in 'set_log_level'".format(command))
        self.currentloglevel = int(command.get('value'))
        self.saveCustomData({
            'Loglevel': self.currentloglevel,
        })
        LOGGER.setLevel(int(self.currentloglevel))
        LOGGER.info("Set Logging Level to {}".format(self.loglevel[self.currentloglevel]))
        self.setDriver('GV4', self.currentloglevel)

    id = 'MeteoBridgeAuth'

    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
        'LOG_LEVEL': set_loglevel,
    }
    # Hub status information here: battery and data health values.
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 25},
        {'driver': 'GV1', 'value': 0, 'uom': 25},
        {'driver': 'GV2', 'value': 0, 'uom': 0},
        {'driver': 'GV3', 'value': 0, 'uom': 58},
        {'driver': 'GV4', 'value': 0, 'uom': 25},
    ]

    def getstationdata(self, ipaddr, username, password):
        """
            Here we assemble the url and template for the call to the Meteobridge
            and then unpack the returned data into variables. Simplified in Version 1.2.5 to
            streamline the basic auth method in requests.get
        """
        try:
            values = str(CreateTemplate())
            url = 'http://' + ipaddr + '/cgi-bin/template.cgi?template='
            LOGGER.debug("url in getstationdata: {}".format(url + values))

            u = requests.get(url + values, auth=(username, password))
            mbrdata = u.content.decode('utf-8')

        except OSError as err:
            LOGGER.error("Unable to connect to your MeteoBridge device")
            LOGGER.error(err)
            return

        mbrarray = mbrdata.split(" ")
        LOGGER.debug("mbrarray: {}".format(mbrarray))

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
            self.pressure_trend = self.pressure_trend + 1  # Meteobridge reports -1, 0, +1 for trends,converted for ISY

            try:
                self.uv = float(mbrarray[12])
                self.uvpresent = True

            except:  # no uv sensor
                self.uv = 0
                self.uvpresent = False

            try:
                self.solarradiation = float(mbrarray[11])
                self.et0 = float(mbrarray[13])
                self.vp2plus = True

            except:  # catch case where solar data is not available
                self.vp2plus = False
                self.solarradiation = 0
                self.et0 = 0

            self.wind = float(mbrarray[14])
            # wind = wind * 3.6 # the Meteobridge reports in mps, this is conversion to kph
            self.wind_gust = float(mbrarray[15])
            self.wind_dir = mbrarray[16]
            self.wind_dir_cardinal = self.wind_card_dict[mbrarray[17]]
            LOGGER.debug(
                "mbr wind: {}, gust: {}, dir: {}, wdc: {}, wind_dir_cardinal: {}".format(self.wind, self.wind_gust,
                                                                                         self.wind_dir, mbrarray[17],
                                                                                         self.wind_dir_cardinal))
            self.rain_rate = float(mbrarray[18])
            self.rain_today = float(mbrarray[19])
            self.rain_24hour = float(mbrarray[20])
            self.rain_yesterday = float(mbrarray[21])
            self.rain_month = float(mbrarray[22])
            self.rain_year = float(mbrarray[23])

            self.mbstation = mbrarray[24]
            self.mbstationnum = float(mbrarray[25])

            self.battery = int(float(mbrarray[26]))
            self.issbattery = int(float(mbrarray[27]))
            self.timestamp = int(mbrarray[28])
            self.lastgooddata = mbrarray[30]
            LOGGER.debug("Timestamp: {}, good data: {}".format(self.timestamp, self.lastgooddata))

        except ValueError or AttributeError as e:
            LOGGER.error("Error in getstationdata: {}".format(e))
            LOGGER.debug("Invalid value")
            LOGGER.debug(mbrarray)


class CreateTemplate:

    def __str__(self):
        mbtemplate = ""
        mbtemplatelist = [
            "[th0temp-act]",  # 0, current outdoor temperature
            "[th0temp-dmax]",  # 1, max outdoor temp today
            "[th0temp-dmin]",  # 2, min outdoor temp today
            "[th0dew-act]",  # 3, current outdoor dewpoint
            "[wind0chill-act]",  # 4 current windchill as calculated by MeteoBridge

            "[th0hum-act]",  # 5 current outdoor relative humidity
            "[th0hum-dmax]",  # 6 max outdoor relative humidity today
            "[th0hum-dmin]",  # 7 min outddor relative humidity today

            "[thb0press-act]",  # 8 current station pressure
            "[thb0seapress-act]",  # 9 current sealevel barometric pressure
            "[thb0press-delta3h=barotrend]",  # 10 pressure trend

            "[sol0rad-act]",  # 11 current solar radiation
            "[uv0index-act]",  # 12 current UV index
            "[sol0evo-daysum]",  # 13 today's cumulative evapotranspiration - Davis Vantage only

            "[wind0avgwind-act]",  # 14 average wind (depends on particular station)
            "[wind0wind-max10]",  # 15 10 minute wind gust
            "[wind0dir-act]",  # 16 current wind direction
            "[wind0dir-act=endir]",  # 17 current cardinal wind direction

            "[rain0rate-act]",  # 18 current rate of rainfall
            "[rain0total-daysum]",  # 19 rain accumulation for today
            "[rain0total-sum24h]",  # 20 rain over the last 24 hours
            "[rain0total-ydmax]",  # 21 total rainfall yesterday
            "[rain0total-monthsum]",  # 22 rain accumulation for this month
            "[rain0total-yearsum]",  # 23 rain accumulation year-to-date

            "[mbsystem-station]",  # 24 station id
            "[mbsystem-stationnum]",  # 25 meteobridge station number
            "[thb0lowbat-act]",  # 26 Station battery status (0=Ok, 1=Replace)
            "[th0lowbat-act]",  # 27 Station battery status (0=Ok, 1=Replace)

            #  "[UYYYY][UMM][UDD][Uhh][Umm][Uss]",  # 28 current observation time
            "[hh][mm][ss]",
            "[epoch]",  # 29 current unix time
            "[mbsystem-lastgooddata]",  # 30 seconds since last good data received from console
        ]

        for tempstr in mbtemplatelist:
            mbtemplate = mbtemplate + tempstr + "%20"

        return mbtemplate.strip("%20")


class TemperatureNode(polyinterface.Node):
    id = 'temperature'
    units = 'metric'
    drivers = []
    hint = [1, 0x0b, 1, 0]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        if (self.units == "us"):
            value = (value * 1.8) + 32  # convert to F

        super(TemperatureNode, self).setDriver(driver, round(value, 1), report=True, force=True)


class PrecipitationNode(polyinterface.Node):
    id = 'precipitation'
    units = 'metric'
    drivers = []
    hint = [1, 0x0b, 5, 0]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        if (self.units == 'us'):
            value = round(value * 0.03937, 2)
        super(PrecipitationNode, self).setDriver(driver, round(value, 2), report=True, force=True)


class HumidityNode(polyinterface.Node):
    id = 'humidity'
    units = 'metric'
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 22}]
    hint = [1, 0x0b, 2, 0]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        super(HumidityNode, self).setDriver(driver, value, report=True, force=True)


class PressureNode(polyinterface.Node):
    id = 'pressure'
    units = 'metric'
    drivers = []
    hint = [1, 0x0b, 3, 0]

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
    units = 'metric'
    drivers = []
    hint = [1, 0x0b, 4, 0]

    def SetUnits(self, u):
        self.units = u

    def setDriver(self, driver, value):
        if driver == 'ST' or driver == 'GV0':
            # Metric value is meters/sec (not KPH)
            if self.units != 'metric':
                value = round(value * 2.23694, 2)
        if (driver == 'GV3' or driver == 'GV4'):
            # Alternate metric value is KPH)
            if (self.units == 'metric'):
                value = round(value * 3.6, 1)
        super(WindNode, self).setDriver(driver, value, report=True, force=True)


class LightNode(polyinterface.Node):
    id = 'light'
    units = 'metric'
    drivers = []
    hint = [1, 0x0b, 6, 0]

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
