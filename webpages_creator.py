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

"""Create webpages with the lists of Wikipedia categories and articles
"""

import os
import urllib
from data_manager import Category, Article
from subprocess import call


### Helpers ############################################################
class Helpers:
    def progress_strings(self, item, mode):
        """Calculate tagging progress
        """
        number = item.progress[mode]["num"]
        progressString = item.progress[mode]["string"]
        if number == 0.0:
            classe = "done0"
        elif number == 1.0:
            classe = "done100"
        elif number <= 0.25:
            classe = "done025"
        elif number <= 0.50:
            classe = "done050"
        elif number <= 0.75:
            classe = "done075"
        else:
            classe = "done099"
        return classe, progressString

    def wikipedia_link(self, item):
        text = item.name.replace("_", " ")
        title = "Vedi %s: %s" % (item.typ.lower(), text.replace("\"", "&quot;"))
        cssClass = ' class="wikipedia_link"'
        link = self.url_to_link(item.wikipediaUrl, title, text, None, cssClass)
        return link

    def osm_ids_string_for_overpass(self, osmIds):
        """Return an OSM ids string used by Overpass
        """
        osmTypeAbbr = {"n": "node", "w": "way", "r": "relation"}
        osmIdsString = ""
        for osmId in osmIds:
            osmIdsString += '%s(%s);' % (osmTypeAbbr[osmId[0]], osmId[1:])
        return osmIdsString

    def overpass_query(self, item):
        if isinstance(item, Article):
            elementsString = self.osm_ids_string_for_overpass(item.osmIds)
        elif isinstance(item, Category):
            elementsString = self.osm_ids_string_for_overpass(item.allOsmIds)
        else:
            #wrongTags and badTags are not articles nor categories
            elementsString = self.osm_ids_string_for_overpass(item)
        query = '('
        query += elementsString
        query += ');'
        query += '(._;>;);'
        query += 'out meta qt;'
        return query

    def josm_link(self, mode, data, img):
        url = "http://localhost:8111/"
        if mode == "download":
            url += "import?url=http://overpass.osm.rambler.ru/cgi/interpreter?data=" + data
            title = "Scarica in JOSM"
        elif mode == "load_and_zoom":
            left = data[1] - 0.0005
            right = data[1] + 0.0005
            top = data[0] + 0.0005
            bottom = data[0] - 0.0005
            url += "load_and_zoom?left=%f&right=%f&top=%f&bottom=%f" % tuple((left, right, top, bottom))
            title = "Zooma in JOSM vicino all'oggetto da taggare"
        link = self.url_to_link(url, title, None, img)
        return link

    def overpass_turbo_link(self, query, cssClass=""):
        url = 'http://overpass-turbo.eu/index.html?Q=%s&R' % urllib.quote_plus(query)
        title = "Visualizza come mappa cliccabile, immagine... (Overpass Turbo)"
        img = "../img/Overpass-turbo.png"
        if cssClass != "":
            cssClass = ' class="%s"' % cssClass
        link = self.url_to_link(url, title, None, img, cssClass)
        return link

    def osm_ids_string(self, item):
        osmTypeAbbr = {"n": "node", "w": "way", "r": "relation"}
        links = {"nodes": [], "ways": [], "relations": []}
        if isinstance(item, Article):
            osmIds = item.osmIds
        else:
            #item == ids of wrongTags or badTags
            osmIds = item
        #create links to OSM web pages
        for osmId in osmIds:
            url = "http://www.openstreetmap.org/browse/%s/%s" % (osmTypeAbbr[osmId[0]], osmId[1:])
            link = self.url_to_link(url, "%s" % "Vedi pagina OSM", osmId[1:])
            links[osmTypeAbbr[osmId[0]] + "s"].append(link)
        osmIdsString = ""
        for osmType, linksList in links.iteritems():
            if len(linksList) > 0:
                if osmIdsString != "":
                    osmIdsString += "<br>"
                if isinstance(item, Article):
                    imgPath = "../img/"
                else:
                    imgPath = "./img/"
                img = '<img title="%s" src=%s%s.png>' % (osmType[:-1], imgPath, osmType)
                osmIdsString += "%s %s" % (img, ", ".join(linksList))
        if isinstance(item, Article):
            #put the string into a div
            osmDivId = item.ident
            osmIdsString = '<div id="%s" style="display:none"><br>%s</div>' % (osmDivId, osmIdsString)
        return links, osmIdsString

    def missing_template_link(self, article):
        title = "Sulla pagina Wikipedia manca il template coord"
        img = "../img/no_template.png"
        link = '<span class="missing_template_alert"><img src="%s" title="%s" class="articleLinkImg"></span>' % (img, title)
        return link

    def add_tags_link(self, category):
        url = "http://toolserver.org/~kolossos/osm-add-tags/index.php?"
        url += "lang=it"
        url += "&bbox=%s" % self.app.COUNTRYBBOX
        url += "&cat=%s" % urllib.quote_plus(category.name.encode("utf-8"))
        url += "&key=*&value=*&basedeep=10&types=*&request=Submit&iwl=yes"
        title = "Cerca oggetti ed aggiungi tag (WIWOSM add-tags)"
        img = "../img/add-tags.png"
        link = self.url_to_link(url, title, None, img)
        return link

    def url_to_link(self, url, title, text, img=None, cssClass="", target=""):
        """Return a link from some parameters
        """
        if target is None:
            target = ""
        else:
            target = ' target="_blank"'
        if img is not None:
            textOrImg = '<img src="%s" class="articleLinkImg">' % img
        else:
            textOrImg = text
        code = '<a href="%s" title="%s"%s%s>%s</a>' % (url, title, target, cssClass, textOrImg)
        return code

    def tagged_article_links(self, app, article):
        """Create links for tagged article from OSM objects to various
           services
        """
        #WIWOSM link
        wiwosmUrl = "http://toolserver.org/~kolossos/openlayers/kml-on-ol-json3.php?lang=%s&title=%s" % (app.WIKIPEDIALANG, article.name)
        wiwosmTitle = "Vedi mappa Wikipedia (WIWOSM)"
        wiwosmImg = "../img/wiwosm.png"
        wiwosmLink = self.url_to_link(wiwosmUrl, wiwosmTitle, None, wiwosmImg)

        #Show a div with OSM ids of the article
        #osm ids div
        osmLinks, osmIdsDiv = self.osm_ids_string(article)
        #link for showing the div
        osmUrl = "javascript:showHideDiv(\'%s\');" % article.ident
        osmLinkTitle = "Vedi pagina OSM"
        #check what kinds of OSM primitive are tagged and use the
        #right icon
        osmTypeAbbr = [osmType[0] for osmType in osmLinks if osmLinks[osmType] != []]
        osmLinkImg = "../img/osm_%s.png" % "".join(sorted(osmTypeAbbr))
        osmLink = self.url_to_link(osmUrl, osmLinkTitle, None, osmLinkImg, "", None)

        query = self.overpass_query(article)

        #JOSM remote control link
        img = "../img/josm.png"
        josmLink = self.josm_link("download", query, img)

        #Overpass Turbo link
        overpassTurboLink = self.overpass_turbo_link(query)

        code = '\n      %s ' % wiwosmLink
        code += '\n      %s ' % osmLink
        code += '\n      %s ' % josmLink
        code += '\n      %s' % overpassTurboLink
        if app.args.show_missing_templates and hasattr(article, "hasTemplate"):
            if not article.hasTemplate:
                code += '\n      %s' % self.missing_template_link(article)
        code += '\n      %s' % osmIdsDiv
        return code

    def non_tagged_article_links(self, app, article):
        """Create links to various services for an article not tagged in OSM yet
        """
        if hasattr(article, "wikipediaCoords"):
            #the article is not tagged but Wikipedia knows its coordinates
            img = "../img/josm_load_and_zoom.png"
            if article.wikipediaCoordsSource == 'Nuts4Nuts':
                img = "../img/josm_load_and_zoom_blue.png"
            code = self.josm_link("load_and_zoom", article.wikipediaCoords, img)
        else:
            code = ""
        return code

    def header_needed(self, subitems, attributeName):
        """Return True or False if any subcategory has wikipediaCoordinates
           or misses Coord template. It is used to know if it is
           necessary to show headers in index tables
        """
        for subitem in subitems:
            if subitem.isMappable:
                if getattr(subitem, attributeName) > 0:
                    return True
        return False


### Webpages creator ###################################################
class Creator():
    def __init__(self, app):
        self.app = app
        #When selectNonMappable==True the cells of tables in webpages
        #can be clicked, to create list of non mappable articles
        #or categories that can be copied into the file ./data/wikipedia/non_mappable
        selectNonMappable = True if app.clickable_cells == "true" else False
        self.homepages = []
        #Create homepage
        modes = ("themes", "regions")
        for modeNumber, mode in enumerate(modes):
            modeInfo = (modeNumber, mode)
            self.homepages.append(Homepage(app, modeInfo).code)

        #Create categories pages
        for theme in app.themes:
            for category in theme.categories:
                category.articles_html = ArticlesTable(app, category, selectNonMappable).code
                for subcategory in category.subcategories:
                    subcategory.html = CategoryTable(app, subcategory, selectNonMappable).code
                category.html = Subpage(app, "themes", "", category, selectNonMappable).code

        #Create regions pages
        for region in app.regions:
            region.html = Subpage(app, "regions", "_1", region, selectNonMappable).code

        #Create errors page
        self.errorsHtml = ErrorsPage(app).code

        #Save all HTML files
        self.save_html_files()

    def save_html_files(self):
        """Save webpages as html files
        """
        # homepage
        for i, homepage in enumerate(self.homepages):
            filename = "index.html"
            if i > 0:
                filename = "index_%d.html" % i
            self.save_file(self.homepages[i], filename)
        # categories pages
        for theme in self.app.themes:
            for category in theme.categories:
                categoryFile = os.path.join("subpages", "%s.html" % category.name)
                self.save_file(category.html, categoryFile)
        # regions pages
        for region in self.app.regions:
            regionFile = os.path.join("subpages", "%s.html" % region.name)
            self.save_file(region.html, regionFile)
        # errors page
        self.save_file(self.errorsHtml, "errors.html")
        if not self.app.args.nofx:
            call("firefox html/index.html", shell=True)

    def save_file(self, text, fileName):
        fileOut = open(os.path.join(self.app.HTMLDIR, fileName), "w")
        if isinstance(text, unicode):
            text = text.encode("utf-8")
        fileOut.write(text)
        fileOut.close()


### Homepage ###########################################################
class Homepage(Helpers):
    def __init__(self, app, modeInfo):
        """Homepage with two tabs: themes, regions
        """
        (modeNumber, mode) = modeInfo
        modesNames = ["Temi", "Regioni"]
        modesTitles = ["Visualizza categorie per tema",
                       "Visualizza categorie per regione"]
        self.app = app
        code = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" http://www.w3.org/TR/html4/loose.dtd>'
        code += '\n<html>\n  <head>'
        code += '\n    <meta http-equiv="Content-type" content="text/html;charset=UTF-8">'
        code += '\n    <title>Articoli di Wikipedia mappabili in OSM</title>'
        if self.app.args.bitly:
            stylecss = "http://bit.ly/1brC3Kk"
        else:
            stylecss = "style.css"
        code += '\n    <link rel="stylesheet" type="text/css" href="%s">' % stylecss
        code += '\n      <script type="text/javascript" charset="utf-8">'
        code += '\n        function showHideDiv(elementid){'
        code += '\n          if (document.getElementById(elementid).style.display == "none"){'
        code += '\n              document.getElementById(elementid).style.display = "";'
        code += '\n              }'
        code += '\n          else {'
        code += '\n              document.getElementById(elementid).style.display = "none";'
        code += '\n              }'
        code += '\n          }'
        code += '\n      </script>'
        code += '\n  </head>'
        code += '\n<body>'
        code += '\n  <div id="update_time">Aggiornamento: %s</div>' % self.app.UPDATETIME
        code += '\n  <div id="header">'
        code += '\n    <h1><a id="top"></a>Articoli Wikipedia mappabili in OSM</h1>'
        code += '\n    <p>Liste di articoli Wikipedia (IT) mappabili in OpenStreetMap, tramite il tag "<b><a href="http://wiki.openstreetmap.org/wiki/Wikipedia" target="_blank">wikipedia</a> = it:Titolo dell\'articolo</b>".</p>'
        code += '\n    <!-- Informations -->'
        code += '\n    <p><a id="description" href="javascript:showHideDiv(\'info\');"><img src="./img/info.png" class="infoImg"> Informazioni e conteggi</a> | <a href="errors.html" title="Visualizza tag sospetti">Tag sospetti</a></p>'
        #Info
        code += '\n    <div id="info" style="display:none">'
        if self.app.users != {}:
            code += self.users_table()
        code += self.stats_table()
        code += '\n      <h2></h2>'
        code += '\n      <ul>'
        code += '\n        <li>Gli oggetti taggati compaiono in Wikipedia <a href="http://toolserver.org/~kolossos/openlayers/kml-on-ol.php?lang=it&uselang=de&params=41.89_N_12.491944444444_E_region%3AIT_type%3Alandmark&title=Colosseom&zoom=18&lat=41.89&lon=12.49284&layers=B00000FTTTF">su una mappa</a> (progetto <a href="http://wiki.openstreetmap.org/wiki/WIWOSM" target="_blank">WIWOSM</a>).</li>'
        code += '\n        <li>La presenza di questi tag migliora i risultati delle ricerche eseguite su www.openstreetmap.org (Nominatim).</li>'
        code += '\n      </ul>'
        code += '\n      <h2>Come</h2>'
        code += '\n      <ul>'
        code += '\n        <li>Aggiungere all\'oggetto in OSM il tag <b>"wikipedia=it:Titolo dell\'articolo"</b>, lasciando gli spazi tra le parole.<br>Basta <b>una sola lingua</b>, se l\'articolo è già taggato in una lingua straniera non occorre aggiungere quella italiana (vedi <a href="http://wiki.openstreetmap.org/wiki/Wikipedia" target="_blank"> eccezioni</a> sul Wiki di OSM).</li>'
        code += '\n      </ul>'
        code += '\n      <h2>Strumenti utili per aggiungere tag</h2>'
        code += '\n      <ul>'
        code += '\n        <li><a href="http://josm.openstreetmap.de/wiki/Help/Plugin/Wikipedia" target="_blank">Plugin Wikipedia</a> per <a href="http://wiki.openstreetmap.org/wiki/IT:JOSM" target="_blank">JOSM</a>.</li>'
        code += '\n        <li><a href="http://wiki.openstreetmap.org/wiki/JOSM/Plugins/RemoteControl/Add-tags" target="_blank">add-tags</a>, si può usare questo servizio anche cliccando sulle icone <img src="./img/add-tags.png"> presenti in queste pagine.'
        code += '\n      </ul>'
        code += '\n      <h2>Difetti nelle liste</h2>'
        code += '\n      <ul>'
        code += '\n        <li> Articoli o categorie <b>non mappabili</b>, ad es. "es. Dipinti nel Museo Tal Dei Tali", possono essere rimossi dalla pagina, se segnalati (vedi mail).</li>'
        code += '\n        <li> Può accadere che in una sottocategoria ricadano articoli non riguardanti il tema di partenza. Se questi sono mappabili vengono comunque mostrati in tabella.</li>'
        code += '\n        <li> Articoli o sottocategorie appartenenti a più categorie possono ripetersi più volte in una stessa pagina (i conteggi ne tengono conto).</li>'
        code += '\n      </ul>'
        code += '\n      <h2>Programma per generare le pagine</h2>'
        code += '\n      <p>Codice: <a href="https://github.com/simone-f/wikipedia-tags-in-osm" target="_blank">wikipedia-tags-in-osm %s</a> (GPLv3)\
<br>Autore: <a href="mailto:groppo8@gmail.com">Simone F.</a></p>' % self.app.version
        code += '\n      <p>Contributors: Luca Delucchi, CristianCantoro</p>'
        code += '\n      <p><br>Riconoscimenti ed attribuzioni:</p>'
        code += '\n      <p>Servizi linkati da queste pagine: \
<a href="http://wiki.openstreetmap.org/wiki/WIWOSM">WIWOSM</a> (master, Kolossos), \
<a href="http://wiki.openstreetmap.org/wiki/JOSM/Plugins/RemoteControl/Add-tags" target="_blank">add-tags</a> (Kolossos), \
<a href="http://overpass-turbo.eu/" target="_blank">OverpassTurbo</a> (tyr.asd).</p>'
        code += '\n      <p>Servizi usati per creare le pagine: \
<a href="http://toolserver.org/%7Edaniel/WikiSense/CategoryIntersect.php" target="_blank">CatScan</a> (Duesentrieb), \
<a href="http://toolserver.org/~kolossos/wp-world/pg-dumps/wp-world/">Wikipedia coordinates</a> (Kolossos), \
<a href="http://nuts4nutsrecon.spaziodati.eu/">Nuts4Nuts</a>, \
<a href="http://tools.wmflabs.org/catscan2/quick_intersection.php">quick_intersection</a> (Magnus Manske).</p>'
        code += '\n      <p>Icone dei temi: <a href="https://github.com/mapbox/maki" target="_blank"">Maki</a> (BSD)<br>'
        code += '\n      Stemmi regionali: <a href="http://www.araldicacivica.it" target="_blank">www.araldicacivica.it</a> (<a href="http://creativecommons.org/licenses/by-nc-nd/3.0/it/">CC BY-NC-ND 3.0</a>)<br>'
        code += '\n      Icone di nodi, way, relazioni ed Overpass Turbo da <a href="http://wiki.openstreetmap.org/">Wiki OSM</a>.</p>'
        code += '\n    </div>'
        #Tabs: themes|regions
        code += '\n    <div id="tabs">'
        code += '\n      <ul>'
        for n, modeName in enumerate(modesNames):
            tabid = ""
            filename = "./index"
            if n > 0:
                filename += "_%d" % n
            filename += ".html"
            if n == modeNumber:
                tabid = ' id ="selected"'
            code += '\n        <li%s><a title="%s" href="%s">%s</a></li>' % (tabid, modesTitles[n], filename, modeName)
        code += '\n       </ul>'
        code += '\n    </div>'
        code += '\n  </div>'
        code += '\n  <div id="content">'
        code += self.themes_and_regions_tabs(mode).encode("utf-8")
        code += '\n  </div>'
        code += '\n</body>\n</html>'
        self.code = code

    def stats_table(self):
        """Return html code of a table with the numbers of tagged/non tagged
           articles of the first and the last 9 days
        """
        red = "#cc0000"
        green = "#00cc7a"
        modes = [("to do", "Da mappare"),
                 ("mapped", "Mappati"),
                 ("total", "Totali")]

        code = '\n      <table id="stats">'
        code += '\n        <tr>'
        code += '\n          <th>Articoli</th>'
        if len(self.app.dates) >= 11:
            dates = [self.app.dates[0]] + self.app.dates[-9:]
            days = [self.app.days[0]] + self.app.days[-9:]
        else:
            dates = self.app.dates
            days = self.app.days
        #dates
        for date in dates:
            code += '\n          <th>%s</th>' % date
        code += '\n        </tr>'
        for mode, description in modes:
            #first cell
            if mode == "total":
                code += '\n        <tr>'
                code += '\n          <th colspan="%d">Tag</th>' % (len(days) + 1)
                code += '\n        </tr>'
            code += '\n        <tr>'
            code += '\n          <td>%s</td>' % description
            #data
            for index, day in enumerate(days):
                value = int(day[mode])
                differenceStr = ""
                if index > 0:
                    previousValue = int(days[index - 1][mode])
                    difference = int(value) - previousValue
                    if difference != 0:
                        differenceStr = str(difference)
                        if difference > 0:
                            if mode == "to do":
                                color = red
                            else:
                                color = green
                            differenceStr = "+%s" % differenceStr
                        elif difference < 0:
                            if mode == "to do":
                                color = green
                            else:
                                color = red
                        differenceStr = ' <span style = "color: %s">(%s)</span>' % (color, differenceStr)
                code += '\n          <td>%s%s</td>' % (value, differenceStr)
            code += '\n        </tr>'
        code += '\n      </table>'
        return code

    def users_table(self):
        """Return html code of a table with the mappers which added
           tags from the previous run of the program
        """
        #users = [[user name, tags num], ...]
        users = sorted(self.app.users.items(), key=lambda x: x[1], reverse=True)
        code = '\n      <div id="users">'
        code += '\n      <table id="users">'
        code += '\n        <tr><th>Mapper</th><th>Tag</th></tr>'
        for user, tagsNumber in users:
            mapperLink = '<a href="http://www.openstreetmap.org/user/%s/">%s</a>' % (urllib.quote_plus(user.encode("utf-8")), user.encode("utf-8"))
            code += '\n        <tr><td>%s</td><td>%s</td></tr>' % (mapperLink, tagsNumber)
        code += '\n      </table>'
        code += '\n      </div>'
        return code

    def main_index(self, items, mode):
        """Return html code of a table with themes or regions, to be used
           as main index of the homepage
        """
        code = '\n    <table id="home_index">'
        code += '\n      <tr>'
        columns = 5
        rows = [items[i:i + columns] for i in range(0, len(items), columns)]
        for row in rows:
            code += '\n      <tr>'
            for item in row:
                iconFile = "./img/%s/%s.png" % (mode, item.name.lower())
                if os.path.isfile(os.path.join(self.app.HTMLDIR, iconFile)):
                    icon = '<img src=%s>' % iconFile
                else:
                    icon = ""
                code += '\n        <td><a href="#%s">%s%s</a></td>' % (item.name, icon, item.name.replace("_", " "))
            code += '\n      </tr>'
        code += '\n    </table>'
        return code

    def themes_and_regions_tabs(self, mode):
        """Return html code of homepage tabs: themes and regions
        """
        #Main index table with icons of themes or regions
        if mode == "themes":
            items = self.app.themes
        else:
            items = self.app.regions
        code = self.main_index(items, mode)
        #Indexes with categories in each theme or region
        for itemIdx, item in enumerate(items):
            #Title
            linkTop = '<a href=#top>&#8593;</a>'
            itemImg = '<img src="./img/%s/%s.png" class="item_img">' % (mode, item.name.lower())
            itemTitle = '%s%s' % (itemImg, item.name.replace("_", " "))
            if mode == "regions":
                itemTitle = '<a href="./subpages/%s.html" title="Visualizza pagina della regione">%s</a>' % (item.name, itemTitle)
            code += '\n\n    <h3>%s<a id="%s"></a>%s</h3>' % (linkTop, item.name, itemTitle)
            #index of categories with progress
            pageType = "home"
            if itemIdx == 0:
                showProgressHeader = True
            else:
                showProgressHeader = False
            code += '\n%s' % IndexOfCategories(self.app, item, mode, pageType, showProgressHeader).code
        return code


### Subpage ############################################################
class Subpage(Helpers):
    def __init__(self, app, mode, suffix, item, selectNonMappable):
        """A webpage with data about a main category or a region.
        """
        self.app = app
        code = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" http://www.w3.org/TR/html4/loose.dtd>'
        code += '\n<html>\n    <head>'
        code += '\n        <meta http-equiv="Content-type" content="text/html;charset=UTF-8">'
        code += '\n        <title>%s</title>' % self.app.homePageTitle
        code += '\n        <link rel="stylesheet" type="text/css" href="../style.css">'
        code += '\n        <script type="text/javascript" src="../jquery-1.10.2.min.js"></script>'
        code += '\n        <script>'
        code += '\n         $(document).ready(function(){});'
        code += '\n            function showHideNonMappable (elementid){'
        code += '\n                var cssclass = "table#" + elementid + " td.non_mappable";'
        code += '\n                if ($(cssclass).css("display") != "table-cell"){'
        code += '\n                    $(cssclass).css("display", "table-cell");}'
        code += '\n                else {'
        code += '\n                   $(cssclass).css("display", "none");}};'
        code += '\n        </script>'
        if selectNonMappable:
            code += '\n        <script type="text/javascript">'
            code += '\n          var nonMappableCategories = "";'
            code += '\n          var nonMappableArticles = "";'
            code += '\n          function getName(cellThatWasClicked){'
            code += '\n            name = decodeURIComponent(cellThatWasClicked.firstChild)'
            code += '\n            name = name.replace("http://it.wikipedia.org/wiki/","");'
            code += '\n            name = name.replace("_"," ");'
            code += '\n            if (name.substring(0,10) == "Categoria:"){'
            code += '\n                nonMappableCategories += "|" + name.replace("Categoria:","");'
            code += '\n               }'
            code += '\n            else {'
            code += '\n               nonMappableArticles += "|" + name;'
            code += '\n            }'
            code += '\n          document.getElementById("nonMappableCategories").innerHTML = nonMappableCategories;'
            code += '\n          document.getElementById("nonMappableArticles").innerHTML = nonMappableArticles;'
            code += '\n          cellThatWasClicked.style.backgroundColor = "#ffb2b2";'
            code += '\n          }'
            code += '\n        </script>'
        code += '\n        <script type="text/javascript" charset="utf-8">'
        code += '\n          function showHideDiv(elementid){'
        code += '\n            if (document.getElementById(elementid).style.display == "none"){'
        code += '\n                document.getElementById(elementid).style.display = "";'
        code += '\n                }'
        code += '\n            else {'
        code += '\n                  document.getElementById(elementid).style.display = "none";'
        code += '\n                  }'
        code += '\n          }'
        code += '\n        </script>'
        code += '\n        <script>'
        code += '\n          $(document).ready(function() {'
        code += '\n            $(".missing_template_alert").click(function (event) {'
        code += '\n                var msg = "All\'articolo in Wikipedia manca il testo per mostrare le coordinate e la mappa OSM (il template Coord).";'
        code += '\n                msg += "\\n\\nAggiungi in cima alla pagina il seguente codice, completando le coordinate:";'
        code += '\n                msg += "\\n\\n{{coord|lat (gradi decimali)|N|long (gradi decimali)|E|display=title}}";'
        code += '\n                msg += "\\n\\nPuoi copiare le coordinate da JOSM: scaricando l\'oggetto e cliccando nel riquadro in basso a sinistra.";'
        code += '\n                alert(msg);'
        code += '\n                });'
        code += '\n           });'
        code += '\n        </script>'
        code += '\n    </head>'
        code += '\n<body>'
        code += '\n\n<!-- Header -->'
        code += '\n<div id="header">'
        code += '\n    <div id="go_to_home"><a href="../index%s.html">&#8592; Tutte le categorie</a></div>' % suffix
        code += '\n    <div id="update_time">'
        if mode == "themes":
            code += '      Aggiornamento articoli in categoria: %s<br>' % item.updateTime
        code += '\n      Aggiornamento stato mappatura: %s' % self.app.UPDATETIME
        code += '\n    </div>'
        code += '\n</div>'

        code += '\n\n<!-- Content -->'
        code += '\n<div id="content">'

        # Title. Main category or region name
        if mode == "themes":
            progressClass, progressString = self.progress_strings(item, "allMArticles")
            code += '\n<h2><a id="index"></a>%s (%s)</h2>' % (self.wikipedia_link(item), progressString)
        else:
            #mode == "regions"
            img = '<img src="../img/%s/%s.png" class="item_img">' % (mode, item.name.lower())
            code += '\n<h2>%s<a id="index"></a>%s</h2>' % (img, item.name.replace("_", " "))

        if selectNonMappable:
            code += '\n<div id="selectNonMappable">'
            code += '\n  Per contrassegnare alcune categorie ed articoli come "non mappabili": clicca sulle loro celle, copia le stringhe qui sotto ed incollale nel file "./data/wikipedia/non_mappable".<br><br>'
            code += '\n  Categorie:'
            code += '\n  <div id="nonMappableCategories">&nbsp;</div><br>'
            code += '\n  Articoli:'
            code += '\n  <div id="nonMappableArticles">&nbsp;</div>'
            code += '\n</div>'

        # Legenda
        code += '\n\n<!-- Legenda -->'
        code += '\n<p><a href="javascript:showHideDiv(\'legenda\');"><img src="../img/info.png" class="infoImg"> Legenda</a></p>'
        code += '\n<div id="legenda" style="display:none">'
        code += self.legend_table()

        # Index with articles and subcategories of a category
        code += '\n\n<!-- Index -->'
        if mode == "themes" and item.articles != [] and item.titles == []:
            code += '\n<div class="showHideNonMappable"><a href=\'javascript:showHideNonMappable("%s_index");\' title="Visualizza sottocategorie non mappabili">Mostra non mappabili</a></div>' % item.ident
        code += '\n%s' % IndexOfCategories(app, item, mode, pageType="sub").code

        # Articles table
        if item.articles != []:
            code += '\n\n<!-- Articles -->'
            articlesProgressString = ""
            if item.titles != []:
                articlesProgressClass, articlesProgressString = self.progress_strings(item, "articles")
            code += '\n\n<h3><a href=#index>&#8593;</a> <a id="Articles"></a>Articoli %s</h3>' % articlesProgressString
            divId = "%s_articles" % item.ident
            if not item.articlesAreAllMappable:
                code += '\n<div class="showHideNonMappable"><a href=\'javascript:showHideNonMappable("%s");\' title="Visualizza articoli non mappabili">Mostra non mappabili</a></div>' % divId
            code += '\n%s\n' % item.articles_html

        # Subcategories tables
        code += '\n\n<!-- Subcategories -->'
        for subcategory in item.subcategories:
            progressString = ""
            if subcategory.isMappable:
                progressClass, progressString = self.progress_strings(subcategory, "allMArticles")
            if subcategory.allTitlesInOSM != []:
                query = self.overpass_query(subcategory)
                overpassTurboLink = " %s" % self.overpass_turbo_link(query)
            else:
                overpassTurboLink = ""
            code += '\n\n<h3>'
            code += '<a href=#index>&#8593;</a> '
            code += '<a id="%s"></a>' % subcategory.name
            code += '%s <span class=%s>%s</span>' % (self.wikipedia_link(subcategory), progressClass, progressString)
            if not len(subcategory.allTitles) == len(subcategory.allTitlesInOSM):
                code += " %s" % self.add_tags_link(subcategory)
            code += '%s</h3>' % overpassTurboLink
            if not subcategory.isAllMappable:
                code += '\n<div class="showHideNonMappable"><a href="javascript:showHideNonMappable(\'%s\');" title="Mostra anche categorie ed articoli non mappabili">Mostra non mappabili</a></div>' % subcategory.ident
            code += '\n%s\n' % subcategory.html
        code += '\n</div>'
        code += '\n</body>\n</html>'
        self.code = code

    def legend_table(self):
        """Return an html table with the legend
        """
        code = '\n  <table id="legend">'
        code += '\n    <tr><td class="index_done100"></td><td>100% articoli taggati</td></tr>'
        code += '\n    <tr><td class="index_done099"></td><td>99% articoli taggati</td></tr>'
        code += '\n    <tr><td class="index_done075"></td><td>75% articoli taggati</td></tr>'
        code += '\n    <tr><td class="index_done050"></td><td>50% articoli taggati</td></tr>'
        code += '\n    <tr><td class="index_done025"></td><td>25% articoli taggati</td></tr>'
        code += '\n    <tr><td class="index_done0"></td><td>0% articoli taggati</td></tr>'
        code += '\n    <tr><td><img src="../img/add-tags.png"></td><td>Cerca in OSM possibili oggetti corrispondenti agli articoli e taggali facilmente tramite lo strumento <a href="http://wiki.openstreetmap.org/wiki/JOSM/Plugins/RemoteControl/Add-tags" target="_blank">add-tags</a></td></tr>'
        code += '\n    <tr><td><img src="../img/wiwosm.png"></td><td>Vedi l\'oggetto sulla mappa Wikipedia</td></tr>'
        code += '\n    <tr><td><img src="../img/josm.png"></td><td>Scarica l\'oggetto in JOSM</td></tr>'
        code += '\n    <tr><td><img src="../img/osm.png"></td><td>Vedi la pagina OSM dell\'oggetto</td></tr>'
        code += '\n    <tr><td><img src="../img/Overpass-turbo.png"></td><td>Vedi gli oggetti su Overpass Turbo (mappa cliccabile, esporta come immagine...)</td></tr>'
        code += '\n    <tr><td><img src="../img/no_template.png"></td><td>All\'articolo su Wikipedia manca il <a href="https://it.wikipedia.org/wiki/Template%3ACoord" target="_blank">template Coord</a>. Clicca su un\'icona per ulteriori informazioni</td></tr>'
        code += '\n    <tr><td><img src="../img/josm_load_and_zoom.png"></td><td>L\'articolo non è taggato ma Wikipedia ne conosce la posizione. Clicca sull\'icona per aprire JOSM alla posizione conosciuta e trovare più facilmente l\'oggetto da taggare</td></tr>'
        code += '\n    <tr><td><img src="../img/josm_load_and_zoom_blue.png"></td><td>L\'articolo non è taggato ma ne è stata calcolata la posizione approssimata tramite i contenuti dell\'articolo e <a href="https://github.com/SpazioDati/Nuts4Nuts" target="_blank">Nuts4Nuts</a>. Clicca sull\'icona per aprire JOSM alla posizione conosciuta e trovare più facilmente l\'oggetto da taggare</td></tr>'
        code += '\n  </table>'
        code += '\n</div>'
        return code.decode("utf-8")


class ArticlesTable(Helpers):
    def __init__(self, app, item, selectNonMappable):
        """Return an html table with articles of a ctagory
        """
        if item.articles == []:
            self.code = ""
            return

        tableId = ""
        if not item.articlesAreAllMappable:
            tableId = ' id="%s_articles"' % item.ident
        code = '\n<table class="data"%s>' % tableId
        articles = item.articles
        for article in articles:
            cssclass = ""
            colspan = ""
            if not article.isMappable:
                cssclass = ' class="non_mappable"'
                colspan = ' colspan="2"'
            else:
                if article.inOSM:
                    links = self.tagged_article_links(app, article)
                else:
                    links = self.non_tagged_article_links(app, article)
            code += "\n  <tr>"
            onclick = ""
            if selectNonMappable:
                onclick = ' onclick="getName(this);"'
            code += "\n    <td%s%s%s>%s</td>" % (onclick, cssclass, colspan, self.wikipedia_link(article))
            if article.isMappable:
                code += "\n    <td>%s</td>" % links
            code += "\n  </tr>"
        code += "\n</table>"
        self.code = code


class CategoryTable(Helpers):
    def __init__(self, app, category, selectNonMappable):
        """Return an html table with subcategories (and their articles)
           of a category
        """
        self.app = app
        self.selectNonMappable = selectNonMappable
        columnsNumber = self.table_columns_number(category) + 1
        tableId = ""
        if not category.isAllMappable:
            tableId = ' id="%s"' % category.ident
        code = '\n<table class="data"%s>' % tableId
        code += "\n  <tr>"
        code = self.build_table(code, category, columnsNumber)
        code += '\n</table>'
        self.code = code

    def table_columns_number(self, category, i=0):
        if category.subcategories != []:
            columnsNumber = max([self.table_columns_number(subcategory, i + 1) for subcategory in category.subcategories])
        else:
            columnsNumber = i
        return columnsNumber

    def build_table(self, code, category, columnsNumber, level=0):
        """Build table by recursively reading subcategories and articles
           of the category
        """
        articles = category.articles
        subcategories = category.subcategories
        isFirstItem = True
        #articles
        for article in articles:
            colspan = columnsNumber - level
            if not article.isMappable:
                colspan += 1
            if colspan > 1:
                colspan = " colspan=%s" % str(colspan)
            else:
                colspan = ""
            code += self.add_item(article, isFirstItem, colspan, "")
            isFirstItem = False
        #subcategories
        for subcategory in subcategories:
            rowsnumber = len(subcategory.allArticles)
            if rowsnumber > 1:
                rowspan = " rowspan=%s" % rowsnumber
            else:
                rowspan = ""
            code += self.add_item(subcategory, isFirstItem, "", rowspan)
            isFirstItem = False
            code = self.build_table(code, subcategory, columnsNumber, level + 1)
        return code

    def add_item(self, item, isFirstItem, colspan, rowspan):
        """Add a cell to the table
        """
        code = "\n  <tr>" if not isFirstItem else ""
        onclick = ""
        if self.selectNonMappable:
            onclick = ' onclick="getName(this);"'
        cssClasses = []
        if not item.isMappable:
            cssClasses.append("non_mappable")
        if isinstance(item, Category):
            cssClasses.append("category")
        if cssClasses == []:
            cssClass = ""
        else:
            cssClass = ' class="%s"' % " ".join(cssClasses)
        #Category
        if isinstance(item, Category):
            catData = self.wikipedia_link(item)
            if not len(item.allTitles) == len(item.allTitlesInOSM):
                #add a link to WIWOSM tool "add-tags"
                catData += "\n %s" % self.add_tags_link(item)
            if item.allTitlesInOSM != [] and not self.selectNonMappable:
                #add a link to overpass for showing all objects
                query = self.overpass_query(item)
                linkClass = "overpassTurboLink"
                catData += "\n %s" % self.overpass_turbo_link(query, linkClass)
            code += "\n    <td%s%s%s>%s</td>" % (onclick, rowspan, cssClass, catData)
        #Article
        if isinstance(item, Article):
            code += "\n    <td%s%s%s>%s</td>" % (onclick, colspan, cssClass, self.wikipedia_link(item))
            if item.isMappable:
                #add one more cell with article info (links if tagged)
                nowrap = ""
                if item.inOSM:
                    links = self.tagged_article_links(self.app, item)
                else:
                    links = self.non_tagged_article_links(self.app, item)
                if links != "":
                    nowrap = " NOWRAP"
                code += "\n    <td%s>%s</td>" % (nowrap, links)
            code += "\n  </tr>"
        return code


### Index of categories (table) ########################################
class IndexOfCategories(Helpers):
    def __init__(self, app, item, mode, pageType, showProgressHeader=False):
        """Return html code of a table with the list of subcategories
           and their tagging progress.

           This table is used as index in:
           - homepage (pageType == "home"):
                -- one table for each theme
                   mode == "themes", item = Theme
                   subitems = theme.categories
                -- one table for each region
                   mode == "regions", item = Region
                   subitems = region.categories
           - subpages (pageType == "sub"):
                -- one table for the Main category of page
                   mode == "themes", item = main category
                   subitems = category.subcategories
                -- one table for the region
                   mode == "regions", item = Region
                   subitems = region.categories
        """
        #Prepare variables
        if mode == "themes":
            if pageType == "home":
                subcategories = item.categories
            else:
                subcategories = item.subcategories
        else:
            subcategories = item.subcategories
        if mode == "themes" and pageType == "sub" and not item.articlesAreAllMappable:
            tableId = ' id="%s_index"' % item.ident
        else:
            tableId = ""
        code = '  <table class="categoriesIndex"%s>' % tableId
        addWikipediaCoords = app.args.show_link_to_wikipedia_coordinates and self.header_needed(subcategories, "wikipediaCoordsNum")
        addMissingTemplates = app.args.show_missing_templates and self.header_needed(subcategories, "missingTemplatesNum")
        #table headers
        headers = ["", ""]
        if showProgressHeader:
            headers[1] = 'Numero di articoli<br>taggati / totale'
        if pageType == "home":
            imgPath = "./img"
        else:
            imgPath = "../img"
        if addWikipediaCoords:
            headers.append('<img src="%s" title="Articoli non taggati ma di cui si conosce la posizione">' % os.path.join(imgPath, "josm_load_and_zoom.png"))
        if addMissingTemplates:
            headers.append('<img src="%s" title="Articoli taggati ma senza template Coord in Wikipedia">' % os.path.join(imgPath, "no_template.png"))
        code += '\n    <thead>'
        code += '\n    <tr>'
        for header in headers:
            code += '\n      <th>%s</th>' % header
        code += '\n    </tr>'
        code += '\n    </thead>'
        #table body
        code += '\n    <tbody>'
        if pageType == "sub":
            # articles
            # row = articles (link) || progress ||  ||
            if item.articles != []:
                # (name = "Articles")
                colspan = ""
                cssclass = ""
                if item.titles == []:
                    cssclass = ' class="non_mappable"'
                    colspan = 2
                    if app.args.show_link_to_wikipedia_coordinates:
                        colspan += 1
                    if app.args.show_missing_templates:
                        colspan += 1
                    colspan = ' colspan="%d"' % colspan
                code += '\n    <tr>'
                code += '\n      <td%s%s>- <a href="#Articles">Articoli</a></td>' % (cssclass, colspan)
                # progress
                if item.titles != []:
                    progressClass, progressString = self.progress_strings(item, "articles")
                    code += '\n        <td>'
                    code += '\n          <div class="progress">'
                    code += '\n              <span class="percent">%s / %s</span>' % (len(item.titlesInOSM), len(item.titles))
                    code += '\n              <div class="bar index_%s" style="width:%d"></div>' % (progressClass, item.progress["articles"]["num"] * 100)
                    code += '\n          </div>'
                    code += '\n        </td>'
                code += '\n    </tr>'
        # subcategories
        # row = category name (link) || progress || wikipedia coords num || missing wikipedia templates
        for subcategory in subcategories:
            # name
            if subcategory.isMappable:
                cssClass = ""
                colspan = ""
            else:
                cssClass = ' class="non_mappable"'
                colspan = 2
                if app.args.show_link_to_wikipedia_coordinates:
                    colspan += 1
                if app.args.show_missing_templates:
                    colspan += 1
                colspan = ' colspan="%d"' % colspan
            code += '\n    <tr>'
            if pageType == "home":
                if mode == "themes":
                    url = "./subpages/%s.html" % subcategory.name
                else:
                    url = "./subpages/%s.html#%s" % (item.name, subcategory.name)
            else:
                url = "#%s" % subcategory.name
            if pageType == "home":
                title = ' title="Vedi pagina"'
            else:
                title = ""
            code += '\n      <td%s%s>- <a href="%s"%s>%s</a></td>' % (cssClass, colspan, url, title, subcategory.name.replace("_", " "))
            # progress
            if subcategory.isMappable:
                progressClass, progressString = self.progress_strings(subcategory, "allMArticles")
                code += '\n        <td>'
                code += '\n          <div class="progress">'
                code += '\n              <span class="percent">%s / %s</span>' % (len(subcategory.allTitlesInOSM), len(subcategory.allTitles))
                code += '\n              <div class="bar index_%s" style="width:%d"></div>' % (progressClass, subcategory.progress["allMArticles"]["num"] * 100)
                code += '\n          </div>'
                code += '\n        </td>'
                #number of non tagged articles with Wikipedia coordinates
                if addWikipediaCoords:
                    if subcategory.isMappable and subcategory.wikipediaCoordsNum > 0:
                        wikipediaCoordsNum = str(subcategory.wikipediaCoordsNum)
                    else:
                        wikipediaCoordsNum = ""
                    code += '\n      <td>%s</td>' % wikipediaCoordsNum
                #number of articles without Coord template
                if addMissingTemplates:
                    if subcategory.isMappable and subcategory.missingTemplatesNum > 0:
                        missingTemplatesNum = str(subcategory.missingTemplatesNum)
                    else:
                        missingTemplatesNum = ""
                    code += '\n      <td>%s</td>' % missingTemplatesNum
            code += '\n    </tr>'
        code += '\n    </tbody>'
        code += '\n  </table>'
        self.code = code


### ErrorsPage #########################################################
class ErrorsPage(Helpers):
    def __init__(self, app):
        """Errors page
        """
        self.app = app
        code = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" http://www.w3.org/TR/html4/loose.dtd>'
        code += '\n<html>\n  <head>'
        code += '\n    <meta http-equiv="Content-type" content="text/html;charset=UTF-8">'
        code += '\n    <title>Articoli di Wikipedia mappabili in OSM</title>'
        code += '\n    <link rel="stylesheet" type="text/css" href="style.css">'
        code += '\n  </head>'
        code += '\n<body>'
        code += '\n\n<!-- Header -->'
        code += '\n<div id="header">'
        code += '\n  <div id="go_to_home"><a href="./index.html">&#8592; Tutte le categorie</a></div>'
        code += '\n  <div id="update_time">Aggiornamento: %s</div>' % self.app.UPDATETIME
        code += '\n</div>'
        code += '\n    <div id="content">'
        code += '\n    <h2><a id="Tag errati"></a>Errori</h2>'
        code += "\n    <p>Tag privi dell'indicazione della lingua, che si riferiscono ad articoli stranieri inesistenti o che non sembrano articoli Wikipedia.</p>"
        # Errors
        if len(self.app.wrongTags) == 0:
            code += "\n    <p><i>Nessun errore rilevato.</i></p>"
        else:
            code += self.errors_or_warnings_table(self.app.wrongTags)
        code += "<br>"
        # Warnings
        code += '\n    <h2><a></a>Avvertimenti</h2>'
        code += '\n    <p>Pagine di Wikipedia taggate tramite una url o con lingua in maiuscolo.<br>Non sono errori e sono usati da WIWOSM, ma sono sconsigliati dal <a href="http://wiki.openstreetmap.org/wiki/Wikipedia" target="_blank">Wiki</a>.</p>'
        code += self.errors_or_warnings_table(self.app.badTags)
        code += '\n    </div>'
        code += '\n</body>\n</html>'
        self.code = code

    def errors_or_warnings_table(self, tagsDict):
        """Return a table with wrong tags or tags with warnings
        """
        code = '\n    <table class="data">'
        for tag in sorted(tagsDict.keys()):
            osmIds = tagsDict[tag]
            elements, osmIdsLinks = self.osm_ids_string(osmIds)
            query = self.overpass_query(osmIds)
            img = "./img/josm.png"
            josmLink = " %s" % self.josm_link("download", query, img)
            code += '\n      <tr>'
            code += '\n        <td>%s</td>' % tag.encode("utf-8")
            code += '\n        <td>%s</td><td>%s</td>' % (osmIdsLinks, josmLink)
            code += '\n      </tr>'
        code += '\n    </table>'
        return code
