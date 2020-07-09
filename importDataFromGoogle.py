""" Library to provide the ability to connect and download worksheet data from a specified google sheet.

The google sheet must have an API user added and json connector key file available so that access can be securely
made. This is done via the google sheets management screen online at https://console.developers.google.com/apis/
by adding a Service Account user and enabling the Google Sheets API. Once the Service Account is created, select it and
then add/generate a key. This will provide a json file which is used in CFFA. Ensure the service account username is
added to the list of shared users in your google sheet.

Requires the cffadb module to execute. In tern this uses the gsheet package.

"""

from cffadb import googleImport
from cffadb import dbinterface
import logging
logger = logging.getLogger("googleimporter")
logger.setLevel(logging.DEBUG)
# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatting = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
ch.setFormatter(formatting)
logger.addHandler(ch)

class GoogleImporter:

    """ Class def for google importer - contaisn all the required data to successfully access and download football data.

    Attributes
    ----------

    db : footballDB
        CFFA db class for the underlying mongoDB. Must be initialised and connected for population to work

    keyfilename : str
        Filename for the json key file from google. This is stored in the webserver under uploads and is not accessible
        publically.

    gsheetName : str
        Name of google sheet

    transactionsWorksheet : str
        Worksheet name in your google sheet with transaction data

    gameWorksheet: str
        Worksheet name in your google sheet with game data

    summaryWorksheet: str
        Worksheet name in your google sheet with summary data showing things such as balances, games played etc

    summaryRowStart: int
        The summary sheet might not summarise from the first tow. Specify from which row to import

    summaryRowEnd: int
        The summary sheet might have lots of other data. States which row to stop importing from.

    """

    def __init__(self, databaseObj, keyfile, gsheetName, transactionsWorksheet, gameWorksheet, summaryWorksheet, summaryRowStart, summaryRowEnd):
        """ Configure the object with the necessary data to connect and import from a google sheet.

        Parameters
        ----------

    db : footballDB
        CFFA db class for the underlying mongoDB. Must be initialised and connected for population to work

    keyfilename : str
        Filename for the json key file from google. This is stored in the webserver under uploads and is not accessible
        publically.

    gsheetName : str
        Name of google sheet

    transactionsWorksheet : str
        Worksheet name in your google sheet with transaction data

    gameWorksheet: str
        Worksheet name in your google sheet with game data

    summaryWorksheet: str
        Worksheet name in your google sheet with summary data showing things such as balances, games played etc

    summaryRowStart: int
        The summary sheet might not summarise from the first tow. Specify from which row to import

    summaryRowEnd: int
        The summary sheet might have lots of other data. States which row to stop importing from.

        """

        self.db = databaseObj
        self.keyfilename = keyfile
        self.gsheetName = gsheetName
        self.transactionsWorksheet = transactionsWorksheet
        self.gameWorksheet = gameWorksheet
        self.summaryWorksheet = summaryWorksheet
        self.summaryRowStart = summaryRowStart
        self.summaryRowEnd = summaryRowEnd

    def downloadData(self):
        """ Calls a series of methods on both the googleImport and footballDB objects to obtain and populate data. Note
        that the logic reads each worksheet in full and populates documents/collections accordingly.

        Once data is populated, calcPopulateTeamSummary is called to calculate the summary. The DB is ready to be used.
        The logic will remove all prior collections prior to population so this is replace not append logic.

        TO DO: error handling!

        Parameters
        ----------

        None

        Returns
        -------

            :Str
            String message on status so that CFFA can banner the message to the end user.

        """

        google = googleImport.Googlesheet(self.keyfilename,
                                          self.gsheetName,
                                          self.transactionsWorksheet,
                                          self.gameWorksheet,
                                          self.summaryWorksheet)

        mainPlayers = google.derivePlayers(self.summaryRowStart,
                                           self.summaryRowEnd)

        self.db.populatePayments(google.transactions)
        google.calcPlayerListPerGame()
        self.db.populateGames(google.allgames)
        adjustments =  google.calcPlayerAdjustments(self.summaryRowStart,self.summaryRowEnd)
        self.db.populateAdjustments(adjustments)
        self.db.calcPopulateTeamSummary(mainPlayers)

        playerDetails = []
        for player in mainPlayers:
            playerDict = dict(playerName=player,
                              retiree=self.db.shouldPlayerBeRetired(player),
                              comment="Imported from GoogleSheet")
            playerDetails.append(playerDict)
        self.db.populateTeamPlayers(playerDetails)

        return "Imported data from google sheet:" + self.gsheetName



