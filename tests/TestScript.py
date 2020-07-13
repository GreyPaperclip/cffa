import datetime
import pprint
from os import environ as env
from dotenv import load_dotenv, find_dotenv
import constants
from cffadb import dbinterface
from cffadb import footballClasses
from cffadb import googleImport

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

mongo_connect_string = "mongodb://" + BACKEND_DBUSR + ":" + \
                       BACKEND_DBPWD + "@" + BACKEND_DBHOST + ":" + \
                       BACKEND_DBPORT + "/" + BACKEND_DBNAME

pp = pprint.PrettyPrinter()

ourDB = dbinterface.FootballDB(mongo_connect_string, BACKEND_DBNAME)
if not ourDB.load_team_tables_for_user_id(CFFA_USERID):
    print(" Could not load DB tables")
    exit(-1)

google = googleImport.Googlesheet(GOOGLEKEYFILE,
                                  GOOGLE_SHEET,
                                  TRANSACTION_SRC_WKSHEET,
                                  GAME_SRC_WKSHEET,
                                  SUMMARY_SRC_WKSHEET
                                  )

players_from_main_sheet = google.derive_players(24, 66)

ourDB.populate_payments(google.transactions)
print(google.calc_player_list_per_game())
ourDB.populate_games(google.all_games)
foobar = google.calc_player_adjustments(24, 66)
ourDB.populate_adjustments(foobar)
# Calc summary then put into DB
ourDB.calc_populate_team_summary(players_from_main_sheet)
player_details = []
for player in players_from_main_sheet:
    player_dict = dict(playerName=player,
                       retiree=ourDB.should_player_be_retired(player),
                       comment="Imported from GoogleSheet")
    player_details.append(player_dict)
ourDB.populate_team_players(player_details)

recent_games = ourDB.get_recent_games()
all_games = ourDB.get_all_games()
recent_transactions = ourDB.get_recent_transactions()
# pp.pprint(recent_transactions)
active_players = ourDB.get_active_player_summary()
all_players = ourDB.get_full_summary()
all_transactions = ourDB.get_all_transactions()

# now testing DB class.

last_game = ourDB.get_last_game_details()
# pp.pprint(last_game)
active_playersX = ourDB.get_active_players_for_new_game()
# pp.pprint(active_playersX)
inactive_playersX = ourDB.get_inactive_players_for_new_game()
# pp.pprint(inactive_playersX)

last_game_details = ourDB.get_defaults_for_new_game("Richard")

# print(ourDB.add_game(game))
print("------------")

db_id = ourDB.get_last_game_db_id()
print("DBID", db_id)
game = ourDB.get_game_details_for_edit_delete_form(db_id, True)
print(game)
