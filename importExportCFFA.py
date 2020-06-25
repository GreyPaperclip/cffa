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

    dbconnection = None
    exportDirectory = "NotSet"

    def __init__(self, dbconnection, exportDirectory):
        self.dbconnection = dbconnection
        self.exportDirectory = exportDirectory

    def exportarchive(self):
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
