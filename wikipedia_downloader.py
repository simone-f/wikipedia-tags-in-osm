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
#  along with Nome-Programma.  If not, see <http://www.gnu.org/licenses/>.

"""Check which articles don't have the Coord template, by asking to Wikipedia
"""


import os
import urllib
import urllib2
import csv
import json
from subprocess import call


def read_old_templates_status(app):
    """Read from old_templates_status.csv which articles have/doesn't have
       the Coord template
    """
    templatesStatus = {}
    fileName = app.TEMPLATESSTATUSFILE
    if os.path.isfile(fileName):
        inFile  = open(fileName, "r")
        reader = csv.reader(inFile, delimiter='\t')
        for row in reader:
            title, status = row
            title = title.decode("utf-8")
            templatesStatus[title] = status
        inFile.close()
    print "  Senza template:",  len([i for i in templatesStatus.values() if i == "False"])
    return templatesStatus


def update_templates_status(app):
    """  Ask to Wikipedia which articles have/have not the Coord template
    """
    #create strings with fifty titles each
    unknownStatus = []
    for title in sorted(app.titlesInOSM):
        if title not in app.templatesStatus or app.templatesStatus[title] == "False":
            unknownStatus.append(title)
    titlesStrings = []
    for fiftyTitles in [unknownStatus[i:i+50] for i in range(0, len(unknownStatus), 50)]:
        titlesString = "|".join(fiftyTitles)
        titlesStrings.append(titlesString)
    #download
    print "  Update data with %d requests to Wikipedia:" % len(titlesStrings)
    for i, titlesString in enumerate(titlesStrings):
        continueString = ""
        tlcontinueString = ""
        print "\n  request %d" % i
        while True:
            wikipediaAnswer = download_templates(app, titlesString, continueString, tlcontinueString)
            if not wikipediaAnswer:
                break
            #parse
            continueString, tlcontinueString = parse_wikipedia_answer(app)
            if (continueString, tlcontinueString) == ("", ""):
                break
            else:
                print "  continue", continueString, tlcontinueString
    #Save updated templates status to file
    save_updated_templates_status(app)


def download_templates(app, titlesString, continueString, tlcontinueString):
    """Query Wikipedia API for Coord template in articles
    """
    titles = urllib.quote_plus(titlesString.replace("_", " ").encode("utf-8"))
    url = 'http://it.wikipedia.org/w/api.php?action=query'
    url += '&format=json'
    url += '&titles=%s' % titles
    url += '&prop=templates'
    url += '&tltemplates=Template:Coord'
    url += '&continue='
    if continueString != "":
        url += '%s&tlcontinue=%s' % (urllib.quote_plus(continueString), urllib.quote_plus(tlcontinueString))
    #debugging
    #answer = raw_input("\n  Download 50 titles status from Wikipedia?\n%s\n[y/N]" % url)
    answer = "y"
    if answer in ("y", "Y"):
        try:
            wikipediaAnswer = urllib2.urlopen(url)
        except:
            print "\n* a problem occurred during downloading:", titlesString, continueString, tlcontinueString
            return False
        else:
            fileName = os.path.join(app.MISSINGTEMPLATESDIR, "answer.json")
            fileOut = open(fileName, "w")
            fileOut.write(wikipediaAnswer.read())
            fileOut.close()
            return True


def parse_wikipedia_answer(app):
    """Read form Wikipedia the articles with/without Coord
       template
    """
    fileName = os.path.join(app.MISSINGTEMPLATESDIR, "answer.json")
    inFile = open(fileName, "r")
    data = json.load(inFile)
    inFile.close()
    pages = data["query"]["pages"]
    for pageid, pageData in pages.iteritems():
        title = pageData["title"].replace(" ", "_")
        if title in app.templatesStatus and app.templatesStatus[title] == "True":
            continue
        else:
            status = str("templates" in pageData)
            app.templatesStatus[title] = status
        #print "aggiunto ", title.encode("utf-8"), status.encode("utf-8")
    if "continue" in data:
        return (data["continue"]["continue"], data["continue"]["tlcontinue"])
    else:
        return ("", "")


def save_updated_templates_status(app):
    print "\n- Salvataggio del file con lo status dei template"
    fileName = app.TEMPLATESSTATUSFILE
    oldFileName = os.path.join(app.MISSINGTEMPLATESDIR, "old_%s" % app.TEMPLATESSTATUSFILE.split("/")[-1])
    call("cp '%s' '%s'" % (fileName, oldFileName), shell=True)
    fileOut = open(fileName, "w")
    writer = csv.writer(fileOut, delimiter='\t')
    withTemplate = 0
    for title in sorted(app.templatesStatus.keys()):
        status = app.templatesStatus[title]
        if status == "True":
            withTemplate += 1
        writer.writerow([title.encode("utf-8"), status])
    fileOut.close()
    #Print results
    print "  Articoli taggati: %d" % len(app.templatesStatus)
    print "    con template  : %d" % len([i for i in app.templatesStatus.values() if i == "True"])
    print "    senza template: %d" % len([i for i in app.templatesStatus.values() if i == "False"])
