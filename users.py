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

"""Count the number of tags add by each user since the previous day
"""

import os
import csv


### Mappers ############################################################
class Users:
    def __init__(self, app):
        """Find which users have added Wikipedia tags from the previous
           run, and count the tags
        """
        print "\n- Find which users have added Wikipedia tags from the previous \
run, and count the tags"
        todayTagsPerUser = {}
        tags = list(set(app.tagsInOSM))
        #Read old tags lists
        dates, tagsLists = self.read_old_tags_lists()
        if dates is None or dates == [app.todayDate]:
            #We do not have the tags of a previous day
            dates = [app.todayDate]
            tagsLists = [tags]
            self.print_users_warning()
        else:
            if (len(dates) == 1 and dates[-1] != app.todayDate) or \
               (len(dates) == 2 and dates[-1] == app.todayDate):
                #csv == yesterday or csv == yesterday || today
                oldTags = tagsLists[0]
                oldDate = dates[0]
            elif len(dates) == 2 and dates[-1] != app.todayDate:
                #csv == before yesterday || yesterday
                oldTags = tagsLists[1]
                oldDate = dates[1]
            #Tags per user
            todayTagsPerUser = self.count_tags_per_user(app, oldTags, tags)
            self.save_tags_per_user(app, todayTagsPerUser)
            dates = [oldDate, app.todayDate]
            tagsLists = [oldTags, tags]
        #Save updated tags list
        self.save_tags_list(dates, tagsLists)

        self.users = todayTagsPerUser

    def print_users_warning(self):
        print "  To show the mappers list, it is necessary to have \
the tags lists of at least two days. Untill then, \
the mappers list will not be shown on the web pages. The tags have been saved \
to `data/OSM/tags.csv`."

    def read_old_tags_per_user(self, today):
        """Read the total number of tags added by each user
        """
        tagsPerUser = {}
        usersFileName = os.path.join("data", "OSM", "users.csv")
        if not os.path.isfile(usersFileName):
            return tagsPerUser
        inFile = open(usersFileName, "rb")
        reader = csv.reader(inFile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
        for i, row in enumerate(reader):
            user = row[0].decode("utf-8")
            totTagsNumber = int(row[1])
            tagsNumber = int(row[2])
            fileDate = row[3]
            tagsPerUser[user] = {"tot": totTagsNumber,
                                 "today": tagsNumber,
                                 "today date": fileDate}
        inFile.close()
        return tagsPerUser

    def read_old_tags_lists(self):
        tagsFileName = os.path.join("data", "OSM", "tags.csv")
        if not os.path.isfile(tagsFileName):
            return None, None
        inFile = open(tagsFileName, "rb")
        reader = csv.reader(inFile, delimiter='\t',
                            quotechar='"',
                            quoting=csv.QUOTE_ALL)
        for i, row in enumerate(reader):
            if i == 0:
                dates = row
                tagsLists = [[] for d in dates]
                continue
            for dayNum in range(len(dates)):
                tagsLists[dayNum].append(row[dayNum].decode("utf-8"))
        inFile.close()
        return dates, tagsLists

    def count_tags_per_user(self, app, oldTags, updatedTags):
        """Read the number of tags added by each user since the previous day
        """
        users = {}
        newTags = {}
        for tag in updatedTags:
            if tag not in oldTags:
                tagUsers = app.tagsData[(tag.split("=")[0], "=".join(tag.split("=")[1:]))]["users"]
                newTags[tag] = tagUsers
                for user in tagUsers:
                    if user not in users:
                        users[user] = 0
                    users[user] += 1
        self.print_new_tags_info(newTags, users)
        return users

    def print_new_tags_info(self, newTags, users):
        """Print the new tags against those of the previous day,
           the names of mappers and the number of tags added by each one
        """
        print "\n  New tags || Mappers"
        for tag, usersList in newTags.iteritems():
            print tag.encode("utf-8"), "||", [u.encode("utf-8") for u in usersList]
        print len(newTags)
        print "\n  Mappers || Tags numbers"
        for user, tagsNum in users.iteritems():
            print user.encode("utf-8"), "||", tagsNum
        print len(users)

    def save_tags_per_user(self, app, todayTagsPerUser):
        """Save to CSV file the total number of tags added by each user
        """
        tagsPerUser = self.read_old_tags_per_user(app.todayDate)
        #old users
        for user, userData in tagsPerUser.iteritems():
            if userData["today date"] != app.todayDate:
                userData["tot"] += userData["today"]
            if user in todayTagsPerUser:
                userData["today"] = todayTagsPerUser[user]
            else:
                userData["today"] = 0
            userData["today date"] = app.todayDate
        #new users
        for user, todayTagsNum in todayTagsPerUser.iteritems():
            if user not in tagsPerUser:
                tagsPerUser[user] = {"tot": 0,
                                     "today": todayTagsNum,
                                     "today date": app.todayDate}

        usersFileName = os.path.join("data", "OSM", "users.csv")
        outFile = open(usersFileName, 'wb')
        writer = csv.writer(outFile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
        for user, userData in tagsPerUser.iteritems():
            writer.writerow([user.encode("utf-8"),
                             userData["tot"],
                             userData["today"],
                             userData["today date"]])
        outFile.close()

    def save_tags_list(self, dates, tagsLists):
        """Save the the list of tags to CSV file
        """
        tagsFileName = os.path.join("data", "OSM", "tags.csv")
        rowsNum = max([len(tagsList) for tagsList in tagsLists])
        rows = []
        for i in range(rowsNum):
            row = []
            for tagsList in tagsLists:
                if i > len(tagsList) - 1:
                    row.append("")
                else:
                    row.append(tagsList[i].encode("utf-8"))
            rows.append(row)
        outFile = open(tagsFileName, 'wb')
        writer = csv.writer(outFile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(dates + [])
        for row in rows:
            writer.writerow(row)
        outFile.close()
