""" Library to handle export and import of DB data in JSOn format.

Currently only implemented Export functionality

TO DO: Destructive import

"""

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

    db_connection : dbinterface.FootballDB
        CFFA do connection object with active connection

    export_directory : str
        Location of where to temporarily export data so that a zip archive can be built from the export from each
        db collection
        """

    db_connection = None
    export_directory = "NotSet"

    def __init__(self, db_connection, export_directory):
        """ Initializer for this class. These are mandatory.

        Parameters
        ----------
        db_connection : dbinterface.FootballDB
            CFFA do connection object with active connection

        export_directory : str
            Location of where to temporarily export data so that a zip archive can be built from the export from each
            db collection

        """
        self.db_connection = db_connection
        self.export_directory = export_directory

    def exportarchive(self):
        """ Execute export by extracting all data and output each collection is json format. Then zip together. Web
        server code (outside this scope) would then send the file to the user

        """

        # use dbconnection to get each collection in turn and export into a json file in ExportImport

        collection_list = []
        collection_list.append(("payments", self.db_connection.get_all_transactions()))
        collection_list.append(("games", self.db_connection.get_all_games()))  # tick
        collection_list.append(("adjustments", self.db_connection.get_all_adjustments()))  # tick
        collection_list.append(("teamSummary", self.db_connection.get_full_summary()))  # tick
        collection_list.append(("teamPlayers", self.db_connection.get_team_players()))  # tick
        collection_list.append(("teamSettings", self.db_connection.get_team_settings()))  # tick

        for collection in collection_list:
            filename = self.export_directory + collection[0] + ".json"
            logger.info("Exporting ", filename)
            with open(filename, 'w') as export_file:
                i = 0
                export_file.write('[')
                for document in collection[1]:
                    document["_id"] = i
                    export_file.write(dumps(document))
                    export_file.write(',')
                    i += 1
                export_file.write(']')
            export_file.close()
            logger.info("Exported ", collection[0])

        ctime = datetime.now()
        archive_export_file = self.export_directory + \
                              "cffa_export" + \
                              str(ctime.day) + "-" + \
                              str(ctime.month) + "-" + \
                              str(ctime.year)
        shutil.make_archive(archive_export_file, 'zip', self.export_directory)

        archive_export_file = archive_export_file + ".zip"
        return archive_export_file
