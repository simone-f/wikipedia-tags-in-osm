#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 - Fondazione Bruno Kessler. 
#  Autore: Cristian Consonni <consonni@fbk.eu>
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

import requests
import json
import ast
import urllib
import signal
import os
import sys
import multiprocessing as mp
import logging

GEONAMES_USER = 'osmit'

try:
    cpus = mp.cpu_count()
except NotImplementedError:
    cpus = 2   # arbitrary default


class GeonamesError(Exception):
    """
    A simple class to expose errors form the Geonames service.
    """
    pass

def geolocate_place(place_name):
    """
    Retrieves the (lon, lat) coordinates of a place, by
    querying the geonames web service.
    """

    params = urllib.urlencode({
        'username': GEONAMES_USER,
        'q': place_name.encode('utf-8'),
        'maxRows': 1,
    })

    response = None
    try:
        response = requests.get(
            "http://api.geonames.org/searchJSON?{}".format(params))
    except requests.exceptions.ConnectionError:
        pass

    if response:
        if response.ok:
            resp_json = response.json()

            if resp_json.get('geonames', None) is None:
                # geonames returned an unexpect answer, here's an example error:
                raise GeonamesError(resp_json['status']['message'])

            resp_data = None
            try:
                resp_data = response.json()['geonames'][0]
            except:
                pass

            loc = None
            if resp_data:
                loc = [float(resp_data['lat']), float(resp_data['lng'])]

            return loc

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def listener(queue, fn):
    '''listens for messages on the q, writes to file. '''

    while 1:
        m = queue.get()
        if m == 'kill':
            break
        with open(fn, 'a+') as f:
            f.write(str(m) + '\n')
            f.flush()

class MultiWorker(object):

    def __init__(self, cpus, outfile):
        self.cpus = cpus
        self.manager = mp.Manager()
        self.queue = self.manager.Queue()
        self.pool = mp.Pool(cpus, init_worker)
        self.outfile = outfile
        self.logger = mp.log_to_stderr()
        self.logger.setLevel(logging.DEBUG)

    def close_multiprocess(self):
        del self.queue
        self.pool.close()
        self.pool.join()

    def terminate_multiprocess(self):
        del self.queue
        self.pool.terminate()
        self.pool.join()


def call_nuts4nuts(article_name, q=None, outfile=None):
    url = 'http://nuts4nutsrecon.spaziodati.eu/reconcile'
    
    query = {
        'q0': {'query': article_name}
    }

    params = urllib.urlencode({
        'queries': json.dumps(query)
    })

    print 'requesting {}'.format(article_name)

    req = None
    try:
        req = requests.get(url, params=params)
    except requests.exceptions.ConnectionError:
       pass 


    if req:
        print 'req.ok: {}'.format(req.ok)
        if not req.ok:
            req.raise_for_status()
    
        res = None
        try:
            res = req.json()['q0']['result']
        except KeyError:
            pass

        loc = None
        if res:
            city = [nut['name'] for nut in res if nut['match']]
            city = city and city[0]
            if city:
                loc = geolocate_place(city)

        print loc
        if loc:
            output = {'article': article_name, 'coords': loc}
            if q:
                print output
                q.put(output)
            else:
                with open(outfile, 'a+') as f:
                    f.write(str(output) + '\n')
                    f.flush()                

def infer_names(mw, articles):

    watcher = mw.pool.apply_async(listener, (mw.queue, mw.outfile))

    jobs = []
    for a in articles:
        job = mw.pool.apply_async(call_nuts4nuts, (a, mw.queue))
        jobs.append(job)

    for job in jobs: 
        job.get()

    mw.queue.put('kill')

def infer_coordinates_with_nuts4nuts(app):
    """ 
    Use Nuts4Nuts and Dandelion by SpazioDati to infer the position of
    a Wikipedia article from his templates and his abstract
    """

    app.titlesNutsCoords = {}    

    inFile = open(os.path.join("data", "nuts4nuts", "articles_to_scan.txt"), "r")
    articles = [line.strip() for line in inFile.readlines()]
    inFile.close()
    
    nutsCoordsFile = os.path.join("data", "nuts4nuts", "nuts4nuts_%s_coords.txt" 
                        % app.WIKIPEDIALANG)

    mw = MultiWorker(cpus, nutsCoordsFile)

    if not os.path.isfile(nutsCoordsFile) or \
            os.stat(nutsCoordsFile).st_size == 0:
        infer_names(mw, articles)

    with open(nutsCoordsFile, 'r') as f:
        data = [ast.literal_eval(line.strip()) for line in f.readlines()]

    app.coordsFromNuts4Nuts = []

    for d in data:
        title = d['article'].replace(" ", "_").decode("utf-8")
        coords = d['coords']
        app.titlesNutsCoords[title] = coords

    for theme in app.themes:
        for category in theme.categories:
            category.check_articles_coords_from_nuts4nuts()

    app.coordsFromNuts4Nuts = list(set(app.coordsFromNuts4Nuts))
    print "  articoli:", len(app.coordsFromNuts4Nuts)


if __name__ == '__main__':

    infilename = os.path.join("data", 
                              "nuts4nuts",
                              "articles_to_scan.txt"
                             )

    inFile = open(infilename, "r")
    articles = frozenset([line.strip() for line in inFile.readlines()])
    inFile.close()

    print ' total articles: %d' %len(articles)

    nutsCoordsFile = os.path.join("data",
                                  "nuts4nuts",
                                  "nuts4nuts_it_coords.txt"
                                 )

    with open(nutsCoordsFile, 'r') as f:
        data = [ast.literal_eval(line.strip()) for line in f.readlines()]

    already_scanned = frozenset([d['article'] for d in data])
    print ' already scanned: %d' %len(already_scanned)

    articles_to_scan = list(articles - already_scanned)
    print ' to scan: %d' %len(articles_to_scan)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)

    logger.addHandler(console)

    mw = MultiWorker(cpus, nutsCoordsFile)

    try:
        infer_names(mw, articles_to_scan)
        mw.close_multiprocess()

    except KeyboardInterrupt:
        print "\nCaught KeyboardInterrupt, terminating workers"
        del mw
#        mw.close_multiprocess()
        #mw.terminate_multiprocess()
        sys.exit(0)