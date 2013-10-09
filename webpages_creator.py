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

"""Crate webpages with the lists of Wikipedia categories and articles
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
        
    def wikipediaLink(self, item):
        text = item.name.replace("_", " ")
        title = "Vedi %s: %s" % (item.typ.lower(), text.replace("\"", "&quot;"))
        cssClass = ' class="wikipedia_link"'
        link = self.url_to_link(item.wikipediaUrl, title, text, None, cssClass)
        return link

    def overpass_osm_ids_string(self, article, osmids=None):
        elementType = {"n" : "node", "w" : "way", "r" : "relation"}
        osmIdsString = ""
        if osmids is None:
            osmIds = article.osmIds
        else:
            osmIds = osmids
        for osmId in osmIds:
            osmIdsString += '%s(%s);' % (elementType[osmId[0]], osmId[1:])
        return osmIdsString
        
    def overpass_query(self, item):
        if isinstance(item, Article):
            elementsString = self.overpass_osm_ids_string(item)
        elif isinstance(item, Category):
            elementsString = ""
            for article in item.allArticlesInOSM:
                elementsString += self.overpass_osm_ids_string(article)
        else:
            #wrongTags and badTags are not articles nor categories
            elementsString = self.overpass_osm_ids_string(None, item)
        query = '('
        query += elementsString
        query += ');'
        query += '(._;>;);'
        query += 'out meta qt;'
        return query
        
    def josm_link(self, query, img):
        url = "http://localhost:8111/import?url=http://overpass.osm.rambler.ru/cgi/interpreter?data=" + query
        title = "Scarica in JOSM"
        link = self.url_to_link(url, title, None, img)
        return link
        
    def overpass_turbo_link(self, query, cssClass=""):
        url = 'http://overpass-turbo.eu/index.html?Q=%s&R' % urllib.quote_plus(query)
        title = "Visualizza come mappa cliccabile, immagine... (Overpass Turbo)"
        img = "../img/Overpass-turbo.png"
        link = self.url_to_link(url, title, None, img, cssClass)
        return link
    
    def osm_ids_string(self, item):
        elementType = {"n" : "node", "w" : "way", "r" : "relation"}
        elements = {"nodes" : [], "ways" :[], "relations" : []}
        if isinstance(item, Article):
            osmIds = item.osmIds
        else:
            #item = wrongTags or badTags
            osmIds = item
        for osmId in osmIds:
            url = "http://www.openstreetmap.org/browse/%s/%s" % (elementType[osmId[0]], osmId[1:])
            link = self.url_to_link(url, "%s" % "Vedi pagina OSM", osmId[1:])
            elements[elementType[osmId[0]] + "s"].append(link)
        osmIdsString = ""
        for elementsType, elementsList in elements.iteritems():
            if len(elementsList) > 0:
                if osmIdsString != "":
                    osmIdsString += "<br>"
                if isinstance(item, Article):
                    imgPath = "../img/"
                else:
                    imgPath = "./img/"
                img = '<img title="%s" src=%s%s.png>' % (elementsType, imgPath, elementsType)
                osmIdsString += "%s %s" % (img, ", ".join(elementsList))
        if isinstance(item, Article):
            #return the string inside a div
            osmDivId = item.ident
            osmIdsString = '<div id="%s" style="display:none"><br>%s</div>' % (osmDivId, osmIdsString)
        return osmIdsString
        
    def url_to_link(self, url, title, text, img=None, cssClass="", target=""):
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
        
    def article_links(self, app, article):
        """Create links from OSM objects to various services
        """
        #WIWOSM link
        wiwosmUrl = "http://toolserver.org/~kolossos/openlayers/kml-on-ol-json3.php?lang=%s&title=%s" % (app.WIKIPEDIALANG, article.name)
        wiwosmTitle = "Vedi mappa Wikipedia (WIWOSM)"
        wiwosmImg = "../img/wiwosm.png"
        wiwosmLink = self.url_to_link(wiwosmUrl, wiwosmTitle, None, wiwosmImg)
        
        #Show div with OSM ids of the article
        osmUrl = "javascript:showHideDiv(\'%s\');" % article.ident
        osmLinkTitle = "Vedi pagina OSM"
        osmLinkImg = "../img/osm.png"
        osmLink = self.url_to_link(osmUrl, osmLinkTitle, None, osmLinkImg, "", None)
        osmIdsDiv = self.osm_ids_string(article)
    
        query = self.overpass_query(article)
        
        #JOSM remote control link
        img = "../img/josm.png"
        josmLink = self.josm_link(query, img)
        
        #Overpass Turbo link
        overpassTurboLink = self.overpass_turbo_link(query)
        
        code = '\n      %s ' % wiwosmLink
        code += '\n      %s ' % osmLink
        code += '\n      %s ' % josmLink
        code += '\n      %s' % overpassTurboLink
        code += '\n      %s' % osmIdsDiv
        return code

    
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
                category.articles_html = Articles_table(app, category, selectNonMappable).code
                for subcategory in category.subcategories:
                    subcategory.html = Category_table(app, subcategory, selectNonMappable).code
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
        code += '\n    <p><a id="description" href="javascript:showHideDiv(\'info\');">Informazioni e conteggi</a> | <a href="errors.html" title="Visualizza tag sospetti">Tag sospetti</a></p>'
        #Info
        code += '\n    <div id="info" style="display:none">'
        code += self.stats_table()
        code += '\n      <h2></h2>'
        code += '\n      <ul>'
        code += '\n        <li>Gli oggetti taggati compaiono in Wikipedia <a href="http://toolserver.org/~kolossos/openlayers/kml-on-ol.php?lang=it&uselang=de&params=41.89_N_12.491944444444_E_region%3AIT_type%3Alandmark&title=Colosseom&zoom=18&lat=41.89&lon=12.49284&layers=B00000FTTTF">su una mappa</a> (progetto <a href="http://wiki.openstreetmap.org/wiki/WIWOSM" target="_blank">WIWOSM</a>).</li>'
        code += '\n        <li>La presenza di tag wikipedia vengono migliora i risultati delle ricerche eseguite su www.openstreetmap.org (Nominatim).</li>'
        code += '\n      </ul>'
        code += '\n      <h2>Come</h2>'
        code += '\n      <ul>'
        code += '\n        <li>Aggiungere all\'oggetto in OSM il tag "wikipedia=it:Titolo articolo", lasciando gli spazi tra le parole.<br>Basta una sola lingua, se l\'articolo è già taggato in una lingua straniera non occorre aggiungere qulla italiana (vedi <a href="http://wiki.openstreetmap.org/wiki/Wikipedia" target="_blank"> eccezioni</a> sul Wiki di OSM).</li>'
        code += '\n        <li>Il <a href="http://josm.openstreetmap.de/wiki/Help/Plugin/Wikipedia" target="_blank">plugin Wikipedia</a> per <a href="http://wiki.openstreetmap.org/wiki/IT:JOSM" target="_blank">JOSM</a> facilita il tagging di articoli in una determinata zona o categoria.</li>'
        code += '\n      </ul>'
        code += '\n      <h2>Difetti nelle liste</h2>'
        code += '\n      <ul>'
        code += '\n        <li> Articoli o categorie <i>non mappabili</i>, ad es. "es. Dipinti nel Museo Tal Dei Tali", possono essere rimossi dalla pagina, se segnalate (vedi mail).</li>'
        code += '\n        <li> Può accadere che in una sottocategoria ricadano articoli non riguardanti il tema di partenza. Se questi sono mappabili vengono comunque mostrati in tabella.</li>'
        code += '\n        <li> Articoli o sottocategorie appartenenti a più categorie possono ripetersi più volte in una stessa pagina (i conteggi ne tengono conto).</li>'
        code += '\n      </ul>'
        code += '\n      <h2>Script per generare le pagine</h2>'
        code += '\n      <p>Codice: <a href="https://github.com/simone-f/wikipedia-tags-in-osm" target="_blank">wikipedia-tags-in-osm %s</a> (GPLv3)<br>Mail: groppo8@gmail.com</p>' % self.app.version
        code += '\n      <p><br>Attribuzioni:</p>'
        code += '\n      <p>Icone dei temi: <a href="https://github.com/mapbox/maki" target="_blank" target="_blank">Maki</a> (BSD)<br>'
        code += '\n      Stemmi regionali: <a href="http://www.araldicacivica.it" target="_blank">www.araldicacivica.it</a> (<a href="http://creativecommons.org/licenses/by-nc-nd/3.0/it/">CC BY-NC-ND 3.0</a>)<br>'
        code += '\n      Icone di nodi, way, relazioni ed Overpass Turbo da <a href="http://wiki.openstreetmap.org/">Wiki OSM</a>.</p>'
        code += '\n    </div>'
        #Tabs: themes|regions|errors
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
        """Return html code of a table with the numebr of tegged articles
        """
        red = "#cc0000"
        green = "#00cc7a"
        strings = {"to do"  : "Da mappare",
                   "mapped" : "Mappati",
                   "total"  : "Totali",
                   "errors" : "Errori"}
        code = '\n      <table id="stats">'
        code += '\n        <tr>'
        code += '\n          <th>Articoli</th>'
        for date in self.app.dates:
            code += '\n          <th>%s</th>' % date
        code += '\n        </tr>'
        for status in ("mapped", "to do", "total"):
            #first cell
            if status == "total":
                code += '\n        <tr>\n          <th>Tag</th>'
                for d in range(len(self.app.days)):
                    code += '\n          <th></th>'
                code += '\n        </tr>'
            code += '\n        <tr>'
            code += '\n          <td>%s</td>' % strings[status]
            #data
            for index, day in enumerate(self.app.days):
                value = int(day[status])
                differenceStr = ""
                if index > 0:#= len(self.app.days) - 1:
                    previousvalue = int(self.app.days[index-1][status])
                    difference = int(value) - previousvalue
                    if difference != 0:
                        differenceStr = str(difference)
                        if difference > 0:
                            if status == "to do":
                                color = red
                            else:
                                color = green
                            differenceStr = "+%s" % differenceStr
                        elif difference < 0:
                            if status == "to do":
                                color = green
                            else:
                                color = red
                        differenceStr = ' <span style = "color: %s">(%s)</span>' % (color, differenceStr)
                code += '\n          <td>%s%s</td>' % (value, differenceStr)
            code += '\n        </tr>'
        code += '\n      </table>'
        return code
        
    def index(self, items, mode):
        """Return html code of a table with themes or regions, to be used
           as index in the homepage
        """
        code = '\n    <table id="home_index">'
        code += '\n      <tr>'
        i = 0
        for n, item in enumerate(items):
            icon = ""
            iconFile = "./img/%s/%s.png" % (mode, item.name.lower())
            if os.path.isfile(os.path.join(self.app.HTMLDIR, iconFile)):
                icon = '<img src=%s>' % iconFile
            code += '\n        <td><a href="#%s">%s%s</a></td>' % (item.name, icon, item.name.replace("_", " "))
            i += 1
            if i == 5:
                code += '\n      </tr>'
                if n != len(items) - 1:
                    code += '\n      <tr>'
                i = 0
        code += '\n      </tr>'
        code += '\n    </table>'
        return code
        
    def themes_and_regions_tabs(self, mode):
        """Return html code of homepage tabs: themes and regions
        """
        #Index table with icons of themes or regions
        if mode == "themes":
            items = self.app.themes
        else:
            items = self.app.regions
        code = self.index(items, mode)
        #Categories in each theme or region
        for item in items:
            linkTop = '<a href=#top>&#8593;</a>'
            itemImg = '<img src="./img/%s/%s.png" class="item_img">' % (mode, item.name.lower())
            itemTitle = '%s%s' % (itemImg, item.name.replace("_", " "))
            if mode == "regions":
                itemTitle = '<a href="./subpages/%s.html">%s</a>' % (item.name, itemTitle)
            code += '\n\n    <h3>%s<a id="%s"></a>%s</h3>' % (linkTop, item.name, itemTitle)
            
            #categories per theme or per region and number of
            #tagged/not tagged articles
            code += '\n    <table class="categoriesIndex">'
            if mode == "themes":
                subitems = item.categories
            else:
                subitems = item.subcategories
            for category in subitems:
                progressClass, progressString = self.progress_strings(category, "allMArticles")
                code += '\n      <tr>'
                if mode == "themes":
                    url = "./subpages/%s.html" % category.name
                else:
                    url = "./subpages/%s.html#%s" % (item.name, category.name)
                code += '\n        <td>- <a href="%s" title="Vedi pagina">%s</a></td>' % (url, category.name.replace("_", " "))
                code += '\n        <td class="%s">%s</td>' % (progressClass, len(category.allArticlesInOSM))
                code += '\n        <td class="%s">%s</td>' % (progressClass, len(category.allMArticles))
                code += '\n      </tr>'
            code += '\n    </table>'
        return code
        
        
### Subpage ###############################################################
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
            code += '\n<h2><a id="index"></a>%s (%s)</h2>' % (self.wikipediaLink(item), progressString)
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
            
        # Index with articles and subcategories of a category
        code += '\n\n<!-- Index -->'
        if mode == "themes" and item.articles != [] and item.mArticles == []:
            code += '\n<div class="showHideNonMappable"><a href=\'javascript:showHideNonMappable("%s_index");\' title="Visualizza sottocategorie non mappabili">Mostra non mappabili</a></div>' % item.ident
        code += '\n%s' % Subpage_index_table(item, mode).code
        
        # Legenda
        code += '\n\n<!-- Legenda -->'
        code += '\n<p><a href="javascript:showHideDiv(\'legenda\');">Legenda</a></p>'
        code += '\n<div id="legenda" style="display:none">'
        code += '\n  <table id="legend">'
        code += '\n    <tr><td class="done100"></td><td>100% articoli taggati</td></tr>'
        code += '\n    <tr><td class="done099"></td><td>99% articoli taggati</td></tr>'
        code += '\n    <tr><td class="done075"></td><td>75% articoli taggati</td></tr>'
        code += '\n    <tr><td class="done050"></td><td>50% articoli taggati</td></tr>'
        code += '\n    <tr><td class="done025"></td><td>25% articoli taggati</td></tr>'
        code += '\n    <tr><td class="done0"></td><td>0% articoli taggati</td></tr>'
        code += '\n    <tr><td><img src="../img/wiwosm.png"></td><td>Vedi l\'oggetto sulla mappa Wikipedia</td></tr>'
        code += '\n    <tr><td><img src="../img/josm.png"></td><td>Scarica l\'oggetto in JOSM</td></tr>'
        code += '\n    <tr><td><img src="../img/osm.png"></td><td>Vedi la pagina OSM dell\'oggetto</td></tr>'
        code += '\n    <tr><td><img src="../img/Overpass-turbo.png"></td><td>Vedi gli oggetti su Overpass Turbo (mappa cliccabile, esporta come immagine...)</td></tr>'
        code += '\n  </table>'
        code += '\n</div>'
        
        # Articles table
        if item.articles != []:
            code += '\n\n<!-- Articles -->'
            articlesProgressString = ""
            if item.mArticles != []:
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
            if subcategory.allArticlesInOSM != []:
                query = self.overpass_query(subcategory)
                overpassTurboLink = " %s" % self.overpass_turbo_link(query)
            else:
                overpassTurboLink = ""
            code += '\n\n<h3>'
            code += '<a href=#index>&#8593;</a> '
            code += '<a id="%s"></a>' % subcategory.name
            code += '%s %s' % (self.wikipediaLink(subcategory), progressString)
            code += ' <span class=%s>&nbsp;&nbsp;</span>' % progressClass
            code += '%s</h3>' % overpassTurboLink
            if not subcategory.isAllMappable:
                code += '\n<div class="showHideNonMappable"><a href="javascript:showHideNonMappable(\'%s\');" title="Mostra anche categorie ed articoli non mappabili">Mostra non mappabili</a></div>' % subcategory.ident
            code += '\n%s\n' % subcategory.html
        code += '\n</div>'
        code += '\n</body>\n</html>'
        self.code = code
        
        
### Categories and regions tables ######################################
class Subpage_index_table(Helpers):
    def __init__(self, item, mode):
        """Return html code for the index of a subpage, hence
           regarding a mainCategory (if by theme) or a region (if by regions)
        """
        tableId = ""
        if mode != "regions" and not item.articlesAreAllMappable:
            tableId = ' id="%s_index"' % item.ident
        code = '  <table class="categoriesIndex"%s>' % tableId
        # articles index
        if item.articles != []:
            colspan = ""
            cssclass = ""
            if item.mArticles == []:
                cssclass = ' class="non_mappable"'
                colspan = ' colspan="3"'
            code += '\n    <tr>'
            code += '\n      <td%s%s>- <a href="#Articles">Articoli</a></td>' % (cssclass, colspan)
            # progress
            if item.mArticles != []:
                progressClass, progressString = self.progress_strings(item, "articles")
                code += '\n      <td class="%s">%s</td>' % (progressClass, len(item.articlesInOSM))
                code += '\n      <td class="%s">%s</td>' % (progressClass, len(item.articles))
            code += '\n    </tr>'
        # subcategories index
        for subcategory in item.subcategories:
            cssclass = ""
            colspan = ""
            if not subcategory.isMappable:
                cssclass = ' class="non_mappable"'
                colspan = ' colspan = "3"'
            code += '\n    <tr>'
            code += '\n      <td%s%s>- <a href="#%s">%s</a></td>' % (cssclass, colspan, subcategory.name, subcategory.name.replace("_", " "))
            # progress
            if subcategory.isMappable:
                progressClass, progressString = self.progress_strings(subcategory, "allMArticles")
                code += '\n      <td class="%s">%s</td>' % (progressClass, len(subcategory.allArticlesInOSM))
                code += '\n      <td class="%s">%s</td>' % (progressClass, len(subcategory.allMArticles))
            code += '\n    </tr>'
        code += '\n  </table>'
        self.code = code

class Articles_table(Helpers):
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
                    links = self.article_links(app, article)
                else:
                    links = ""
            code += "\n  <tr>"
            onclick = ""
            if selectNonMappable:
                onclick = ' onclick="getName(this);"'
            code += "\n    <td%s%s%s>%s</td>" % (onclick, cssclass, colspan, self.wikipediaLink(article))
            if article.isMappable:
                code += "\n    <td>%s</td>" % links
            code += "\n  </tr>"
        code += "\n</table>"
        self.code = code
        
class Category_table(Helpers):
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
            code += self.addItem(article, isFirstItem, colspan, "")
            isFirstItem = False
        #subcategories
        for subcategory in subcategories:
            rowsnumber = subcategory.subItemsNumber
            if rowsnumber > 1:
                rowspan = " rowspan=%s" % rowsnumber
            else:
                rowspan = ""
            code += self.addItem(subcategory, isFirstItem, "", rowspan)
            isFirstItem = False
            code = self.build_table(code, subcategory, columnsNumber, level+1)
        return code

    def addItem(self, item, isFirstItem, colspan, rowspan):
        """Add a cell to the table
        """
        code = "\n  <tr>" if not isFirstItem else ""
        cssclass = ' class="non_mappable"' if not item.isMappable else ""
        onclick = ""
        if self.selectNonMappable:
            onclick = ' onclick="getName(this);"'
        if isinstance(item, Category):
            if item.allArticlesInOSM != [] and not self.selectNonMappable:
                #use a div to add an overpass link
                query = self.overpass_query(item)
                addClass = ' class="overpassTurboLink"'
                catDiv = "<div class=categoryLink><span>%s</span>" % self.wikipediaLink(item)
                catDiv += " %s</div>" % self.overpass_turbo_link(query, addClass)
            else:
                catDiv = self.wikipediaLink(item)
            code += "\n    <td%s%s%s>%s</td>" % (onclick, rowspan, cssclass, catDiv)
        if isinstance(item, Article):
            code += "\n    <td%s%s%s>%s</td>" % (onclick, colspan, cssclass, self.wikipediaLink(item))
            if item.isMappable:
                #add cell with article info (links if tagged)
                links = ""
                nowrap = ""
                if item.inOSM:
                    links = self.article_links(self.app, item)
                if links != "":
                    nowrap = " NOWRAP"
                code += "\n    <td%s>%s</td>" % (nowrap, links)
            code += "\n  </tr>"
        return code
        

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
            osmIdsLinks = self.osm_ids_string(osmIds)
            query = self.overpass_query(osmIds)
            img = "./img/josm.png"
            josmLink = " %s" % self.josm_link(query, img)
            code += '\n      <tr>'
            code += '\n        <td>%s</td>' % tag.encode("utf-8")
            code += '\n        <td>%s</td><td>%s</td>' % (osmIdsLinks, josmLink)
            code += '\n      </tr>'
        code += '\n    </table>'
        return code
