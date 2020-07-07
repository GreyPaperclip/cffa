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

    def __init__(self, databaseObj, keyfile, gsheetName, transactionsWorksheet, gameWorksheet, summaryWorksheet, summaryRowStart, summaryRowEnd):
        self.db = databaseObj
        self.keyfilename = keyfile
        self.gsheetName = gsheetName
        self.transactionsWorksheet = transactionsWorksheet
        self.gameWorksheet = gameWorksheet
        self.summaryWorksheet = summaryWorksheet
        self.summaryRowStart = summaryRowStart
        self.summaryRowEnd = summaryRowEnd

    def downloadData(self):
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



