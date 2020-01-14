#!/usr/bin/env python3

class extractarray:

    def extract(self, mbrcontent):
        global temperature, dewpoint, mintemp, maxtemp, rh, minrh, maxrh, wind, solarradiation, et0, rain_today, \
            pressure, windchill, rain_rate, rain_yesterday, wind_gust, wind_dir

        mbrarray = mbrcontent.split(" ")

        lat = float(mbrarray[4])
        long = float(mbrarray[5])

        temperature = float(mbrarray[0])
        et0 = float(mbrarray[3])
        mintemp = float(mbrarray[7])
        maxtemp = float(mbrarray[6])
        rh = float(mbrarray[1])
        minrh = float(mbrarray[9])
        maxrh = float(mbrarray[8])
        wind = float(mbrarray[10])
        # wind = wind / 3.6 # the Meteobridge already reports in mps so conversion is not required
        solarradiation = float(mbrarray[11])  # needs to be converted from watt/sqm*h to Joule/sqm

        # if solarradiation is not None:
        #    solarradiation *= 0.0864
        # LOGGER.debug(str(temperature) + " " + str(et0) + " " + str(mintemp) + " " + str(maxtemp) +
        #          " " + str(rh) + " " + str(wind) + " " + str(solarradiation))

        rain_today = float(mbrarray[12])
        dewpoint = float(mbrarray[13])
        pressure = float(mbrarray[2]) / 10
        timestamp = int(mbrarray[15])
        windchill = float(mbrarray[16])
        # rain_rate = float(mbrarray[17])
        rain_rate = 17.0
        rain_yesterday = float(mbrarray[18])
        wind_gust = float(mbrarray[19])
        wind_dir = mbrarray[20]



