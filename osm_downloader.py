#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2013 Simone F. <groppo8@gmail.com>
#
#  This file is part of wikipedia-tags-in-osm.
#  wikipedia-tags-in-osm is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  wikipedia-tags-in-osm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with wikipedia-tags-in-osm.  If not, see <http://www.gnu.org/licenses/>.

"""Modules for downloading, updating and filtering OSM data
"""

import os
import sys
from subprocess import call


### Download/update OSM data ###########################################
def download_osm_data(app):
    """Download OSM data from GEOFABRIK, in PBF format
    """
    print "\n- Download data of the country from Geofabrik ..."
    if os.path.isfile(app.countryPBF):
        call('mv %s %s' % (app.countryPBF, app.oldCountryPBF), shell=True)
    url = "http://download.geofabrik.de/europe/%s-latest.osm.pbf" % app.country
    call("wget -c '%s' -O %s" % (url, app.countryPBF), shell=True)
    convert_pbf_to_o5m(app)


def convert_pbf_to_o5m(app):
    """Convert file format PBF --> O5M, necessary for using osmfilter later
    """
    if not os.path.isfile(app.countryPBF):
        print "\n* PBF file is missing.\nDownload the OSM data by launching the program with `-d` option."
        sys.exit(1)
    print "\n- Convert file format: PBF --> O5M ..."
    if os.path.isfile(app.countryO5M):
        call('mv %s %s' % (app.countryO5M, app.oldCountryO5M), shell=True)
    command = 'osmconvert %s -B=%s --out-o5m -o=%s' % (app.countryPBF, app.countryPoly, app.countryO5M)
    call(command, shell=True)
    print "... done"


def update_osm_data(app):
    """Update OSM data (O5M format) with osmupdate
    """
    print "\n- Update OSM data of %s with osmupdate ..." % app.country
    if os.path.isfile(app.countryO5M):
        call('mv %s %s' % (app.countryO5M, app.oldCountryO5M), shell=True)
    else:
        print "O5M is missing, I'll try to convert the PBF file..."
        app.convert_pbf_to_o5m(app)
    call('osmupdate -v -B=%s %s %s' % (app.countryPoly, app.oldCountryO5M, app.countryO5M), shell=True)
    if os.path.isfile(app.countryO5M):
        print "\n- %s has been updated, removing temporary file %s" % (app.countryO5M, app.oldCountryO5M)
        call("rm %s" % app.oldCountryO5M, shell=True)
        return True
    else:
        print "\n it was already updates, ==> restoring the previoius file %s" % app.country
        call('mv %s %s' % (app.oldCountryO5M, app.countryO5M), shell=True)
        return False


def filter_wikipedia_data_in_osm_file(app):
    """Filter from OSM data (O5M format) of the country those with
       wikipedia tag
    """
    if not os.path.isfile(app.countryO5M):
        print "O5M file is missing, I'll try to convert the PBF file..."
        app.convert_pbf_to_o5m(app)
    print "\n- Extract OSM data wih Wikipedia tag"

    if app.args.show_coordinates_from_osm:
        command = 'osmfilter %s --keep="wikipedia*=*" --keep-tags="all wikipedia*=*" -o=%s' % (app.countryO5M, app.wOSMFile)
    else:
        command = 'osmfilter %s --keep="wikipedia*=*" --keep-tags="all wikipedia*=*" --ignore-dependencies -o=%s' % (app.countryO5M, app.wOSMFile)

    call(command, shell=True)
