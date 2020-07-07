from flask_wtf import FlaskForm
from flask_wtf import CsrfProtect
from wtforms import FormField, SubmitField, RadioField, IntegerField, DateField,\
    FloatField, BooleanField, HiddenField, FieldList, StringField, validators, SelectField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired
from cffadb import footballClasses
import pprint
import datetime
pp = pprint.PrettyPrinter()
csrf = CsrfProtect()
import logging

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
    teamName = StringField("New Team Name", [validators.required()])
    submitNewTeam = SubmitField("Next")

    def __init__(self, allTeamNames, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        # formdata = hmmm add at it works but now has broken newgame -formdata override removed when page has own entry point.
        # FlaskForm.__init__(self, formdata=None, *args, **kwargs)
        self.allTeamNames = allTeamNames  # for validation to ensure team name is unique

    def validate(self):
        if not super().validate():
            return False
        result = True

        if self.teamName.data in (item[1] for item in self.allTeamNames):
            self.playerName.errors.append("Team name already in use. Choose a different one!")
            result = False

        return (result)


class AddGame_NoPlayers(FlaskForm):
    noPlayers = RadioField('noPlayers', choices=[('6', '6 Players'),
                                                 ('7', '7 Players'),
                                                 ('8', '8 Players'),
                                                 ('9', '9 Players'),
                                                 ('10', '10 Players'),
                                                 ('11', '11 Players'),
                                                 ('12', '12 Players'),
                                                 ('13', '13 Players'),
                                                 ('14', '14 Players'),
                                                 ('Other', 'Other')]
                             )
    submit = SubmitField("Next")

class PlayerInGame(FlaskForm):
    id = HiddenField('Player DB ID')
    playerName = StringField("Player Name")
    playedLastGame = BooleanField('Played')
    pitchBooker = BooleanField('Booker')
    guests = IntegerField('Guests', [validators.optional()])


class GameDetails(FlaskForm):
    gameCost = FloatField('Cost of Game', [validators.required()])
    gameDate = DateField('Game Date', [validators.required()])
    playerList = FieldList(FormField(PlayerInGame), min_entries=10)
    submit = SubmitField('Submit')

    def __init__(self, numberofExpectedPlayers, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        # formdata = hmmm add at it works but now has broken newgame -formdata override removed when page has own entry point.
        # FlaskForm.__init__(self, formdata=None, *args, **kwargs)
        self.numberofExpectedPlayers = numberofExpectedPlayers

    def validate(self):
        if not super().validate():
            return False
        result=True
        selectedPlayerList = set()
        numberofSelectedPlayers = 0
        countBookers = 0
        for field in [self.playerList.data]:
            for x in field:
                if x.get("playedLastGame") == True:
                    if x.get("playerName") in selectedPlayerList:
                        self.playerList.errors.append("Duplicate player provided - check player names!")
                        result=False
                    elif x.get("playerName") == "" or x.get("playerName") == None:
                        self.playerList.errors.append("Cannot play an unnamed player. Please enter a name!")
                        result=False
                    else:
                        selectedPlayerList.add(x.get("playerName"))
                    numberofSelectedPlayers+=1
                # don't need to play a game to have a guest
                # print("GameDetails form: player name ", x.get("playerName"), " has ", x.get("guests"), " guests")
                numberofSelectedPlayers+=x.get("guests", 0)
                if x.get("pitchBooker") == True:
                    countBookers+=1

        if self.numberofExpectedPlayers > 0:
            if self.numberofExpectedPlayers != numberofSelectedPlayers:
                ourError = "Unexpected number of players. " + str(numberofSelectedPlayers) + " selected, but "\
                                                                                       + str(self.numberofExpectedPlayers) + " expected!"
                self.playerList.errors.append(ourError)
                result=False

        if countBookers != 1:
            self.playerList.errors.append("There must be one player who booked the pitch!")
            result=False

        return(result)



class EditGameSelectForm(FlaskForm):
    game = SelectField(u'Game', coerce=int)
    submitEdit = SubmitField("Edit Game")

    def validate(self):
        if not super().validate():
            return False

        result=True

        if self.game.data == None:
            self.game.errors.append("Game must be selected first, or maybe play a game!")
            result=False

        return(result)

class DeleteGameSelectForm(FlaskForm):
    game = SelectField(u'Game', coerce=int)
    submitDel = SubmitField("Delete Game")

    def validate(self):
        if not super().validate():
            return False

        result=True

        if self.game.data == None:
            self.game.errors.append("Game must be selected first, or maybe play a game!")
            result=False

        return(result)

class ConfirmDelete(FlaskForm):
    confirmDel = SubmitField("Confirm Game Deletion")

class NewPlayer(FlaskForm):
    playerName = StringField("Enter player nickname: ")
    comment = StringField("Enter comments: ")
    submitNew = SubmitField("Add Player")
    allPlayers = []

    def __init__(self, allPlayers, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)

        self.allPlayers = allPlayers

    def validate(self):
        if not super().validate():
            return False

        result=True
        titledPlayerName = self.playerName.data.title()  # make sure it is consistent.

        if titledPlayerName in (item[1] for item in self.allPlayers):
            self.playerName.errors.append("Duplicate player name entered - check summary!")
            result = False

        return (result)
        # TO DO: code to check for duplicate names when submitting new player

class SelectPlayerToEdit(FlaskForm):
    oldPlayer = SelectField(u'PlayerName', coerce=int)
    submitEditPlayer = SubmitField("Edit selected Player")

class EditPlayer(FlaskForm):
    playerName = StringField("Enter new player name: ")
    retiree = BooleanField('Retired')
    comment = StringField("Update comments: ")
    submitEdit = SubmitField("Apply Changes")

    def __init__(self, allPlayers, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)

        self.allPlayersExceptMe = allPlayers   # allplayers must be list of all players excluding the player being edited.

    def validate(self):
        if not super().validate():
            return False

        result=True
        titledPlayerName = self.playerName.data.title()  # make sure it is consistent.

        if titledPlayerName in (item[1] for item in self.allPlayersExceptMe):
            self.playerName.errors.append("Duplicate player name entered - check summary!")
            result = False

        return (result)



class RetirePlayer(FlaskForm):
    retirePlayer = SelectField(u'PlayerName', coerce=int)
    submitRetire = SubmitField("Retire")

class ReactivatePlayer(FlaskForm):
    reactivatePlayer = SelectField(u'PlayerName', coerce=int)
    submitReactivate = SubmitField("Reactivate")

class NewTransaction(FlaskForm):
    player = SelectField(u'PlayerName', coerce=int)
    transactionDate = DateField('Transaction Date', [validators.required()])
    amount = FloatField('Amount', [validators.required()])
    type = StringField("Description")
    submitTrans = SubmitField("Add Transaction")

class AutopayforCurrentUser(FlaskForm):
    submitAutoPay = SubmitField("AutoPay")

class CFFASettings(FlaskForm):
    teamName = StringField("Team Name")
    submitTeam = SubmitField("Update Team Name")

class DownloadJSON(FlaskForm):
    submitDownload = SubmitField("Download DB archive")

class UploadJSON(FlaskForm):
    selectArchiveFile = FileField('CFFA Archive File', validators=[FileRequired(),
                                                                   FileAllowed('cffaDB',
                                                                               'CFFA DB exports only!')])
    submitRecovery = SubmitField("Reset and Recover DB")

class addAccess(FlaskForm):
    name = StringField("Name")
    authID = StringField("Auth0 ID")
    type = SelectField(u'UserType', choices=[('Manager', 'Manager'), ('Player', 'Player')])
    submitAddAccess = SubmitField("Add User")

class selectEditUserAccess(FlaskForm):
    editUser = SelectField(u'name', coerce=int)
    submitEditUser = SubmitField("Edit User")

class selectRevokeUserAccess(FlaskForm):
    revokeUser = SelectField(u'name', coerce=int)
    submitRevokeUser = SubmitField("Revoke User")

class EditUserAccess(FlaskForm):
    name = StringField("Name")
    authID = StringField("Auth0 ID")
    type = SelectField(u'UserType', choices=[('Manager', 'Manager'), ('Player', 'Player')])
    revoked = BooleanField('Revoked')
    submitEditUserAccess = SubmitField("Commit changes to user")

class PopulateFromGoogleSheet(FlaskForm):
    googleFile = FileField()
    sheetName = StringField("Google Sheet Document Name")
    transactionSheetName = StringField("Worksheet name with transactions")
    gameSheetName = StringField("Worksheet name with games data")
    summarySheetName = StringField("Worksheet name with summary data")
    summarySheetStartRow = IntegerField("Start row on summary worksheet")
    summarySheetEndRow = IntegerField("End row on summary worksheet")
    submitUpload = SubmitField("Upload google sheet")

def createLabelsForGames(games):
    # games is a list of dicts from DB not a game class
    gameLabels=[]
    customID = 0
    for game in games:
        gameDate = game.get("Date of Game dd-MON-YYYY")
        gameLabel = str(gameDate.year) + "/" + str(gameDate.month) + "/" + str(gameDate.day) + \
                    "," + str(game.get("Players")) + " players, " +\
                    str(game.get("Cost of Game").to_decimal()) + " : " + game.get("PlayerList")
        gameLabels.append( (customID, gameLabel) )
        customID+=1

    return(gameLabels)

def createLabelsForPlayers(players, action):
    playerLabels=[]
    customID = 0
    for player in players:
        if action=="allplayers":
            playerLabels.append( (customID, player.get("playerName")))
        elif action=="retire" and not player.get("retiree", False):
            playerLabels.append((customID, player.get("playerName")))
        elif action=="reactivate" and player.get("retiree", False):
            playerLabels.append((customID, player.get("playerName")))

        customID+=1

    return(playerLabels)


def deleteGameForm(games):
    gameLabels=[]
    customID = 0
    for game in games:
        gameDate = game.get("Date of Game dd-MON-YYYY")
        gameLabel = str(gameDate.year) + "/" + str(gameDate.month) + "/" + str(gameDate.day) + \
                    "," + str(game.get("Players")) + " players, " +\
                    str(game.get("Cost of Game").to_decimal()) + " : " + game.get("PlayerList")
        gameLabels.append( ( customID, gameLabel) )
        customID+=1

    form = DeleteGameSelectForm(obj=gameLabels)
    form.game.choices = gameLabels
    return (form)

def gameFormToFootball(form):

    newGamePlayers = []

    for player in form.playerList:
        newplayer = footballClasses.Player(player.id,
                                           player.playerName.data,
                                           player.playedLastGame.data,
                                           player.pitchBooker.data,
                                           player.guests.data)
        newGamePlayers.append(newplayer)

        if player.pitchBooker.data == True:
            theBooker = player.playerName.data

    newGame = footballClasses.Game(form.gameCost.data, form.gameDate.data, newGamePlayers, theBooker)

    return(newGame)


def newPlayerFormToFootball(form):

    newplayer = footballClasses.TeamPlayer(form.playerName.data,
                                           False,
                                           form.comment.data)

    return(newplayer)

def editPlayerFormToFootball(form):
    player = footballClasses.TeamPlayer(form.playerName.data, form.retiree.data, form.comment.data)
    return(player)


def newTransactionFormToFootball(form, player):
    titledPlayer = player.title()
    transaction = footballClasses.Transaction(titledPlayer,
                                              form.type.data,
                                              form.amount.data,
                                              form.transactionDate.data)
    return(transaction)

def createLabelsForUsers(users):
    userLabels=[]
    customID = 0
    for user in users:
        userLabels.append( (customID, user.name) )
        customID+=1

    return(userLabels)

def editUserAccessFormToFootball(form):
    user = footballClasses.CFFAUser(form.name.data, form.authID.data, form.type.data, form.revoked.data)
    return(user)