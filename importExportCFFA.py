""" Library to handle export and import of DB data in JSOn format.

Currently only implemented Export functionality

TO DO: Destructive import

"""

import json
import shutil
from cffadb import dbinterface
from bson.json_util import dumps
from datetime import datetime
import logging

# logging config
logger = logging.getLogger("cffaImportExport")
logger.setLevel(logging.DEBUG)
# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatting = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
ch.setFormatter(formatting)
logger.addHandler(ch)


class CFFAImportExport:
    """ Class def for import and export of DB data.

    Attributes
    ----------

    dbconnection : dbinterface.FootballDB
        CFFA do connection object with active connection

    exportDirectory : str
        Location of where to temporarily export data so that a zip archive can be built from the export from each
        db collection
        """

    dbconnection = None
    exportDirectory = "NotSet"

    def __init__(self, dbconnection, exportDirectory):
        """ Initializer for this class. These are mandatory.

        Parameters
        ----------
        dbconnection : dbinterface.FootballDB
            CFFA do connection object with active connection

        exportDirectory : str
            Location of where to temporarily export data so that a zip archive can be built from the export from each
            db collection

        """

    def exportarchive(self):
        """ Execute export by extracting all data and output each collection is json format. Then zip together. Web
        server code (outside this scope) would then send the file to the user

        """

        # use dbconnection to get each collection in turn and export into a json file in ExportImport

        collectionList = []
        collectionList.append(("payments", self.dbconnection.getAllTransactions()))
        collectionList.append(("games", self.dbconnection.getAllGames()))  # tick
        collectionList.append(("adjustments", self.dbconnection.getAllAdjustments()))  # tick
        collectionList.append(("teamSummary", self.dbconnection.getFullSummary()))  # tick
        collectionList.append(("teamPlayers", self.dbconnection.getTeamPlayers()))    # tick
        collectionList.append(("teamSettings", self.dbconnection.getTeamSettings())) # tick

        fileList = [ 'payments', 'games', 'adjustments', 'teamSummary', 'teamPlayers', 'teamSettings' ]

        for collection in collectionList:
            filename = self.exportDirectory + collection[0] + ".json"
            logger.info("Exporting ", filename)
            with open(filename, 'w') as exportFile:
                i=0
                exportFile.write('[')
                for document in collection[1]:
                    document["_id"] = i
                    exportFile.write(dumps(document))
                    exportFile.write(',')
                    i+=1
                exportFile.write(']')
            exportFile.close()
            logger.info ("Exported ", collection[0])

        ctime=datetime.now()
        archiveExportFile=self.exportDirectory + "cffa_export" + str(ctime.day) + "-" + str(ctime.month) + "-" + str(ctime.year)
        shutil.make_archive(archiveExportFile, 'zip', self.exportDirectory)

        archiveExportFile = archiveExportFile + ".zip"
        return(archiveExportFile)
