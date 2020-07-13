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
    """ Class def for google importer - contaisn all the required data to successfully access and download football
    data.

    Attributes
    ----------

    db : footballDB
        CFFA db class for the underlying mongoDB. Must be initialised and connected for population to work

    key_filename : str
        Filename for the json key file from google. This is stored in the webserver under uploads and is not accessible
        externally.

    gsheet_name : str
        Name of google sheet

    transactions_worksheet : str
        Worksheet name in your google sheet with transaction data

    game_worksheet: str
        Worksheet name in your google sheet with game data

    summary_worksheet: str
        Worksheet name in your google sheet with summary data showing things such as balances, games played etc

    summary_row_start: int
        The summary sheet might not summarise from the first tow. Specify from which row to import

    summary_row_end: int
        The summary sheet might have lots of other data. States which row to stop importing from.

    """

    def __init__(self, database_obj, keyfile, gsheet_name, transactions_worksheet, game_worksheet,
                 summary_worksheet, summary_row_start, summary_row_end):
        """ Configure the object with the necessary data to connect and import from a google sheet.

        Parameters
        ----------

    db : footballDB
        CFFA db class for the underlying mongoDB. Must be initialised and connected for population to work

    key_filename : str
        Filename for the json key file from google. This is stored in the webserver under uploads and is not accessible
        outside of the server.

    gsheet_name : str
        Name of google sheet

    transactions_worksheet : str
        Worksheet name in your google sheet with transaction data

    game_worksheet: str
        Worksheet name in your google sheet with game data

    summary_worksheet: str
        Worksheet name in your google sheet with summary data showing things such as balances, games played etc

    summary_row_start: int
        The summary sheet might not summarise from the first tow. Specify from which row to import

    summary_row_end: int
        The summary sheet might have lots of other data. States which row to stop importing from.

        """

        self.db = database_obj
        self.key_filename = keyfile
        self.gsheet_name = gsheet_name
        self.transactions_worksheet = transactions_worksheet
        self.game_worksheet = game_worksheet
        self.summary_worksheet = summary_worksheet
        self.summary_row_start = summary_row_start
        self.summary_row_end = summary_row_end

    def download_data(self):
        """ Calls a series of methods on both the googleImport and footballDB objects to obtain and populate data. Note
        that the logic reads each worksheet in full and populates documents/collections accordingly.

        Once data is populated, calcPopulateTeamSummary is called to calculate the summary. The DB is ready to be used.
        The logic will remove all prior collections prior to population so this is replace not append logic.

        TO DO: error handling!

        Returns
        -------

            :Str
            String message on status so that CFFA can banner the message to the end user.

        """

        google = googleImport.Googlesheet(self.key_filename,
                                          self.gsheet_name,
                                          self.transactions_worksheet,
                                          self.game_worksheet,
                                          self.summary_worksheet)

        main_players = google.derive_players(self.summary_row_start,
                                             self.summary_row_end)

        self.db.populate_payments(google.transactions)
        google.calc_player_list_per_game()
        self.db.populate_games(google.all_games)
        adjustments = google.calc_player_adjustments(self.summary_row_start, self.summary_row_end)
        self.db.populate_adjustments(adjustments)
        self.db.calc_populate_team_summary(main_players)

        player_detalls = []
        for player in main_players:
            player_dict = dict(playerName=player,
                               retiree=self.db.should_player_be_retired(player),
                               comment="Imported from GoogleSheet")
            player_detalls.append(player_dict)
        self.db.populate_team_players(player_detalls)

        return "Imported data from google sheet:" + self.gsheet_name
