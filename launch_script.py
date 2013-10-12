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

#  Nome-Programma is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with Nome-Programma.  If not, see <http://www.gnu.org/licenses/>.

"""Starting from a list of Wikipedia categories written by the user in
   'config' file, the script:
   - downloads/updates a national OSM data file
   - downloads from (from catscan) Wikipedia data regarding the selected
     categories (subcategories names and articles titles)
   - creates webpages for showing which articles are already tagged and
     which ones are not.
"""

import argparse
import os
import time
from subprocess import call
import csv
import urllib
import urllib2
import ConfigParser
import sys

#local imports
from osm_parser import ParseOSMData
from data_manager import Themes, Regions
from webpages_creator import Creator


class App:
    def __init__(self):
        #Options
        text = "A partire da una lista di categorie inserite dall'utente nel file 'config', lo script:\
 scarica/aggiorna i dati OSM nazionali, scarica da Wikipedia i dati sulle categorie (gli articoli che le compongono)\
 e crea delle pagine HTML indicando gli articoli già taggati e da taggare in OSM."
        parser = argparse.ArgumentParser(description=text)
        group = parser.add_mutually_exclusive_group()
        #Manage OSM data
        parser.add_argument("-d", "--download_osm", help="Scarica i dati OSM nazionali (da Geofabrik)",
                            action="store_true")
        parser.add_argument("-u", "--update_osm", help="Aggiorna i dati OSM nazionali scaricati (tramite osmupdate)",
                            action="store_true")
        #Analyze data from Wikipedia and OSM
        parser.add_argument("-a", "--analyze", help="Analizza i dati: Wikipedia (sottocategorie ed articoli delle categorie) ed OSM (tag Wikipedia presenti)",
                            action="store_true")
        parser.add_argument("--category_info", help="Analizza i dati e stampa le informazioni su una specifica categoria",
                            action='store')
        group.add_argument("-p", "--print_categories_list", help="Analizza i dati e stampa la lista delle categorie nel progetto",
                            action="store_true")
        #Create webpages
        group.add_argument("-w", "--create_webpages", help="Analizza i dati ed aggiorna le pagine web",
                            action="store_true")
        parser.add_argument("-s", "--save_stats", help="Se sono state aggiornate le pagine web, salva il conteggio aggiornato con il numero di articoli taggati (default: chiedi cosa fare).",
                            action="store_true")
        parser.add_argument("--nofx", help="Non aprire le pagine web in Firefox dopo averle aggiornate.",
                            action="store_true")
        parser.add_argument("--copy", help="Copia la cartella html nella directory descritta nel file config (es. dir dropbox).",
                            action="store_true")
        parser.add_argument("--bitly", help="Use bitly links, to count visits to homepage.",
                            action="store_true")
        self.args = parser.parse_args()
        if self.args.category_info or self.args.category_info\
           or self.args.create_webpages or self.args.print_categories_list:
            self.args.analyze = True

        if len(sys.argv)==1:
            parser.print_help()
            sys.exit(1)
        os.chdir(os.path.dirname(sys.argv[0]))

        #Configurations
        self.version = "v0.1.3"
        #From 'config' file
        themesAndCatsNames = self.read_config()
        # OSM data
        self.countryPBF = os.path.join(self.OSMDIR, "%s-latest.osm.pbf" % self.country)
        self.oldCountryPBF = os.path.join(self.OSMDIR, "%s.osm.pbf" % self.country)
        self.countryO5M = os.path.join(self.OSMDIR, "%s-latest.o5m" % self.country)
        self.oldCountryO5M = os.path.join(self.OSMDIR, "%s.o5m" % self.country)
        # OSM data with wikipedia tag
        self.wOSMFile = os.path.join("data", "OSM", "Wikipedia-data-in-OSM.osm")
        # OSM data of foreign coountries
        self.FOREIGNOSMDIR = "/tmp/"
        # Wikipedia categories data, downloaded from catscan
        self.CATSCANDIR = os.path.join("data", "wikipedia", "catscan")
        # lists of categories and articles that should be ignored
        # (not geographic content)
        self.NONMAPPABLE = os.path.join("data", "wikipedia", "non_mappable")
        # conversions foreign articles titles - preferred language articles
        self.WIKIPEDIAANSWERS = os.path.join("data", "wikipedia", "answers")
        self.WIKIPEDIAANSWER = os.path.join(self.WIKIPEDIAANSWERS, "answer")
        # directory with webpages
        self.HTMLDIR = 'html'
        if not os.path.exists(os.path.join(self.HTMLDIR, "subpages")):
            os.makedirs(os.path.join(self.HTMLDIR, "subpages"))
        statsDir = os.path.join("data", "stats")
        if not os.path.exists(statsDir):
            os.makedirs(statsDir)
        logsDir = os.path.join("data", "logs")
        if not os.path.exists(logsDir):
            os.makedirs(logsDir)
        self.homePageTitle = "Articoli Wikipedia etichettabili in OSM"
        self.UPDATETIME = time.strftime("%b %d, ore %H", time.localtime())


### Manage OpenStreetMap data ##########################################
        #Analyse national OSM data file and create lists of already
        #tagged Wikipedia articles.

        #Download/update OSM data
        if self.args.download_osm or self.args.update_osm:
            if self.args.download_osm:
                self.download_OSM_data()
            if self.args.update_osm:
                status = self.update_OSM_data()
        if self.args.download_osm or (self.args.update_osm and status):
            self.filter_wikipedia_data_in_OSM_file()
        if self.args.update_osm and not status:
            print "I dati OSM erano già aggiornati all'ultimo minuto, o l'aggiornamento con osmupdate è stato interrotto.\
Per ripetere l'aggiornamento, lanciare nuovamente lo script con l'opzione -u."

        if not self.args.analyze:
            #"There's nothing left for me to tell you"
            sys.exit(1)
        else:
            if not os.path.isfile(self.wOSMFile):
                self.filter_wikipedia_data_in_OSM_file()
            else:
                #Extract Wikipedia articles tagged in OSM with preferred language.
                #If an article is tagged in a foreign language, ask to Wikpedia
                #what is the corrisponding article of the preferred language, so
                #that we can flag it as tagged aswell.
                print "\n- Estrai dal file OSM gli articoli già taggati"
                parseOSMData = ParseOSMData(self)
                #list of Wikipedia tags in OSM
                self.tagsInOSM = parseOSMData.allTags
                #list of tagged Wikipedia articles
                self.taggedTitles = parseOSMData.titles
                #tags with errors
                self.wrongTags = parseOSMData.wrongTags
                #ugly tags (with url, language capitalized...), not errors
                self.badTags = parseOSMData.badTags
                #add articles manually flagged as tagged in data/workaround/tagged.csv
                #in case the parser misses them (strange tags)
                self.add_tagged_articles()


### Manage Wikipedia data ##############################################
        #Read from 'non-mappable' file the categories and articles that
        #aren't mappable e.g. "Paintings in the X museum",
        #self.nonMappable = {mainCategory.name : {"articles" : [], "subcategories" : []}}
        self.nonMappable = self.read_non_mappable_items()

        #Check if we have Wikipedia data from catscan of all the selected categories
        themesAndCatsNames = self.check_catscan_data(themesAndCatsNames)

        #Organize Wikipedia data.
        #self.themes = [Theme(), ...]
        #  Theme().categories = [Category(), ...]
        #    Category().subcategories = [Category(), ...]
        #    Category().articles = [Article(), ...]
        #categories without catscan data
        self.categoriesWithoutData = []
        self.themes = Themes(self, themesAndCatsNames).themesList

        #Organize data in regions, for a different visualization
        #self.regions = [Region()]
        #  Region().categories = [Category(), ... ]
        self.regions = Regions(self).regionsList

        #Print names of all categories
        if self.args.print_categories_list:
            self.display_categories_names()
            if not self.args.category_info:
                #"There's nothing left for me to tell you"
                sys.exit(1)


### Merge OSM info into Wikipedia data #################################
        #Add to Wikipedia categories and articles istances info about
        #their status in OSM: (tagged/not tagged), osm ids and counters
        print "\n- Controlla quali articoli nelle liste sono già taggati nel file OSM"
        for theme in self.themes:
            for category in theme.categories:
                category.check_articles_in_osm()
        self.titlesInOSM, self.titlesNotInOSM = self.lists_of_titles_in_OSM_or_not()

        #For debugging
        # print info about a specific category
        if self.args.category_info:
            self.print_category_info(self.args.category_info.replace(" ", "_"))
            if self.args.create_webpages:
                raw_input("\nContinue?[Press any key]")
        # write categories trees to text files (uncomment lines)
        if self.print_categories_to_text_files == "true":
            for theme in self.themes:
                for category in theme.categories:
                    category.print_category_tree_to_file()

        #Read and update stats with the number of tagged articles
        self.dates, self.days = self.read_past_stats()
        download_other_countries = False
        todayDate, today = self.read_new_stats(download_other_countries)
        self.days.append(today)
        self.dates.append(todayDate)
        if len(self.dates) > 1 and todayDate == self.dates[-2]:
            #If this is the second analysis of the day,
            #overwrite old statistics of today
            del self.dates[-2]
            del self.days[-2]
            print "\n Questa è la seconda volta che i dati vengono analizzati oggi. \
Il numero di articoli taggati sostituisce quelli precedenti nella tabella dei conteggi."

        #Create webpages
        if self.args.create_webpages:
            print "\n- Crea pagine web"
            Creator(self)

        #Save stats
        if self.args.create_webpages and self.args.save_stats:
            answer = "y"
        else:
            answer = raw_input("\n- Salvo il numero di articoli mappati/da mappare in ./data/stats/stats.csv?\n[y/n]\n")
        if answer == "y":
            self.save_stats_to_csv()
        else:
            print "\nI nuovi conteggi non vengono salvati."

        #Copy files from html dir to outdir (for example a Dropbox directory)
        if self.args.copy:
            self.copy_html_files_to_outdir()

        print "\nDone."


### Configuration from config file #####################################
    def read_config(self):
        configparser = ConfigParser.RawConfigParser()
        configparser.optionxform=str
        fp = open("config")
        configparser.readfp(fp)
        fp.close()
        #country
        self.WIKIPEDIALANG = configparser.get("general", "preferred language")
        self.country = configparser.get("general", "country")
        self.OSMDIR = configparser.get("general", "osmdir")
        self.countryPoly = os.path.join("data", "OSM", "%s.poly" % self.country)
        if self.WIKIPEDIALANG == "" or self.country == "" or self.OSMDIR == "":
            print "\n* Inserisci nel file 'config' le opzioni 'osmdir', 'preferred language', 'country'"
            sys.exit(1)
        # directory where html files must be copied after creation
        #(for example, Dropbox dir)
        self.OUTDIR = configparser.get("general", "outdir")
        #themes and categories
        themesAndCatsNames = {}
        for themeName in configparser.options("themes"):
            categoriesNames = [c.strip().replace(" ", "_").decode("utf-8") for c in configparser.get("themes", themeName).split("|")]
            themesAndCatsNames[themeName.replace(" ", "_").decode("utf-8")] = categoriesNames
        #categories dates
        self.categoriesDates = {}
        for categoryName, date in configparser.items("catscan dates"):
            self.categoriesDates[categoryName] = date
        #debugging
        self.print_categories_to_text_files = configparser.get("debug", "print categories to text files")
        self.clickable_cells = configparser.get("debug", "clickable cells")
        return themesAndCatsNames


### Download/update OSM data ###########################################
    def download_OSM_data(self):
        """Download OSM data from GEOFABRIK, in PBF format
        """
        print "\n- Scarico i dati di OSM Italia da Geofabrik ..."
        if os.path.isfile(self.countryPBF):
            call('mv %s %s' % (self.countryPBF, self.oldCountryPBF), shell=True)
        url = "http://download.geofabrik.de/europe/%s-latest.osm.pbf" % self.country
        call("wget -c '%s' -O %s" % (url, self.countryPBF), shell=True)
        self.convert_pbf_to_o5m()

    def convert_pbf_to_o5m(self):
        """Convert file format PBF --> O5M, necessary for using osmfilter later
        """
        if not os.path.isfile(self.countryPBF):
            print "\n* File PBF assente.\nScaricare i dati OSM nazionali, lanciando lo script con l'opizone -d."
            sys.exit(1)
        print "\n- Conversione del formato dei dati: PBF --> O5M ..."
        if os.path.isfile(self.countryO5M):
            call('mv %s %s' % (self.countryO5M, self.oldCountryO5M), shell=True)
        command = 'osmconvert %s -B=%s --out-o5m -o=%s' % (self.countryPBF, self.countryPoly, self.countryO5M)
        call(command, shell=True)
        print "... done"

    def update_OSM_data(self):
        """Update OSM data (O5M format) with osmupdate
        """
        print "\n- Aggiornamento dei dati OSM %s con osmupdate ..." % self.country
        if os.path.isfile(self.countryO5M):
            call('mv %s %s' % (self.countryO5M, self.oldCountryO5M), shell=True)
        else:
            print "File O5M assente, provo a convertire il file PBF..."
            self.convert_pbf_to_o5m()
        call('osmupdate -v -B=%s %s %s' % (self.countryPoly, self.oldCountryO5M, self.countryO5M), shell=True)
        if os.path.isfile(self.countryO5M):
            print "\n- %s aggiornato, rimuovo file temporaneo %s" % (self.countryO5M, self.oldCountryO5M)
            call("rm %s" % self.oldCountryO5M, shell=True)
            return True
        else:
            print "\n era già aggiornato, ==> ripristina file %s precedente" % self.country
            call('mv %s %s' % (self.oldCountryO5M, self.countryO5M), shell=True)
            return False

    def filter_wikipedia_data_in_OSM_file(self):
        """Filter from OSM data (O5M format) of the country those with
           wikipedia tag
        """
        if not os.path.isfile(self.countryO5M):
            print "File O5M assente, provo a convertire il file PBF..."
            self.convert_pbf_to_o5m()
        print "\n- Estrai i dati OSM con tag wikipedia"
        command = 'osmfilter %s --keep="wikipedia*=*" --keep-tags="all wikipedia*=*" --drop-version --ignore-dependencies -o=%s' % (self.countryO5M, self.wOSMFile)
        call(command, shell=True)

    def lists_of_titles_in_OSM_or_not(self):
        """Create a list of already tagged titles, for counting their
           number
        """
        titlesInOSM = []
        titlesNotInOSM = []
        for theme in self.themes:
            theme.check_articles_in_osm()
            for title in theme.titlesNotInOSM:
                titlesNotInOSM.append(title)
            for title in theme.titlesInOSM:
                titlesInOSM.append(title)
        titlesInOSM = list(set(titlesInOSM))
        titlesNotInOSM = list(set(titlesNotInOSM))
        return titlesInOSM, titlesNotInOSM

### Manage catscan data ################################################
    def check_catscan_data(self, themesAndCatsNames):
        """Check if we have Wikipedia data from catscan (subcategories names
           and articles names) of all the categories written in 'config' file
        """
        print "\n- Controlla la presenza dei dati Wikipedia (catscan) di tutte le categorie nel file 'config'"
        needInfo = {}
        for themeName, categoriesNames in themesAndCatsNames.iteritems():
            for categoryName in categoriesNames:
                categoryCatscanFile = os.path.join(self.CATSCANDIR, themeName, "%s.csv" % categoryName)
                categoryCatscanFile = categoryCatscanFile.encode("utf-8")
                if not os.path.isfile(categoryCatscanFile):
                    if not themeName in needInfo:
                        needInfo[themeName] = []
                    needInfo[themeName].append(categoryName)
        #download catscan data of missing categories
        for themeName, categoriesNames in needInfo.iteritems():
            for categoryName in categoriesNames:
                result = self.download_a_new_category(themeName, categoryName)
                if not result:
                    themesAndCatsNames[themeName].remove(categoryName)
        return themesAndCatsNames

    def download_a_new_category(self, themeName, categoryName):
        """Download data (subcategories and articles) of a new category
           from catscan (http://toolserver.org/%7Edaniel/WikiSense/CategoryIntersect.php)
           and save it to: CATSCANDIR/theme name/category name.csv
        """
        print "\n- Scarico (da catscan) la lista di sottocategorie ed articoli di una nuova categoria Wikipedia"
        response = raw_input("\n- Scarico dati categoria %s da catscan?\n[y|n]" % categoryName.encode("utf-8"))
        if response != "y":
            return False
        print "\ndownloading category info from catscan..."

        if themeName not in os.listdir(self.CATSCANDIR):
            os.makedirs(os.path.join(self.CATSCANDIR, themeName))

        #Download the CSV file with subcategories and articles of the requested category
        url = "http://toolserver.org/~daniel/WikiSense/CategoryIntersect.php?"
        url += "wikilang=%s" % self.WIKIPEDIALANG
        url += "&wikifam=.wikipedia.org"
        url += "&basecat=" + urllib.quote_plus(categoryName.encode("utf-8"))
        url += "&basedeep=8&templates=&mode=al&format=csv"

        print "url:"
        print url

        data = urllib2.urlopen(url)
        filename = os.path.join(self.CATSCANDIR, themeName, "%s.csv" % categoryName)
        csvFile = open(filename,'w')
        csvFile.write(data.read())
        csvFile.close()
        print "Dati Wikipedia sulla nuova categoria salvati in:\n%s" % filename

        #Remember category date
        configparser = ConfigParser.RawConfigParser()
        configparser.optionxform=str
        configparser.read("config")
        categoryDate = time.strftime("%b %d, ore %H", time.localtime())
        configparser.set("catscan dates", categoryName.encode("utf-8"), categoryDate)
        configparser.write(open("config", "w"))
        #update category date
        self.categoriesDates[categoryName] = categoryDate
        return True

### Not mappable items and false positive tags #########################
    def read_non_mappable_items(self):
        """Read lists of categories and articles that must be ignored,
           because not mappable.
           Wikipedia articles or categories like: "Paintings in the X museum",
           "Opere nel Castello Sforzesco‎"...
        """
        print "\n- Leggi le liste di articoli e categorie da ignorare perché non mappabili, dal 'file ./data/wikipedia/non_mappable'"
        #nonMappable = {category : {"subcategories" : [], "articles" : []}, ...}
        nonMappableParser = ConfigParser.RawConfigParser()
        nonMappableParser.read(self.NONMAPPABLE)
        nonMappable = {}
        for section in nonMappableParser.sections():
            categoryName = section.replace(" ", "_").decode("utf-8")
            nonMappable[categoryName] = {}
            for elementType in ("subcategories", "articles"):
                nonMappableString = nonMappableParser.get(section, elementType)
                nonMappableList = nonMappableString.split("|")
                nonMappable[categoryName][elementType] = [item.replace(" ", "_").decode("utf-8") for item in nonMappableList]
        return nonMappable

    def add_tagged_articles(self):
        """Read from file "./data/workaround/tagged.csv" articles flagged as tagged
           by hand, in case the parser did not detected them.
        """
        ifile  = open(os.path.join("data", "workaround", "tagged.csv"), "rb")
        reader = csv.reader(ifile, delimiter = '\t')
        for row in reader:
            if row != [] and row[0][0] != "#":
                if len(row) == 2:
                    articleName = row[0].replace(" ", "_")
                    osmIds = row[1].split(",")
                    self.taggedTitles[articleName] = osmIds
        ifile.close()


### Print info to terminal #############################################
    def print_category_info(self, categoryName):
        """Print to the terminal informaions about the reqiested category
        """
        catFound = False
        for theme in self.themes:
            for category in theme.categories:
                if catFound == True:
                    break
                if category.name == categoryName:
                    category.print_info()
                    catFound = True
                    break
                for subcategory in category.subcategories:
                    if subcategory.name == categoryName:
                        subcategory.print_info()
                        catFound = True
                        break
        if not catFound:
            print "\nNessuna categoria trovata con il nome specificato."

    def display_categories_names(self):
        """Print to terminal the list of main categories
        """
        print "\n=CATEGORIES="
        categoryNum = 0
        for theme in self.themes:
            print "\n%s:" % theme.name
            for category in theme.categories:
                print "%d - %s" % (categoryNum, category.name.replace("_", " "))
                categoryNum += 1


### Statistics #########################################################
    def read_past_stats(self):
        """Read stats
        """
        statsFile = os.path.join("data", "stats", "stats.csv")
        if not os.path.isfile(statsFile):
            dates = []
            days = []
        else:
            ifile = open(statsFile, "r")
            reader = csv.reader(ifile, delimiter='\t', quotechar='"')
            #list with the number of tagged articles, per day
            days = []
            for rowNum, row in enumerate(reader):
                if rowNum == 0:
                    #date
                    dates = row[1:]
                    for date in dates:
                        days.append({})
                else:
                    #data
                    status = row[0]
                    for dateIndex, value in enumerate(row[1:]):
                        if value == "":
                            days[dateIndex][status] = ""
                        else:
                            days[dateIndex][status] = int(value)
            ifile.close()
        return dates, days

    def count_wkp_tags_in_file(self, country):
        """Count the number of 'wikipedia=*' in OSM file
        """
        print "\n conteggio del numero di tag wikipedia tags"
        if country == "italy":
            path = self.OSMDIR
        else:
            path = "/tmp/"
        call('osmfilter %s%s.o5m --out-count | grep wikipedia > data/stats/%s' % (path, country, country), shell=True)
        file_in = open("data/%s" % country, "r")
        lines = file_in.readlines()
        file_in.close()
        tagsInCountry = 0
        for line in lines:
            line = line.replace(" ","")[:-1]
            tagsInCountry += int(line.split("\t")[0])
        return tagsInCountry

    def read_new_stats(self, download_other_countries):
        """Add latest numbers to stats
        """
        todayDate = self.UPDATETIME.split(",")[0]
        today = {"to do"  : len(self.titlesNotInOSM),
                 "mapped" : len(self.titlesInOSM),
                 "total"  : len(self.tagsInOSM)}
        #Print tags numbers of other countries
        if download_other_countries == True:
            print "\n- Tags numbers in countries (with duplicate articles"
            tagsNum = {"italy" : self.tagsInOSM, "spain" : "", "france" : "", "germany" : ""}
            for country in tagsNum:
                print "\n- %s:" % country
                if self.country != "italy":
                    #download other countries
                    print "\n downloading..."
                    url = "http://download.geofabrik.de/osm/europe/%s.osm.pbf" % country
                    call('wget -c %s -O %s.osm.pbf' % (url, country) , shell=True)
                    print "\n converting to 05m..."
                    call('osmconvert %s.osm.pbf -o=%s.o5m' % (country, country), shell=True)
                    call('rm %s.osm.pbf' % (country), shell=True)
                    #count tags "wikipedia=*"
                    tagsInCountry = self.count_wkp_tags_in_file(country)
                    tagsNum[country] = tagsInCountry
                print country, tagsNum[country]
        return todayDate, today

    def save_stats_to_csv(self):
        """Save stats to file
        """
        print "\n- Salvataggio dei dati su file CSV"
        statsDir = os.path.join("data", "stats")
        statsFile = os.path.join(statsDir, "stats.csv")
        oldStatsFile = os.path.join(statsDir, "old_stats.csv")
        if os.path.isfile(oldStatsFile):
            call('mv %s %s' % (statsFile, oldStatsFile), shell=True)
        ofile  = open(statsFile, "w")
        writer = csv.writer(ofile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
        #headers
        header = [" "] + [date for date in self.dates]
        writer.writerow(header)
        #days that must be saved to CSV file
        daysToSave = self.days
        #data
        for status in self.days[0]:
            values = [status] + [day[status] for day in daysToSave]
            writer.writerow(values)
        ofile.close()


### Copy webpages to a second directory ################################
    def copy_html_files_to_outdir(self):
        """Copy html files to another directory, for example Dropbox dir
        """
        print "\n- Copia i file delle pagine web nella directory '%s'" % self.OUTDIR
        if self.OUTDIR == "":
            print "\n  *Scrivi nel file 'config' --> 'outdir', il path della directory su cui copiare i file."
        else:
            call("cp -R ./html/* %s" % self.OUTDIR, shell=True)


def main():
    App()

if __name__ == '__main__':
    main()
