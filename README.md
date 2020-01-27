# MeteoBridgeAuth
Nodeserver to acquire data using templates from Meteobridge 
weather server.  Requires authorization thus entry of username
and password.  This nodeserver is an adaptation of the
meteobridgepoly nodeserver written by [Bob Pauuwe](http://www.bobsplace.com).

This node server is designed to support the [Meteobridge](http://www.meteobridge.com/)
in combination with a [Davis Instruments Vantage Pro 2+](https://www.davisinstruments.com/solution/vantage-pro2/) weather station
It should run with other Meteobridge connected weather stations, but 
the evapotranspiration values provided by the VP2+ will be missing
 
## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Add NodeServer in Polyglot Web
   * After the install completes, Polyglot will reboot your ISY, you can watch the status in the main polyglot log.
4. Once your ISY is back up open the Admin Console.
5. The node server should automatically run and find your hub(s) and start adding weather sensors.  It can take a couple of minutes to discover the sensors. Verify by checking the nodeserver log. 
   * While this is running you can view the nodeserver log in the Polyglot UI to see what it's doing

### Node Settings
The settings for this node are:

#### Short Poll
   * Not used
#### Long Poll
   * How often the MeteoBridge is polled for data
#### Password
   * Password associated with above username
#### IPAddress
   * Configure the IP address of the MeteoBridge.
#### Units
   * Configure the units used when displaying data. Choices are:
   *   metric - SI / metric units
   *   us     - units generally used in the U.S.



## Requirements

1. Polyglot V2 itself should be run on Raspian Stretch.
  To check your version, ```cat /etc/os-release``` and the first line should look like
  ```PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"```. It is possible to upgrade from Jessie to
  Stretch, but I would recommend just re-imaging the SD card.  Some helpful links:
   * https://www.raspberrypi.org/blog/raspbian-stretch/
   * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
2. This NS has been tested and verified for compatibility with UDI Polisy.
3. This has only been tested with ISY 5.0.16b so it is not guaranteed to work with any other version.

# Upgrading

Open the Polyglot web page, go to nodeserver store and click "Update" for "MeteoBridge".

Then restart the MeteoBridge nodeserver by selecting it in the Polyglot dashboard and select Control -> Restart, then watch the log to make sure everything goes well.

The MeteoBridge nodeserver keeps track of the version number and when a profile rebuild is necessary.  The profile/version.txt will contain the MeteoBridge profile_version which is updated in server.json when the profile should be rebuilt.

# Release Notes
- 1.0.6 27/01/2020
    - add a 'longPoll' in start() to immediately populate node fields 
- 1.0.5 20/01/2020
    - add some error trapping for bad/missing values from Meteobridge
- 1.0.4 18/01/2020
   - move create_url call to the start method.  There's no need to re-create it during each longpoll.
- 1.0.3 17/01/2020
   - made some corrections to README.md
   - fixed pressure trend display for "us" units
   - added 24 hour rainfall data 
- 1.0.2 17/01/2020
   - add missing conversion to "us" units for evapotranspiration
   - add missing monthly rainfall data
- 1.0.1 17/01/2020 
    - remove custom parameter for username, it is hard coded as
 "meteobridge" in the MeteoBridge.
    - fixed missing driver update for monthly rainfall
    - added yearly rainfall accumulation
- 1.0.0 16/01/2020
   - Initial alpha release
