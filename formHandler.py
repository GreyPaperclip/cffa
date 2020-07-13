"""  CFFA form classes and related logic.

This file includes all form defintions used during jinja templating of form pages in CFFA. Where required, also includes
front end validation logic on input fields. Also includes functionality to convert input form data into CFFA objects
used when populating the backend DB.

Notes
-----

    Where validation requires access to data outside of the default form, an __init__ defintion is added so that the
    data is added to the object prior to validation. For example, list of player names to ensure a new name is unique

"""

from flask_wtf import FlaskForm
from flask_wtf import CsrfProtect
from wtforms import FormField, SubmitField, RadioField, IntegerField, DateField, \
    FloatField, BooleanField, HiddenField, FieldList, StringField, validators, SelectField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from cffadb import footballClasses
import pprint
import logging

pp = pprint.PrettyPrinter()
csrf = CsrfProtect()

# logging config
logger = logging.getLogger("cffa_formHandler")
logger.setLevel(logging.DEBUG)
# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatting = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
ch.setFormatter(formatting)
logger.addHandler(ch)


class AddTeam(FlaskForm):
    """ Simple input form class to specify the team name.

    Attributes
    ----------

    teamName : wtforms StringField
        str team input field
    submitNewteam : wtforms Submitfield

    """
    teamname = StringField("New Team Name", [validators.required()])
    submitnewteam = SubmitField("Next")

    def __init__(self, all_team_names, *args, **kwargs):
        """ Requires init so that all_team_names can be part in the class and checked against during validation to
        prevent re-use of the same name

        Parameters
        ----------

        all_team_names : `list` of `str`
            Should be set against the current list of all other team names. Make sure the current name is not in
            this list.
        *args : *args
            Passed through to the FlaskForm
        **kwargs : **kwargs
            Passed through to the FlaskForm

        """

        FlaskForm.__init__(self, *args, **kwargs)
        # formdata = hmmm add at it works but now has broken new_game -formdata override removed when page has own
        # entry point.
        # FlaskForm.__init__(self, formdata=None, *args, **kwargs)
        self.all_team_names = all_team_names  # for validation to ensure team name is unique

    def validate(self):
        """ Validation logic to check if the team name entered already exists in the database """
        if not super().validate():
            return False
        result = True

        if self.teamname.data in (item[1] for item in self.all_team_names):
            self.playername.errors.append("Team name already in use. Choose a different one!")
            result = False

        return result


class AddGameNoPlayers(FlaskForm):
    """  wtform as first step in the Add Game wizard. The number of players is used in the GameDetails validation
     to ensure the right number of players are selected.

     TO DO: Other option is not yet implemented

      Attributes
      ----------

      noplayers: RadioField
        wtform simple radiofield
      submit: SubmitField
        wtform simple submit button

        """
    noplayers = RadioField('noPlayers', choices=[('6', '6 Players'),
                                                 ('7', '7 Players'),
                                                 ('8', '8 Players'),
                                                 ('9', '9 Players'),
                                                 ('10', '10 Players'),
                                                 ('11', '11 Players'),
                                                 ('12', '12 Players'),
                                                 ('13', '13 Players'),
                                                 ('14', '14 Players'),
                                                 ('Other', 'Other')])
    submit = SubmitField("Next")


class PlayerInGame(FlaskForm):
    """ Part of both add and edit game form. Each PlayerInGame form represents a row in the input table that is used to
    select whether a player booked (ie: paid for) the pitch, played, or had guests. The playedLastGame helps usability
    by checking players who played in the previous game - based on the logic that frequent players are most likely to
    play the next game. Note that all validation occurs in GameDetails not this form.

    Attributes
    ----------

    id : HiddenField
        Used to identify each row when selected. Not exposed to the user in the GUI
    playermame : StringField
        Player Name. Users can enter any name to quickly modify who played in the match, instead of multi-click pull
        downs. App will create any new users automatically however there is a architectural flaw if a incorrect name is
        added as it is not possible to remove that name from the DB.
    playedlastgame : BooleanField
        Checked (true) if the player played the last game. This is set via the obj= argument int he GameDetails
        flaskform as the provided obj contains n object with the same field name (playedLastGame).
    pitchbooker : BooleanField
        Checked (true) when this player booked the pitch. Logic will preset the booker as the person who is logged into
        CFFA - as this is the most likely booker of the game.
    guests: IntegerField
        By default 0, this logic handles that one-off guests might join the game. CFFA logic means that the player will
        pick up the costs of the guests (ie: their portion of the booking cost).
    """
    id = HiddenField('Player DB ID')
    playername = StringField("Player Name")
    playedlastgame = BooleanField('Played')
    pitchbooker = BooleanField('Booker')
    guests = IntegerField('Guests', [validators.optional()])


class GameDetails(FlaskForm):
    """ Used by new and edit game this contains all the data for each game. Note that a FieldList is used to show each
    player details in the game. Validation ensures that duplicate names cannot be entered and only one person can
    be chosen as the game booker.

    Requires __init__ function so that validation can check if the right number of players are checked by the user.

    TO DO: validation for Game Date, or pull down to select from calender. Implement titling of player names
    (first letter is a capital). There is also a bad flaw in the DB design as a player name could clash with a another
    key not associated with player name, needs redesign before production use. for example, don't enter a player name as
    'Cost of Game'!

    TO DO: NB: CFFA only supports GBP, hardcoded currency behaviour.

    Attributes
    ----------

    gamecost : FloatField
        Cost in GBP for the game booking. Eventually converted to Decimal128 for currency DB storage.
    gamedate : DateField
        DateTime.DateTime is the data attribute in this input field
    playerlist : `FieldList` of `PlayerInGame` obj of `FlaskForm.
        Note the minimum number of rows is 10 when displaying the form. Logic will pad out empty rows if default
        population does not cover sufficient rows.
    submit : SubmitField
        Standard submit button.

    """

    gamecost = FloatField('Cost of Game', [validators.required()])
    gamedate = DateField('Game Date', [validators.required()])
    playerlist = FieldList(FormField(PlayerInGame), min_entries=10)
    submit = SubmitField('Submit')

    def __init__(self, number_of_expected_players, *args, **kwargs):
        """ Requires init so that number_of_expected_players can be part in the class and checked against during
        validation to ensure the right number of players are checked. This logic counts any guests specified as well.

        Parameters
        ----------

        number_of_expected_players : `int`
            Set by the user in the form AddGameNoPlayers
        *args : *args
            Passed through to the FlaskForm
        **kwargs : **kwargs
            Passed through to the FlaskForm

        """
        FlaskForm.__init__(self, *args, **kwargs)
        # formdata = hmmm add at it works but now has broken new_game -formdata override removed when page has own
        # entry point.
        # FlaskForm.__init__(self, formdata=None, *args, **kwargs)
        self.number_of_expected_players = number_of_expected_players

    def validate(self):
        """ Checks only for: a) right number of players selected, including guest numbers. (b) There must be one booker
         selected. Note that a booker does not have to play the game """
        if not super().validate():
            return False
        result = True
        selected_player_list = set()
        number_of_selected_players = 0
        count_bookers = 0
        for field in [self.playerlist.data]:
            for x in field:
                if x.get("playedlastgame"):
                    if x.get("playername") in selected_player_list:
                        self.playerlist.errors.append("Duplicate player provided - check player names!")
                        result = False
                    elif x.get("playername") == "" or x.get("playername") is None:
                        self.playerlist.errors.append("Cannot play an unnamed player. Please enter a name!")
                        result = False
                    else:
                        selected_player_list.add(x.get("playername"))
                    number_of_selected_players += 1
                # don't need to play a game to have a guest
                # print("GameDetails form: player name ", x.get("playername"), " has ", x.get("guests"), " guests")
                number_of_selected_players += x.get("guests", 0)
                if x.get("pitchbooker"):
                    count_bookers += 1

        if self.number_of_expected_players > 0:
            if self.number_of_expected_players != number_of_selected_players:
                our_error = "Unexpected number of players. " + \
                            str(number_of_selected_players) + \
                            " selected, but " + \
                            str(self.number_of_expected_players) + \
                            " expected!"
                self.playerlist.errors.append(our_error)
                result = False

        if count_bookers != 1:
            self.playerlist.errors.append("There must be one player who booked the pitch!")
            result = False

        return result


class EditGameSelectForm(FlaskForm):
    """ Form to select a previous game before showing the edit game form. Validation in case no games have been
    played yet for new deployments.

      Attributes
      ----------

      game : SelectField
        User is show a pull-down list of games. Integer value is used for indexing hence coerce=int
      submitedit : SubmitField
        wtform simple submit button

        """
    game = SelectField(u'Game', coerce=int)
    submitedit = SubmitField("Edit Game")

    def validate(self):
        if not super().validate():
            return False

        result = True

        if self.game.data is None:
            self.game.errors.append("Game must be selected first, or maybe play a game!")
            result = False

        return result


class DeleteGameSelectForm(FlaskForm):
    """ Form to select a previous game before showing the delete game confirmation form. Validation in case no games
    have been played yet for new deployments.

      Attributes
      ----------

      game : SelectField
        User is show a pull-down list of games. Integer value is used for indexing hence coerce=int
      submitdel : SubmitField
        wtform simple submit button

        """
    game = SelectField(u'Game', coerce=int)
    submitdel = SubmitField("Delete Game")

    def validate(self):
        if not super().validate():
            return False

        result = True

        if self.game.data is None:
            self.game.errors.append("Game must be selected first, or maybe play a game!")
            result = False

        return result


class ConfirmDelete(FlaskForm):
    """ Super simple form def to confirm game deletion.

      Attributes
      ----------

      confirmdel : SubmitField
        wtform simple submit button

        """
    confirmdel = SubmitField("Confirm Game Deletion")


class NewPlayer(FlaskForm):
    """ Form to add a new player (not CFFA user) into the system. Note that CFFA will also add new players in the add
    and edit game forms if the name is not recognised. Form must be initialized for validation to ensure players [names]
    cannot be duplicated.

      Attributes
      ----------

      playername: StringField
        Player Name, typically nickname as this is a casual tool to help football finances! Note that player names are
        titled during validation (first letter in each worth capitalised).
      comment: StringField
        User can enter a comment. Not used much at present.
      submitnew: SubmitField
        wtform simple submit button

        """
    playername = StringField("Enter player nickname: ")
    comment = StringField("Enter comments: ")
    submitnew = SubmitField("Add Player")
    all_players = []

    def __init__(self, all_players, *args, **kwargs):
        """ Requires init so that all_players can be part in the class and checked against during validation
        to ensure the right number of players are checked. This logic counts any guests specified as well.

        Parameters
        ----------

        all_players : `list` of `str`
            Should be set against the current list of all other player names. Make sure the entered player name is not
            in this list.
        *args : *args
            Passed through to the FlaskForm
        **kwargs : **kwargs
            Passed through to the FlaskForm

        """
        FlaskForm.__init__(self, *args, **kwargs)

        self.all_players = all_players

    def validate(self):
        """ validation function for this form, see init for more details. """
        if not super().validate():
            return False

        result = True
        titled_player_name = self.playername.data.title()  # make sure it is consistent.

        if titled_player_name in (item[1] for item in self.all_players):
            self.playername.errors.append("Duplicate player name entered - check summary!")
            result = False

        return result
        # TO DO: code to check for duplicate names when submitting new player


class SelectPlayerToEdit(FlaskForm):
    """ Form to select a player to edit.

      Attributes
      ----------

      oldplayer: SelectField
        Noting that the playername can be changed, so variable is called oldplayer. Indexed by int and initialised
        after the form object is created by setting the choices attribute (outside of this code).

      submiteditplayer: SubmitField
        wtform simple submit button

        """
    oldplayer = SelectField(u'PlayerName', coerce=int)
    submiteditplayer = SubmitField("Edit selected Player")


class EditPlayer(FlaskForm):
    """ Form to edit a player (not CFFA user) into the system. Form must be initialized for validation to ensure
    players [names] cannot be duplicated.

      Attributes
      ----------

      playername: StringField
        Player Name, typically nickname as this is a casual tool to help football finances! Note that player names are
        titled during validation (first letter in each worth capitalised).
      retiree: BooleanField
        Retiree controls if a player is in an active list of players (and hence may or may not get displayed depending
        on circumstances. You cannot delete a player in CFFA. TO DO: delete player.
      comment: StringField
        User can enter a comment. Not used much at present.
      submitEdit: SubmitField
        wtform simple submit button

        """
    playername = StringField("Enter new player name: ")
    retiree = BooleanField('Retired')
    comment = StringField("Update comments: ")
    submitedit = SubmitField("Apply Changes")

    def __init__(self, all_players, *args, **kwargs):
        """ Requires init so that all_players can be part in the class and checked against during validation
        to ensure the right number of players are checked. This logic counts any guests specified as well.

        Parameters
        ----------

        all_players : `list` of `str`
            Should be set against the current list of all other player names. Make sure the entered player name is not
            in this list.
        *args : *args
            Passed through to the FlaskForm
        **kwargs : **kwargs
            Passed through to the FlaskForm

        """
        FlaskForm.__init__(self, *args, **kwargs)

        self.allPlayersExceptMe = all_players
        # all_players must be list of all players excluding the player being edited.

    def validate(self):
        """ validation function for this form, check whether the name entered already exists. """
        if not super().validate():
            return False

        result = True
        titled_player_name = self.playername.data.title()  # make sure it is consistent.

        if titled_player_name in (item[1] for item in self.allPlayersExceptMe):
            self.playername.errors.append("Duplicate player name entered - check summary!")
            result = False

        return result


class RetirePlayer(FlaskForm):
    """ Form to select  a player (not CFFA user) to retire so that they are not listed as an active user (eg: not
    automatically populated when adding an new game into the system).

      Attributes
      ----------

      retireplayer: StringField
        SelectField indexed by an int. Note that the choices attribute is set after this object is created so the
        pull down operates.

      submitretire: SubmitField
        wtform simple submit button

        """
    retireplayer = SelectField(u'PlayerName', coerce=int)
    submitretire = SubmitField("Retire")


class ReactivatePlayer(FlaskForm):
    """ Form to select  a player (not CFFA user) to reactivate (from retirement) so that they are now listed as an
    active user.

      Attributes
      ----------

      reactivateplayer: StringField
        SelectField indexed by an int. Note that the choices attribute is set after this object is created so the
        pull down operates.

      submitreactivate: SubmitField
        wtform simple submit button

        """
    reactivateplayer = SelectField(u'PlayerName', coerce=int)
    submitreactivate = SubmitField("Reactivate")


class NewTransaction(FlaskForm):
    """ Form to add a new transaction between the manager (accounts owner) and player. This does not include credits
    for booking as they are part of the add game functionality. An example would be when a player gives the manager
    £20 to clear their debt from previous games they have played. Another example is when a player retires and their
    account is in credit and the manager returns the remainder of their money.

      Attributes
      ----------

      player: SelectField
        Pull down to select which player is transaction is with.

      transactiondate: DateField
        What day the money was transferred

      amount : FloatField
        How much was transferred

      type: StringField
        Description of the transfer, eg: cash, credit for beers in after game pub etc

      submittrans: SubmitField
        wtform simple submit button

        """
    player = SelectField(u'PlayerName', coerce=int)
    transactiondate = DateField('Transaction Date', [validators.required()])
    amount = FloatField('Amount', [validators.required()])
    type = StringField("Description")
    submittrans = SubmitField("Add Transaction")


class AutopayforCurrentUser(FlaskForm):
    """ AutoPay form covers the regular transaction made by the accounts manager where money is never transferred to
    themselves but as they played the game their accounts still need to updated. This form is re-populated so only
    requires the manager to quickly confirm the transaction.

    TO DO: Prevent managers repeatedly confirming this form for the same game

     Attributes
     ----------

     submitautopay : SubmitField
        Confirms the autopay

    """

    submitautopay = SubmitField("AutoPay")


class CFFASettings(FlaskForm):
    """ Currently only supports the Team Name setting (this is the only setting currently). May not be required because
    team Name is duplicated in the Tenancy collection as well.

    TO DO: add settings to define what constitutes a recent games and transaction. Currently hardcoded to 6 months

    Attributes
    ----------

    teamname : StringField
        Set the teamName

    submitteam : SubmitField
        Confirmation Button

     """
    teamname = StringField("Team Name")
    submitteam = SubmitField("Update Team Name")


class DownloadJSON(FlaskForm):
    """ Button form to confirm download of the database in JSON format.

    TO DO: separate this functionality to admin class users only instead of managers

     Attributes
     ----------

     submitdownload : SubmitField
        Confirm Download.
     """

    submitdownload = SubmitField("Download DB archive")


class UploadJSON(FlaskForm):
    """ Form to upload JSON into the DB. Not implemented and likely validators will not work yet. Once implemented this
    will drop the current database collections for the tenancy to upload the JSON data. Will not append existing data.

    TO DO: Implement

    Attributes
    ----------

    selectarchivefile : FileField
        FlaskForm class type.

    submitrecovery: SubmitField
        Confirm upload and reset of db.

    """

    selectarchivefile = FileField('CFFA Archive File', validators=[FileRequired(),
                                                                   FileAllowed('cffaDB',
                                                                               'CFFA DB exports only!')])
    submitrecovery = SubmitField("Reset and Recover DB")


class AddAccess(FlaskForm):
    """ Access form to add a user to CFFA. The user may not necessarily be a player or manager of the system, but the
    user name should match a player if one exists.

    TO DO: Add validation to prevent duplicate user names. This will require a __init__ and validation logic to work
    (similar to the add player form).

    Attributes
    ----------

    name : StringField
        Name of CFFA user.

    authid : StringField
        This is the auth0 user ID - string starting with auth0| . Only the auth0 admin can confirm the user ID.
        Onboarding process requires the administrator to access Auth0 management portal to manually add the user,
        and confirm auth0 user ID.
        Long Term TO DO: Write separate gRPC service to use the AUth0 REST API to manage users - this app can then
        connect via gRPC to manage users better.

    type : SelectField
        Currently only Manager and Player have access. Players are restricted to seeing their summary data only and
        cannot make any changes. TO DO: Introduce Admin class for actions such as CFFA user access endpoints, and
        database export, import, googlesheet import, DB reset.

    submitaddaccess: SubmitField
        Confirm access to new user.

    """
    name = StringField("Name")
    authid = StringField("Auth0 ID")
    type = SelectField(u'UserType', choices=[('Manager', 'Manager'), ('Player', 'Player')])
    submitaddaccess = SubmitField("Add User")


class SelectEditUserAccess(FlaskForm):
    """ Form to edit user access including disabling user access. User deletion is not posssible currently.

    TO DO: Implement

    Attributes
    ----------

    edituser : SelectField
        Indexed by int, shows list of users to edit. After form obj is created, selection list must set via the choices
        attribute.

    submitedituser: SubmitField
        Confirm which user has been selected.

    """

    edituser = SelectField(u'name', coerce=int)
    submitedituser = SubmitField("Edit User")


class SelectRevokeUserAccess(FlaskForm):
    """ Unused form as functionality is possible in the EditUserAccess form.

    TO DO: Maybe implement in CFFA as a usability but duplicate function.

    Attributes
    ----------

    revokeuser : SelectField
        Indexed by int, shows list of users to revoke access. After form obj is created, selection list must set via the
        choices attribute. Only one user can be revoked at a time.

    submitedituser: SubmitField
        Confirm which user has been selected.

    """
    revokeuser = SelectField(u'name', coerce=int)
    submitrevokeuser = SubmitField("Revoke User")


class EditUserAccess(FlaskForm):
    """ Edit the access attributes for a CFFA user..

    Attributes
    ----------

    name : StringField
        Edit the name of the user. Note this must match the name of the user in Auth0

    authID : StringField
        Must match the auth0 ID allocated by Auth0 in their management authorisation system

    type : SelectField
        Change user role, currently fixed.

    revoked: BooleanField
       Change whether a user has access or not.

    submitedituseraccess: SubmitField
        Confirm user changes (if any).

    """
    name = StringField("Name")
    authid = StringField("Auth0 ID")
    type = SelectField(u'UserType', choices=[('Manager', 'Manager'), ('Player', 'Player')])
    revoked = BooleanField('Revoked')
    submitedituseraccess = SubmitField("Commit changes to user")


class PopulateFromGoogleSheet(FlaskForm):
    """ Import a google sheet containing football data. Refer to sheet template for formatting. The google sheet
    must be set up for API sharing with a specifc user and the secure json access key must be uploaded to CFFA
    to permit access.

    TO DO: complete template and introduce checks on fields. perhaps break up so that the sheet is loaded first and user
    can select the tabs and rows etc.

    Attributes
    ----------

    googlefile : FileField
        The google sheet json key file.

    sheetname : StringField
        Name of the google spreadsheet

    transactionsheetname : StringField
        Worksheet (tab) name containing all transactions

    gamesheetname : StringField
        Worksheet (tab) name containing all games played

    summarysheetname : StringField
        Worksheet (tab) name containing summary data

    summarysheetstartrow : IntegerField
        Row number of when the summary starts on the summarySheet.

    summarysheetendrow : IntegerField
        Row number of when the summary ends on the summarySheet.

    submitupload: SubmitField
        Submit above data and execute import.
        """

    googlefile = FileField()
    sheetname = StringField("Google Sheet Document Name")
    transactionsheetname = StringField("Worksheet name with transactions")
    gamesheetname = StringField("Worksheet name with games data")
    summarysheetname = StringField("Worksheet name with summary data")
    summarysheetstartrow = IntegerField("Start row on summary worksheet")
    summarysheetendrow = IntegerField("End row on summary worksheet")
    submitupload = SubmitField("Upload google sheet")


class DeleteAll(FlaskForm):
    """ Form to confirm deletion of all user collections and the Tenancy collection. TO DO: Be more graceful by only
    removing tenancies for the current user.

    Attributes
    ----------

    confirmdelete: SubmitField
        Confirm deletion of database.

    """
    confirmdelete = SubmitField("Confirm delete all data")


def create_labels_for_games(games):
    """ Function to create the displayed labels for the selectGames forms (editGame and deleteGame). Label consists
    of date, number of players, game cost and the list of player names in each game.

    Parameters
    ----------

    games : `list` of `dict`
        The dict is direct extract from the games collection from mongo hence date is a DateTime obj.

    Returns
    -------

    :str:list
        List of game labels

    """
    # games is a list of dicts from DB not a game class
    game_labels = []
    custom_id = 0
    for game in games:
        game_date = game.get("Date of Game dd-MON-YYYY")
        game_label = str(game_date.year) + "/" + str(game_date.month) + "/" + str(game_date.day) + \
                     "," + str(game.get("Players")) + " players, " + \
                     str(game.get("Cost of Game").to_decimal()) + " : " + game.get("PlayerList")
        game_labels.append((custom_id, game_label))
        custom_id += 1

    return game_labels


def create_labels_for_players(players, action):
    """ Function to create the displayed labels for the selectPlayer forms (editPlayer and retirePlayer). Label consists
     of player names. Depending on use, action is used to determine what players are listed.

     Parameters
     ----------

     players : `list` of `players'
         The dict is  extract from the TeamPlayers collection from mongo.

     action : str
        all_players - include every player. "retire" - list of active players. "reactivate" - list of deactivated users.

     Returns
     -------

     :tuple:list
        consisting of an ID (integer from 0) and the playerName.

     """
    player_labels = []
    custom_id = 0
    for player in players:
        if action == "allplayers":
            player_labels.append((custom_id, player.get("playerName")))
        elif action == "retire" and not player.get("retiree", False):
            player_labels.append((custom_id, player.get("playerName")))
        elif action == "reactivate" and player.get("retiree", False):
            player_labels.append((custom_id, player.get("playerName")))

        custom_id += 1

    return player_labels


def delete_game_form(games):
    """ Unused function originally designed to specify the labels for delete game. C.

     Parameters
     ----------

     games : `list` of `games'
         The dict is an extract from the Games collection from mongo.

     Returns
     -------

     :FlaskForm
        DeleteGame form.

     """
    game_labels = []
    custom_id = 0
    for game in games:
        game_date = game.get("Date of Game dd-MON-YYYY")
        game_label = str(game_date.year) + "/" + str(game_date.month) + "/" + str(game_date.day) + \
                     "," + str(game.get("Players")) + " players, " + \
                     str(game.get("Cost of Game").to_decimal()) + " : " + game.get("PlayerList")
        game_labels.append((custom_id, game_label))
        custom_id += 1

    form = DeleteGameSelectForm(obj=game_labels)
    form.game.choices = game_labels
    return form


def game_form_to_football(form):
    """ Converts the completed GameDetails form into the FootballClasses game object (with number of Player objects for
    easier processing into mongoDB.

     Parameters
     ----------

     form : GameDetails obj
         Completed GameDetails object from edit or new game.

     Returns
     -------

     :FootballClasses.game obj

     """

    new_game_players = []
    the_booker = None

    for player in form.playerlist:
        new_player = footballClasses.Player(player.id,
                                            player.playername.data,
                                            player.playedlastgame.data,
                                            player.pitchbooker.data,
                                            player.guests.data)
        new_game_players.append(new_player)

        if player.pitchbooker.data:
            the_booker = player.playername.data

    new_game = footballClasses.Game(form.gamecost.data, form.gamedate.data, new_game_players, the_booker)

    return new_game


def new_player_form_to_football(form):
    """ Converts the completed new_player form into the FootballClasses player object  for
    easier processing into mongoDB.

     Parameters
     ----------

     form : new_player obj
         Completed new_player object from edit or new game.

     Returns
     -------

     :FootballClasses.TeamPlayer obj

     """

    new_player = footballClasses.TeamPlayer(form.playername.data,
                                            False,
                                            form.comment.data)

    return new_player


def edit_player_form_to_football(form):
    """ Converts the completed EditPlayer form into the FootballClasses player object  for
    easier processing into mongoDB.

     Parameters
     ----------

     form : EditPlayer obj
         Completed new_player object from edit or new game.

     Returns
     -------

     :FootballClasses.TeamPlayer obj

     """

    player = footballClasses.TeamPlayer(form.playername.data, form.retiree.data, form.comment.data)
    return player


def new_transaction_form_to_football(form, player):
    """ Converts the completed NewTransaction form into the FootballClasses transaction object  for
    easier processing into mongoDB.

     Parameters
     ----------

     form : NewTransaction obj
         Completed NewTransaction object from new or edit transaction.

     player : str
        The players name to identify who sent/received the transaction.

     Returns
     -------

     :FootballClasses.Transaction obj

     """
    titled_player = player.title()
    transaction = footballClasses.Transaction(titled_player,
                                              form.type.data,
                                              form.amount.data,
                                              form.transactiondate.data)
    return transaction


def create_labels_for_users(users):
    """ Create the selectForm labels for new CFFA users.

     Parameters
     ----------

     users : AddAccess obj
         Completed AddAccess object from new or edit transaction.

     Returns
     -------

     :tuple:list
        List of select labels indexed by an int.

     """
    user_labels = []
    custom_id = 0
    for user in users:
        user_labels.append((custom_id, user.name))
        custom_id += 1

    return user_labels


def edit_user_access_form_to_football(form):
    """ Converts the Add/Edit User access form into the FootballClasses CFFAuser object for
    easier processing into mongoDB.

     Parameters
     ----------

     form : EditUserAccess or AddAccess obj
         Completed user access object from new or edit transaction.

     Returns
     -------

     :FootballClasses.CFFAUser obj

     """
    user = footballClasses.CFFAUser(form.name.data, form.authid.data, form.type.data, form.revoked.data)
    return user
