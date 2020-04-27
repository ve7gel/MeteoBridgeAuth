#!/usr/bin/env python3

import collections
import polyinterface
import re
import os
import zipfile
import json
import uom

LOGGER = polyinterface.LOGGER
pfx = "write_profile:"

VERSION_FILE = "profile/version.txt"

# define templates for the various sensor nodes we have available. Each
# sensor node will have a pre-defined list of drivers. When we build
# the node definition, we get to pick which drivers we include based on
# the user's configuration.


NODEDEF_TMPL = "  <nodeDef id=\"%s\" nls=\"%s\">\n"
STATUS_TMPL = "      <st id=\"%s\" editor=\"%s\" />\n"


# As long as we provide proper dictionary lists for each type of node
# this will generate the node definitions.
#
# Assumes that the NLS exist for the nodes and that the editors exist.

def write_profile(logger, temperature_list, humidity_list, pressure_list,
                  wind_list, rain_list, light_list, lightning_list):
    sd = get_server_data(logger)
    if sd is False:
        logger.error("Unable to complete without server data...")
        return False

    logger.info("{0} Writing profile/nodedef/nodedefs.xml".format(pfx))
    if not os.path.exists("profile/nodedef"):
        try:
            os.makedirs("profile/nodedef")
        except:
            LOGGER.error('unable to create node definition directory.')

    nodedef = open("profile/nodedef/nodedefs.xml", "w")
    nodedef.write("<nodeDefs>\n")

    # First, write the controller node definition
    nodedef.write(NODEDEF_TMPL % ('MeteoBridgeAuth', 'ctl'))
    nodedef.write("    <sts>\n")
    nodedef.write("      <st id=\"ST\" editor=\"bool\" />\n")
    nodedef.write("      <st id=\"GV0\" editor=\"I_BATTERY\" />\n")
    nodedef.write("      <st id=\"GV1\" editor=\"I_BATTERY\" />\n")
    nodedef.write("      <st id=\"GV2\" editor=\"I_LAST_UPDATE\" />\n")
    nodedef.write("      <st id=\"GV3\" editor=\"I_SECONDS\" />\n")
    nodedef.write("      <st id=\"GV4\" editor=\"LOGLEVEL\" />\n")
    nodedef.write("    </sts>\n")
    nodedef.write("    <cmds>\n")
    nodedef.write("      <sends>\n")
    nodedef.write("        <cmd id= \"LOG_LEVEL\" />\n")
    nodedef.write("      </sends>\n")
    nodedef.write("      <accepts>\n")
    nodedef.write("        <cmd id=\"LOG_LEVEL\" >\n")
    nodedef.write("            <p id= \"\" editor= \"LOGLEVEL\" init= \"GV4\"/>\n")
    nodedef.write("        </cmd>\n")
    nodedef.write("        <cmd id=\"DISCOVER\" />\n")
    nodedef.write("        <cmd id=\"REMOVE_NOTICES_ALL\" />\n")
    nodedef.write("        <cmd id=\"UPDATE_PROFILE\" />\n")
    nodedef.write("      </accepts>\n")
    nodedef.write("    </cmds>\n")
    nodedef.write("  </nodeDef>\n\n")

    # Need to translate temperature.main into <st id="ST" editor="TEMP_C" />
    # and     translate temperature.extra1 into <st id="GV5" editor="TEMP_C" />

    if (len(temperature_list) > 0):
        nodedef.write(NODEDEF_TMPL % ('temperature', 'TEMP'))
        nodedef.write("    <sts>\n")
        for t in temperature_list:
            nodedef.write(STATUS_TMPL % (uom.TEMP_DRVS[t], temperature_list[t]))
        nodedef.write("    </sts>\n")
        nodedef.write("  </nodeDef>\n")

    if (len(humidity_list) > 0):
        nodedef.write(NODEDEF_TMPL % ('humidity', 'HUM'))
        nodedef.write("    <sts>\n")
        for t in humidity_list:
            nodedef.write(STATUS_TMPL % (uom.HUMD_DRVS[t], humidity_list[t]))
        nodedef.write("    </sts>\n")
        nodedef.write("  </nodeDef>\n")

    if (len(pressure_list) > 0):
        nodedef.write(NODEDEF_TMPL % ('pressure', 'PRESS'))
        nodedef.write("    <sts>\n")
        for t in pressure_list:
            nodedef.write(STATUS_TMPL % (uom.PRES_DRVS[t], pressure_list[t]))
        nodedef.write("    </sts>\n")
        nodedef.write("  </nodeDef>\n")

    if (len(wind_list) > 0):
        nodedef.write(NODEDEF_TMPL % ('wind', 'WIND'))
        nodedef.write("    <editors   />\n")
        nodedef.write("    <sts>\n")
        for t in wind_list:
            nodedef.write(STATUS_TMPL % (uom.WIND_DRVS[t], wind_list[t]))
        nodedef.write("    </sts>\n")
        nodedef.write("  </nodeDef>\n")

    if (len(rain_list) > 0):
        nodedef.write(NODEDEF_TMPL % ('precipitation', 'RAIN'))
        nodedef.write("    <sts>\n")
        for t in rain_list:
            nodedef.write(STATUS_TMPL % (uom.RAIN_DRVS[t], rain_list[t]))
        nodedef.write("    </sts>\n")
        nodedef.write("  </nodeDef>\n")

    if (len(light_list) > 0):
        nodedef.write(NODEDEF_TMPL % ('light', 'LIGHT'))
        nodedef.write("    <sts>\n")
        for t in light_list:
            nodedef.write(STATUS_TMPL % (uom.LITE_DRVS[t], light_list[t]))
        nodedef.write("    </sts>\n")
        nodedef.write("  </nodeDef>\n")

    if (len(lightning_list) > 0):
        nodedef.write(NODEDEF_TMPL % ('lightning', '139S'))
        nodedef.write("    <sts>\n")
        for t in lightning_list:
            nodedef.write(STATUS_TMPL % (uom.LTNG_DRVS[t], lightning_list[t]))
        nodedef.write("    </sts>\n")
        nodedef.write("  </nodeDef>\n")

    nodedef.write("</nodeDefs>")

    nodedef.close()

    # Update the profile version file with the info from server.json
    with open(VERSION_FILE, 'w') as outfile:
        outfile.write(sd['profile_version'])
    outfile.close()

    # Create the zip file that can be uploaded to the ISY
    write_profile_zip(logger)

    logger.info(pfx + " done.")


def write_profile_zip(logger):
    src = 'profile'
    abs_src = os.path.abspath(src)
    with zipfile.ZipFile('profile.zip', 'w') as zf:
        for dirname, subdirs, files in os.walk(src):
            # Ignore dirs starint with a dot, stupid .AppleDouble...
            if not "/." in dirname:
                for filename in files:
                    if filename.endswith('.xml') or filename.endswith('txt'):
                        absname = os.path.abspath(os.path.join(dirname, filename))
                        arcname = absname[len(abs_src) + 1:]
                        logger.info('write_profile_zip: %s as %s' %
                                    (os.path.join(dirname, filename), arcname))
                        zf.write(absname, arcname)
    zf.close()


def get_server_data(logger):
    # Read the SERVER info from the json.
    try:
        with open('server.json') as data:
            serverdata = json.load(data)
    except Exception as err:
        logger.error('get_server_data: failed to read {0}: {1}'.format('server.json', err), exc_info=True)
        return False
    data.close()
    # Get the version info
    try:
        version = serverdata['credits'][0]['version']
    except (KeyError, ValueError):
        logger.info('Version not found in server.json.')
        version = '0.0.0.0'
    # Split version into two floats.
    sv = version.split(".");
    v1 = 0;
    v2 = 0;
    if len(sv) == 1:
        v1 = int(v1[0])
    elif len(sv) > 1:
        v1 = float("%s.%s" % (sv[0], str(sv[1])))
        if len(sv) == 3:
            v2 = int(sv[2])
        else:
            v2 = float("%s.%s" % (sv[2], str(sv[3])))
    serverdata['version'] = version
    serverdata['version_major'] = v1
    serverdata['version_minor'] = v2
    return serverdata


# If we wanted to call this as a stand-alone script to generate the profile
# files, we'd do something like what's below but we'd need some way to
# set the configuration.

if __name__ == "__main__":
    import logging, json

    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=10,
        format='%(levelname)s:\t%(name)s\t%(message)s'
    )
    logger.setLevel(logging.DEBUG)
