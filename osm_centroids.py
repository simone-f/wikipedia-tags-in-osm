#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2013 Fondazione Bruno Kessler
#  Author: <consonni@fbk.eu>
#  This work has been funded by Fondazione Bruano Kessler (Trento, Italy)
#  under projects T2DataExchange and LOD4STAT
#
#  This file is part of wikipedia-tags-in-osm.
#  wikipedia-tags-in-osm is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  wikipedia-tags-in-osm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with wikipedia-tags-in-osm.
#  If not, see <http://www.gnu.org/licenses/>.


import argparse
import os
from pysqlite2 import dbapi2 as spatialite
from subprocess import Popen, PIPE, call


class OSMcentroids(object):
    def __init__(self, wOSMFile, wOSMdb, libspatialitePath, args=None):
        self.wOSMFile = wOSMFile
        self.wOSMdb = wOSMdb
        self.libspatialitePath = libspatialitePath

        if args is not None:
            self.args = args

            if self.args.drop_database:
                self.drop_database()

            elif self.args.drop_ways_centroids_table:
                self.drop_table('osm_ways_centroids')

            elif self.args.drop_relations_centroids_table:
                self.drop_table('osm_relations_centroids')

            else:
                if self.args.import_data:
                    self.import_data_in_sqlite_db()

                if self.args.ways:
                    self.create_ways_centroids()

                if self.args.relations:
                    self.create_relations_centroids()

    def import_data_in_sqlite_db(self):
        """Import OSM data with Wikipedia tag in a sqlite database to calculate
           centroids
        """

        print "Import OSM data of file: "
        print self.wOSMFile
        print "into the Spatialite database: "
        print self.wOSMdb
        print

        command = "spatialite_osm_raw -o {wosm_file} -d {wtosm_db}".format(
            wosm_file=self.wOSMFile,
            wtosm_db=self.wOSMdb)
        call(command, shell=True)

        print
        print "Import completed!"

    def _query_wrapper(self, query):
        con = spatialite.connect(self.wOSMdb)
        con.enable_load_extension(True)
        try:
            with con:
                cur = con.cursor()
            cmd = "SELECT load_extension('%s');" % self.libspatialitePath
            cur.execute(cmd)
            cur.execute(query)
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error
            print "None table created"

        return cur

    def create_ways_centroids(self):
        query = """CREATE TABLE osm_ways_centroids
                   AS SELECT way_id,
                             AsText(Centroid(ST_Collect(Geometry))) as centr,
                             AsText(
                                MakePoint(MbrMinX(ST_Collect(Geometry)),
                                          MbrMinY(ST_Collect(Geometry)),
                                          4326
                                          )
                                ) as p1,
                             AsText(
                                 MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                           MbrMaxY(ST_Collect(Geometry)),
                                           4326
                                           )
                                 ) as p2,
                             GeodesicLength(
                                 MakeLine(
                                     MakePoint(MbrMinX(ST_Collect(Geometry)),
                                               MbrMinY(ST_Collect(Geometry)),
                                               4326
                                               ),
                                     MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                               MbrMaxY(ST_Collect(Geometry)),
                                               4326
                                               )
                                     )
                                 ) as dist
                      FROM osm_way_refs AS w
                      JOIN osm_nodes AS n
                      ON w.node_id = n.node_id
                      GROUP BY way_id
                """

        self._query_wrapper(query)

        con = spatialite.connect(self.wOSMdb)

        query = """SELECT Count(*)
                   FROM osm_ways_centroids
                """

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
            num = cur.fetchone()[0]
            print "A table with %d rows has been created" % num
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error

    def create_relations_centroids(self):
        con = spatialite.connect(self.wOSMdb)

        query = """CREATE TABLE osm_relations_centroids_source
                   AS SELECT rel_id, type, ref, Geometry
                   FROM osm_relation_refs AS rr
                   JOIN (SELECT way_id, w.node_id, Geometry
                         FROM osm_way_refs AS w
                         JOIN osm_nodes AS n
                         ON w.node_id = n.node_id
                         ) AS nw
                   ON (type = "W" AND rr.ref = nw.way_id)
                """

        self._query_wrapper(query)

        query = """INSERT INTO osm_relations_centroids_source
                   SELECT rel_id, type, ref, Geometry
                   FROM osm_relation_refs AS rr
                   JOIN osm_nodes AS n
                   ON (type = "N" AND rr.ref = n.node_id)
                """
        self._query_wrapper(query)

        query = """CREATE TABLE osm_relations_centroids
                   AS SELECT rel_id,
                             AsText(Centroid(ST_Collect(Geometry))) as centr,
                             AsText(
                                MakePoint(MbrMinX(ST_Collect(Geometry)),
                                          MbrMinY(ST_Collect(Geometry)),
                                          4326
                                          )
                                ) as p1,
                             AsText(
                                 MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                           MbrMaxY(ST_Collect(Geometry)),
                                           4326
                                           )
                                 ) as p2,
                             GeodesicLength(
                                 MakeLine(
                                     MakePoint(MbrMinX(ST_Collect(Geometry)),
                                               MbrMinY(ST_Collect(Geometry)),
                                               4326
                                               ),
                                     MakePoint(MbrMaxX(ST_Collect(Geometry)),
                                               MbrMaxY(ST_Collect(Geometry)),
                                               4326
                                               )
                                     )
                                 ) as dist
                   FROM osm_relations_centroids_source
                   GROUP BY rel_id
                """
        self._query_wrapper(query)

        query = """SELECT Count(*)
                   FROM osm_relations_centroids
                """

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
            num = cur.fetchone()[0]
            print "A table with %d rows has been created" % num
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error
            print "None table created"
        finally:
            with con:
                cur = con.cursor()
            cur.execute("DROP TABLE osm_relations_centroids_source")
            print "Drop TEMP table osm_relations_centroids_source"

    def _get_coords_from_wkt(self, cur):
        centroids = {}
        if cur:
            for obj_id, wkt in cur:
                coords = [float(c)
                          for c in wkt.strip('POINT(').strip(')').split()
                          ]
                coords.reverse()
                centroids[obj_id] = coords

        return centroids

    def get_relations_centroids(self):
        query = """SELECT rel_id, centr
                   FROM osm_relations_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_coords_from_wkt(cur)

    def get_ways_centroids(self):
        query = """SELECT way_id, centr
                   FROM osm_ways_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_coords_from_wkt(cur)

    def _get_dims(self, cur):
        dims = {}
        if cur:
            for obj_id, dist in cur:
                dims[obj_id] = int(round(dist))

        return dims

    def get_relations_dimensions(self):
        query = """SELECT rel_id, dist
                   FROM osm_relations_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_dims(cur)

    def get_ways_dimensions(self):
        query = """SELECT way_id, dist
                   FROM osm_ways_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_dims(cur)

    def drop_table(self, table_name):
        con = spatialite.connect(self.wOSMdb)

        query = "DROP TABLE {}".format(table_name)

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error

    def drop_database(self):
        proc = Popen(["rm", self.wOSMdb], stderr=PIPE)
        status = proc.wait()

        if status == 0:
            print "Rimosso il database {}".format(self.wOSMdb)
        else:
            output = proc.stderr.read()
            print "rm exited with status: {}".format(status)
            print output


def main():
        # Options
        text = 'Starting from the file containing OSM elements with '\
               'Wikipedia tag (created with osmfilter) this script imports data into a '\
               'Spatialite database '\
               '(through spatialite_osm_raw). '\
               'Then, it creates two tables: '\
               '1) osm_ways_centroids '\
               '2) osm_relations_centroids '\
               '- which contain the centroids of ways and relations with Wikipedia tags respectevely.'\
               'These data are used by the main program\'s script during '\
               'web pages creation, specifically while creating the link '\
               'to insert {{coord}} template in Wikipedia'

        parser = argparse.ArgumentParser(description=text)

        parser.add_argument("-d", "--database",
                            help='SQLite/Spatialite database name that '
                                 'will be created [default: '
                                 './data/OSM/Wikipedia-data-in-OSM.sqlite]',
                            dest="wOSMdb",
                            default=os.path.join("data",
                                                 "OSM",
                                                 "Wikipedia-data-in-OSM.sqlite"
                                                 ),
                            action="store"
                            )
        parser.add_argument("-p", "--libspatialite_path",
                            help='Path to libspatialite [default: '
                                 'libspatialite]',
                            dest="libspatialitePath",
                            default="libspatialite",
                            action="store"
                            )
        parser.add_argument("-f", "--osm_file",
                            help='Name of the file with OSM data (created by '
                                 'osmfilter) [default: '
                                 './data/OSM/Wikipedia-data-in-OSM.osm]',
                            dest="wOSMFile",
                            default=os.path.join("data",
                                                 "OSM",
                                                 "Wikipedia-data-in-OSM.osm"
                                                 ),
                            action="store"
                            )
        parser.add_argument("-i", "--import_data",
                            help="Import data in the Spatialite database",
                            action="store_true"
                            )
        parser.add_argument("-w", "--ways",
                            help="Calculate centroids for ways",
                            action="store_true"
                            )
        parser.add_argument("-r", "--relations",
                            help="Calculate centroids for relations",
                            action="store_true"
                            )
        parser.add_argument("--drop_database",
                            help="Drop the database",
                            action="store_true")
        parser.add_argument("--drop_ways_centroids_table",
                            help='Drop from the database the table whith ways centroids: '
                                 'osm_ways_centroids',
                            action="store_true")
        parser.add_argument("--drop_relations_centroids_table",
                            help='Drop from the database the table with relations centroids: '
                                 'osm_relations_centroids',
                            action="store_true")

        args = parser.parse_args()
        #print args

        osm = OSMcentroids(args.wOSMFile,
                           args.wOSMdb,
                           args.libspatialitePath,
                           args)

if __name__ == '__main__':
    main()
