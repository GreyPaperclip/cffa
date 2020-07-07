
import datetime
import pprint
from os import environ as env
from dotenv import load_dotenv, find_dotenv
import constants

ENV_FILE = find_dotenv()
if ENV_FILE:
    print('Found env file ')
    load_dotenv(ENV_FILE)

BACKEND_DBUSR = env.get(constants.BACKEND_DBUSR)
BACKEND_DBPWD = env.get(constants.BACKEND_DBPWD)
BACKEND_DBHOST = env.get(constants.BACKEND_DBHOST)
BACKEND_DBPORT = env.get(constants.BACKEND_DBPORT)
BACKEND_DBNAME = env.get(constants.BACKEND_DBNAME)
GOOGLEKEYFILE = env.get(constants.GOOGLEKEYFILE)
GOOGLE_SHEET = env.get(constants.GOOGLE_SHEET)
TRANSACTION_SRC_WKSHEET = env.get(constants.TRANSACTION_SRC_WKSHEET)
GAME_SRC_WKSHEET = env.get(constants.GAME_SRC_WKSHEET)
SUMMARY_SRC_WKSHEET = env.get(constants.SUMMARY_SRC_WKSHEET)
CFFA_USERID = env.get(constants.CFFA_USERID)

from cffadb import dbinterface
from cffadb import footballClasses
from cffadb import googleImport

mongoConnectString = "mongodb://" + BACKEND_DBUSR + ":" + BACKEND_DBPWD + "@" + BACKEND_DBHOST + ":" + BACKEND_DBPORT + "/" + BACKEND_DBNAME

pp = pprint.PrettyPrinter()

ourDB = dbinterface.FootballDB(mongoConnectString, BACKEND_DBNAME)
if ourDB.loadTeamTablesForUserId(CFFA_USERID) == False:
    print(" Could not load DB tables")
    exit(-1)

google = googleImport.Googlesheet(GOOGLEKEYFILE,
                     GOOGLE_SHEET,
                     TRANSACTION_SRC_WKSHEET,
                     GAME_SRC_WKSHEET,
                     SUMMARY_SRC_WKSHEET
                     )

playersFromMainSheet = google.derivePlayers(24,66)

ourDB.populatePayments(google.transactions)
print (google.calcPlayerListPerGame())
ourDB.populateGames(google.allgames)
foobar = google.calcPlayerAdjustments(24,66)
ourDB.populateAdjustments(foobar)
#Calc summary then put into DB
ourDB.calcPopulateTeamSummary(playersFromMainSheet)
playerDetails = []
for player in playersFromMainSheet:

    playerDict = dict(playerName=player,
                      retiree=ourDB.shouldPlayerBeRetired(player),
                      comment="Imported from GoogleSheet")
    playerDetails.append(playerDict)
ourDB.populateTeamPlayers(playerDetails)

recentGames = ourDB.getRecentGames()
allGames = ourDB.getAllGames()
recentTransactions = ourDB.getRecentTransactions();
#pp.pprint(recentTransactions)
activePlayers = ourDB.getActivePlayerSummary()
allPlayers = ourDB.getFullSummary()
allTransactions = ourDB.getAllTransactions()

# now testing DB class.

lastgame = ourDB.getLastGameDetails()
#pp.pprint(lastgame)
activePlayers2 = ourDB.getActivePlayersForNewGame()
#pp.pprint(activePlayers2)
inactivePlayers2 = ourDB.getInactivePlayersForNewGame()
#pp.pprint(inactivePlayers2)

lastGameDetails = ourDB.getDefaultsForNewGame("Richard")

#print(ourDB.addGame(game))
print("------------")

dbid = ourDB.getLastGameDBID()
print ("DBID", dbid)
game = ourDB.getGameDetailsForEditDeleteForm(dbid, True)
print(game)

