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

"""Extract lists of Wikipedia articles from wikipedia tags in an OSM file
"""

from lxml import etree
import urllib
import urllib2
import csv
from subprocess import call
import os

class ParseOSMData():
    def __init__(self, app):
        """ Read an OSM file containing only wikipedia*=* tagged data
            and extract tags and titles of Wikipedia articles.

            Returned variables:
            allTags = [list of Wikipedia tags], used to count tags numbers
            articles = {Wikipedia article title : tag}
            wrongTags = []
            badTags = {}
        """
        self.app = app

        #Read false positive
        self.falsePositiveTags = self.read_false_positive()

        #Parse OSM file and extract tags and osmIds
        self.allTags, self.tagsData = self.parse_osm_file()

        #Extract articles titles from tags
        #create dictionaries with data like {title : osmIds}
        self.titles = {}        #articles tagged in preferred the language
        self.wrongTags = {}     #wrong tags (lang is missing or url not from Wikipedia)
        self.badTags = {}       #warnings: tagged with a url instead of article title or upper lang
        self.foreignTitles = {} #articles tagged in foreign language
        dicts = self.extract_titles_from_tags()
        n = 0
        for lang, titles in self.foreignTitles.iteritems():
            n += len(titles)
        print "  %d tags referring to foreign languages have been found." % n

        #Translate foreign titles to preferred language
        self.nonexistent = {}
        foreignTitlesDisabled = False        #for debugging
        if foreignTitlesDisabled:
            print "\n  * foreignTitlesDisabled: not using foreign tagged articles"
            self.converted = {}
        else:
            #read old translations
            self.converted = self.old_converted_titles()
            #get from Wikipedia API titles translations
            self.translate_titles()
        #Add foreign, translated titles
        for lang, foreignTitles in self.foreignTitles.iteritems():
            for foreignTitle, osmids in foreignTitles.iteritems():
                if lang in self.converted and foreignTitle in self.converted[lang]:
                    title = self.converted[lang][foreignTitle]
                    #print "added translated article", foreignTitle, title
                    self.add_title_to_dict(self.titles, title, osmids)
                elif lang in self.nonexistent and foreignTitle in self.nonexistent[lang]:
                    #wrong tag
                    self.add_title_to_dict(self.wrongTags, foreignTitle.replace("_", " "), osmids)

    def read_false_positive(self):
        """Read from file ".data/workaround/false_positive.csv" tags
           that should not be considered as errors
        """
        tags = []
        ifile  = open(os.path.join("data", "workaround", "false_positive_tags.csv"), "rb")
        reader = csv.reader(ifile, delimiter = '\t')
        for row in reader:
            if row != [] and row[0][0] != "#":
                if len(row) == 1:
                    tags.append(row[0].decode("utf-8"))
        ifile.close()
        return tags

#### Parse OSM file ####################################################
    def parse_osm_file(self):
        """Extract from an OSM file wikipeida tags and OSM id where the
           tags are used
        """
        allTags = []
        tagsData = {}
        tags = []
        for event, element in etree.iterparse(self.app.wOSMFile, events=("end",)):
            #OSM element with Wikipedia tag.
            #Find corresponding Wikipedia article
            if "k" in element.keys():
                key = element.get("k")
                value = element.get("v")
                if not isinstance(key, unicode):
                    key = key.decode("utf-8")
                if not isinstance(value, unicode):
                    value = value.decode("utf-8")
                tagString = "%s=%s" % (key, value)
                if tagString in self.falsePositiveTags:
                    continue
                tags.append((key, value))
                allTags.append(tagString)
            if element.tag in ("node", "way", "relation"):
                #end of OSM object
                osmId = element.tag[0] + element.get("id")
                user = element.get("user")
                for tag in tags:
                    if tag not in tagsData:
                        tagsData[tag] = {"osmIds" : [], "users" : []}
                    tagsData[tag]["osmIds"].append(osmId)
                    tagsData[tag]["users"].append(user)
                #print element.tag, osmId, allObjects[osmId]
                tags = []       # reset tags
            element.clear()
        #print "\nWikipedia tags number (with duplicate): ", len(allTags)
        #print "\nwikipedia tags number (no duplicate): ", len(tagsData)
        return allTags, tagsData

    def extract_titles_from_tags(self):
        """Extract from the OSM tags the titles of articles and the
           OSM ids of the objects
        """
        prefLang = self.app.WIKIPEDIALANG
        #dicts = {"w_lang"           : {} wikipedia = lang:title,
        #             "w_LANG"                   : {} wikipedia = LANG:title,
        #             "wLang"            : {} wikipedia:lang = title,
        #             "wLANG_ "                  : {} wikipedia:LANG = title,
        #             "w_urlLang"        : {} wikipedia = http(s)://lang.wikipedia.org/title,
        #             "w_LANGUrl"                : {} wikipedia = http(s)://LANG.wikipedia.org/title,
        #             "w_urlForeignlang" : {} wikipedia = http(s)://foreign lang.wikipedia.org/title,
        #             "w_Foreignlang"    : {} wikipedia = foreign lang:title,
        #             "wForeignlang"     : {} wikipedia = foreign lang:title,
        #             "langMissing"              : {}} wikipedia = title (lang missing)

        dicts = {"w_lang"           : {},
                 "w_LANG"           : {},
                 "wLang_"           : {},
                 "wLANG_"           : {},
                 "w_langUrl"        : {},
                 "w_LANGurl"        : {},
                 "w_foreignlangUrl" : {},
                 "w_foreignlang"    : {},
                 "wForeignlang_"    : {},
                 "langMissing"      : {}}

        for tag, tagData in self.tagsData.iteritems():
            osmIds = tagData["osmIds"]
            #for (key, value) in tags:
            (key, value) = tag
            tagString = "%s=%s" % (key, value)
            #Exclude "strange" tags
            if key in ("wikipedia:image",
                       "wikipedia:operator",
                       "wikipedia:architect"):
                continue
            if key == "wikipedia":
                # tag type wikipedia = *
                if value.find(":http") != -1:
                    ## wikipeida = *:http://en....
                    self.add_title_to_dict(self.wrongTags, tagString, osmIds)
                    continue
                if value.find(":") == -1:
                    ## wikipedia = title --> wrong tag: lang is missing
                    self.add_title_to_dict(dicts["langMissing"], tagString, osmIds)
                    self.add_title_to_dict(self.wrongTags, tagString, osmIds)
                else:
                    # wikipedia = *:*
                    if len(value.split(":")) > 2:
                        ## wikipedia = *:*:*
                        self.add_title_to_dict(self.wrongTags, tagString, osmIds)
                        continue
                    if not value.startswith("http"):
                        language, title = value.split(":")
                        if language == prefLang:
                            ## wikipedia = pref lang:title
                            self.add_title_to_dict(dicts["w_lang"], tagString, osmIds)
                            self.add_title_to_dict(self.titles, title, osmIds)
                        elif language == prefLang.upper():
                            ## wikipedia = PREF LANG:title --> bad tag
                            self.add_title_to_dict(dicts["w_LANG"], tagString, osmIds)
                            self.add_title_to_dict(self.titles, title, osmIds)
                            self.add_title_to_dict(self.badTags, tagString, osmIds)
                        else:
                            ## wikipedia = foreign lang:title
                            self.add_title_to_dict(dicts["w_foreignlang"], "%s:%s" % (language, title), osmIds)
                            self.add_title_to_foreignTitles(language, title, osmIds)
                    else:
                        ## wikipedia = url
                        self.add_title_to_dict(self.badTags, tagString, osmIds)
                        value = urllib.unquote(value)
                        params = value.split("/")
                        if len(params) >= 4:
                            if params[2][-13:] == "wikipedia.org":
                                title = params[-1]
                                language = params[2].split(".")[0]
                                if language == prefLang:
                                    ### wikipedia = http://pref lang.wikipedia.org/*
                                    self.add_title_to_dict(dicts["w_langUrl"], tagString, osmIds)
                                    self.add_title_to_dict(self.titles, title, osmIds)
                                elif language == prefLang.upper():
                                    ### wikipedia = ttp://PREF LANG.wikipedia.org/* --> bad tag
                                    self.add_title_to_dict(dicts["w_LANGurl"], tagString, osmIds)
                                    self.add_title_to_dict(self.titles, title, osmIds)
                                else:
                                    ### wikipedia = http://foreign lang.wikipedia.org/*
                                    self.add_title_to_dict(dicts["w_foreignlangUrl"], "%s:%s" % (language, title), osmIds)
                                    self.add_title_to_foreignTitles(language, title, osmIds)
                            else:
                                ### wrong url, not Wikipedia url --> wrong tag
                                self.add_title_to_dict(self.wrongTags, tagString, osmIds)

            elif key.find(":") != -1:
                # wikipedia:*=*
                language = key.split(":")[1]
                if value.find(":") == -1:
                    ## wikipedia:* = *
                    title = value
                    if language == prefLang:
                        ### wikipedia:pref lang=title
                        self.add_title_to_dict(dicts["wLang_"], title, osmIds)
                        self.add_title_to_dict(self.titles, title, osmIds)
                    elif language == prefLang.upper():
                        ### wikipedia:PREF LANG=title --> bad tag
                        self.add_title_to_dict(dicts["wLANG_"], tagString, osmIds)
                        self.add_title_to_dict(self.titles, title, osmIds)
                        self.add_title_to_dict(self.badTags, tagString, osmIds)
                    else:
                        ### wikipedia:foreign lang=title
                        self.add_title_to_dict(dicts["wForeignlang_"], "%s:%s" % (language, title), osmIds)
                        self.add_title_to_foreignTitles(language, title, osmIds)
                else:
                    ## wikipedia:* = *:*
                    if value.find("http") == -1:
                        # wikipedia:* = *:title
                        self.add_title_to_dict(self.wrongTags, tagString, osmIds)
                    else:
                        ### wikipedia:* = url
                        self.add_title_to_dict(self.badTags, tagString, osmIds)
                        value = urllib.unquote(value)
                        params = value.split("/")
                        if len(params) >= 4:
                            if params[2][-13:] == "wikipedia.org":
                                title = params[-1]
                                urlLanguage = params[2].split(".")[0]
                                if urlLanguage != language:
                                    #### wikipedia:X = http:Y.wikipedia.org...
                                    self.add_title_to_dict(self.wrongTags, tagString, osmIds)
                                    continue
                                if urlLanguage == prefLang:
                                    #### wikipedia = http://pref lang.wikipedia.org/*
                                    self.add_title_to_dict(dicts["w_langUrl"], tagString, osmIds)
                                    self.add_title_to_dict(self.titles, title, osmIds)
                                elif urlLanguage == prefLang.upper():
                                    #### wikipedia = ttp://PREF LANG.wikipedia.org/* --> bad tag
                                    self.add_title_to_dict(dicts["w_LANGurl"], tagString, osmIds)
                                    self.add_title_to_dict(self.titles, title, osmIds)
                                else:
                                    #### wikipedia = http://foreign lang.wikipedia.org/*
                                    self.add_title_to_dict(dicts["w_foreignlangUrl"], "%s:%s" % (language, title), osmIds)
                                    self.add_title_to_foreignTitles(language, title, osmIds)
                            else:
                                #### wrong url, not Wikipedia url --> wrong tag
                                self.add_title_to_dict(self.wrongTags, tagString, osmIds)
        return dicts

    def add_title_to_foreignTitles(self, language, title, osmIds):
        if language not in self.foreignTitles:
            self.foreignTitles[language] = {}
        self.add_title_to_dict(self.foreignTitles[language], title, osmIds)

    def add_title_to_dict(self, dictionary, title, osmIds):
        """Add article title and osmIds to a dictionary
        """
        title = title.replace(" ", "_")
        if title not in dictionary:
            dictionary[title] = []
        for osmId in osmIds:
            if osmId not in dictionary[title]:
                dictionary[title].append(osmId)

    def sum_dictionaries(self, dictionariesList):
        """Sum dictionaries with a list as value
        """
        dictA, dictB = dictionariesList[:2]
        dictC = dictA
        for title, osmIds in dictB.iteritems():
            if not title in dictC:
                dictC[title] = []
            for osmId in osmIds:
                if not osmId in dictC[title]:
                    dictC[title].append(osmId)
        for dictionary in dictionariesList[2:]:
            dictC = self.sum_dictionaries([dictC, dictionary])
        return dictC

### Query Wikipedia API for foreign --> preferred language titles translation
    def translate_titles(self):
        """Converts foreign titles to the corresponding titles
           in the preferred language, by asking it to Wikipedia.
        """
        #Group the titles by language, {lang : [title, title, ...], ...}
        titlesPerLang = {}
        for language, foreignTitles in self.foreignTitles.iteritems():
            for foreignTitle, osmIds in foreignTitles.iteritems():
                if foreignTitle.find("#") == -1:
                    #Skipp wikipedia*=*article#section
                    #it is not possible to find a section of a page in a
                    #language corresponding to a section of another language
                    if language in self.converted and foreignTitle in self.converted[language]:
                        #We already know the title of this article in preferred language
                        #print "translation already known", language, foreignTitle
                        continue
                    if language not in titlesPerLang:
                        titlesPerLang[language] = []
                    titlesPerLang[language].append(foreignTitle)

        #Create strings of 50 titles per language, to ask to Wikipedia
        #for translation
        #titlesStringsPerLang = {lang : ["title1|...|title50",
        #                                "title1|...|title50",
        #                                ...],
        #                        lang : [], ...}
        stringsPerLang = {}
        for language, titles in titlesPerLang.iteritems():
            if language not in stringsPerLang:
                stringsPerLang[language] = []
            for fiftyTitles in [sorted(titles[i:i+50]) for i in range(0, len(titles), 50)]:
                titlesString = "|".join(fiftyTitles).replace("_", " ")
                stringsPerLang[language].append(titlesString)
            print "  %d articles must be translated from %s" % (len(titles), language)

        #Query Wikipedia API, 50 titles of the same language per time
        self.nonexistent = {}        # non existent page or wrong url

        #stringsPerLang = {"hr" : stringsPerLang["hr"]}      #debugging

        for language, fiftyStringsList in stringsPerLang.iteritems():
            print "\n- Get translations for %s titles:" % language
            for fiftyStrings in fiftyStringsList:
                answer = self.download_converted_titles(language, fiftyStrings)
                #answer = True
                if answer:
                    self.parse_wikipedia_answer(language)

        #Save updated conversions (converted) to file
        self.save_updated_conversions()

    def download_converted_titles(self, lang, titlesString):
        """Query Wikipedia API for titles conversion from foreing to
           preferred language
        """
        string = urllib.quote_plus(titlesString.encode("utf-8"))
        url = "https://%s.wikipedia.org/w/api.php?action=query&prop=langlinks&lllang=it&format=xml&lllimit=55&titles=%s" % (lang.encode("utf-8"), string)
        #answer = raw_input("\n  Download from Wikipedia 50 titles translations from %s?\n  titles:\n%s\n  url:\n%s\n  [y|n]" % (lang.encode("utf-8"), titlesString.encode("utf-8"), url))
        answer = "y"
        if answer == "y":
            try:
                #print "\n", url
                wikipediaAnswer = urllib2.urlopen(url)
            except:
                print "\n Wrong url because lang was wrong:", string
                titles = [t.replace(" ", "_") for t in titlesString.split("|")]
                self.add_to_nonexistent(lang, titles)
                print "\n- nonexistent titles returned from Wikipedia:\n", titles
                return False
            else:
                if wikipediaAnswer == None:
                    print "\n Answer None"
                    titles = [t.replace(" ", "_") for t in titlesString.split("|")]
                    self.add_to_nonexistent(lang, titles)
                    print "\n- nonexistent titles returned from Wikipedia:\n", titles
                    return False
                else:
                    #print "\nOK, Saving answer"
                    file_out = open(self.app.WIKIPEDIAANSWER, "w")
                    file_out.write(wikipediaAnswer.read())
                    file_out.close()
                    return True

    def parse_wikipedia_answer(self, language):
        """Extract form Wikipedia answer correspondeces between foreing
           and preferred language article
        """
        #print "  parsing answer"
        converted = {}      #{foreign title : translated title, ...}
        nonexistent = []    #[nonexistent title, ...]
        for event, element in etree.iterparse(self.app.WIKIPEDIAANSWER, events=("end",)):
            if element.tag == "page":
                title = element.get("title")
                if "invalid" in element.keys() or "missing" in element.keys():
                    #print "X doesn't exist", title, "in language", language
                    nonexistent.append(title.replace(" ", "_"))
                elif len(element.getchildren()) == 0:
                    #print "X article in preferred lang is missing or foreign \
#is a redirect (this is wrong for WIWOSM rules). Ignore it."
                    continue
                elif len(element.getchildren()) != 0:
                    prefTitle = element[0][0].text
                    #print "OK, converted: %s ---> %s:" % (title, prefTitle)
                    converted[title.replace(" ", "_")] = prefTitle.replace(" ", "_")
        self.add_to_nonexistent(language, nonexistent)
        self.add_to_converted(language, converted)
        #print "\n parsing done."

    def add_to_nonexistent(self, language, titles):
        if language not in self.nonexistent:
            self.nonexistent[language] = []
        self.nonexistent[language].extend(titles)
        print "  nonexistent titles in %s: %d" % (language, len(titles))
        for title in titles:
            print " ", title.encode("utf-8")

    def add_to_converted(self, language, newconverted):
        if language not in self.converted:
            self.converted[language] = {}
        for foreignTitle, prefTitle in newconverted.iteritems():
            self.converted[language][foreignTitle] = prefTitle
        #print "\n- titles converted to preferred language: %s, (%d)" % (language, len(newconverted))


### Manage CSV file with titles translations ###########################
    def old_converted_titles(self):
        """Read CSV file with the conversions done in the past
           foreign lang -- foreign title -- title in preferred language
        """
        converted = {}
        fileName = os.path.join(self.app.WIKIPEDIAANSWERS, "conversions.csv")
        if os.path.isfile(fileName):
            inFile  = open(fileName, "r")
            reader = csv.reader(inFile, delimiter='\t')
            for row in reader:
                language, foreignTitle, title = row
                foreignTitle = foreignTitle.decode("utf-8")
                title = title.decode("utf-8")
                if language not in converted:
                    converted[language] = {}
                converted[language][foreignTitle] = title
            inFile.close()
        #self.print_translations(converted)
        return converted

    def print_translations(self, c):
        for lang, translations in c.iteritems():
            print
            print "language:", lang
            for foreign, preferred in translations.iteritems():
                print "%s --> %s" % (foreign, preferred)

    def save_updated_conversions(self):
        print "\n- Salvataggio del file con le traduzioni"
        fileName = os.path.join(self.app.WIKIPEDIAANSWERS, "conversions.csv")
        oldFileName = os.path.join(self.app.WIKIPEDIAANSWERS, "old_conversions.csv")
        call("cp '%s' '%s'" % (fileName, oldFileName), shell=True)
        fileOut = open(fileName, "w")
        writer = csv.writer(fileOut, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
        n = 0
        for language, data in self.converted.iteritems():
            for foreignTitle, preferredTitle in data.iteritems():
                row = [language, foreignTitle.encode("utf-8"), preferredTitle.encode("utf-8")]
                writer.writerow(row)
                n += 1
        fileOut.close()
        print "  %d titoli di articoli tradotti nella lingua preferita e salvati in %s" % (n, fileName)
