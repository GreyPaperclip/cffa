""" CFFA application V0.1. Casual Football Finance Manager with multi-tenancy project
"""
from functools import wraps
import json
from os import environ as env
import os
from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, redirect, render_template, session, url_for, flash, send_file, send_from_directory
from flask import request
from flask_bootstrap import Bootstrap
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

import formHandler
from formHandler import csrf
import importExportCFFA
import logging
from logging.handlers import RotatingFileHandler
import constants
import pprint
pp = pprint.PrettyPrinter()

from cffadb import dbinterface
import importExportCFFA
import autometadata_handler

app = Flask(__name__, static_url_path='/static', static_folder='./static')
app.secret_key = constants.SECRET_KEY
app.debug = True
csrf.init_app(app)
bootstrap = Bootstrap(app)


if not os.path.exists('logs'):
        os.mkdir('logs')
file_handler = RotatingFileHandler('logs/cffa_webserver.log', maxBytes=1024000,
                                       backupCount=10000)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('CFFA webserver startup')


ENV_FILE = find_dotenv()
if ENV_FILE:
    app.logger.info('Found .env file ')
    load_dotenv(ENV_FILE)

AUTH0_CALLBACK_URL = env.get(constants.AUTH0_CALLBACK_URL)
AUTH0_CLIENT_ID = env.get(constants.AUTH0_CLIENT_ID)
AUTH0_CLIENT_SECRET = env.get(constants.AUTH0_CLIENT_SECRET)
AUTH0_DOMAIN = env.get(constants.AUTH0_DOMAIN)
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = env.get(constants.AUTH0_AUDIENCE)

BACKEND_DBUSR = env.get(constants.BACKEND_DBUSR)
BACKEND_DBPWD = env.get(constants.BACKEND_DBPWD)
BACKEND_DBHOST = env.get(constants.BACKEND_DBHOST)
BACKEND_DBPORT = env.get(constants.BACKEND_DBPORT)
BACKEND_DBNAME = env.get(constants.BACKEND_DBNAME)
mongoConnectString = "mongodb://" + BACKEND_DBUSR + ":" + BACKEND_DBPWD + "@" + BACKEND_DBHOST + ":" + BACKEND_DBPORT + "/" + BACKEND_DBNAME

try:
    ourDB = dbinterface.FootballDB(mongoConnectString, BACKEND_DBNAME)
    EXPORT_DIR = env.get(constants.EXPORTDIRECTORY)
    app.logger.info("Export Dir is:" + EXPORT_DIR)
    fileManager = importExportCFFA.CFFAImportExport(ourDB, EXPORT_DIR)
except Exception as e:
    app.logger.critical("ABORT. CFFA initialisation with DB failed with " + mongoConnectString + ". " + getattr(e, 'message', repr(e)))
    exit(-1)




@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response


oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated

def requires_managerRole(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        userID = session[constants.PROFILE_KEY].get('user_id')
        playerConfirmed = ourDB.validateUserAsPlayerRole(userID)
        if playerConfirmed == True:
            return redirect('/playerSummary')

        return f(*args, **kwargs)

    return decorated


# Controllers API
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture'],
    }
    return redirect('/cffa')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)


@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session[constants.PROFILE_KEY],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/cffa')
@requires_auth
@requires_managerRole
def entryScreen():
    # from username lets check tenancy. Use metadata in Auth0 for userID. This will be unique.
    if ourDB.loadTeamTablesForUserId(session[constants.PROFILE_KEY].get('user_id', None)) == False:
        # new manager entry point, redirect to onboarding wizard
        return(redirect(url_for('onboarding')))

    app.logger.debug('Rendering entryScreen.html')
    return render_template("entryScreen.html",
                           playerSummaries = ourDB.getActivePlayerSummary(),
                           allPlayers = ourDB.getFullSummary(),
                           recentGames = ourDB.getRecentGames(),
                           allGames = ourDB.getAllGames(),
                           transactions = ourDB.getRecentTransactions(),
                           cffauser=session[constants.PROFILE_KEY].get('name'))

@app.route('/onboarding', methods=['GET', 'POST'])
@requires_auth
def onboarding():
    # display welcome screen and prompt user to create a new team name.
    app.logger.debug("Entering onboarding")
    addTeamForm = formHandler.AddTeam(ourDB.getListofAllTenantNames())

    if addTeamForm.validate_on_submit():
        # before adding team, if this is a new user auth0 metadata is not set -
        if session[constants.PROFILE_KEY].get('user_id', None) == None:
            # fatal, every login from auth0 will have user_id set.
            logger.critical("No user_id set in authenticator, cannot onboard")
            message="No user_id set in authenticator. Cannot on-board this user"
        else:
            message = ourDB.addTeam(addTeamForm.teamName.data,
                                session[constants.PROFILE_KEY].get('user_id', None),
                                session[constants.PROFILE_KEY].get('name'))

        flash(message)
        # when switching back to entryScreen we will end up switching the db collections to the tenant

        return(redirect(url_for('entryScreen')))

    return render_template("newTeam.html",
                           addTeamForm = addTeamForm,
                           cffauser=session[constants.PROFILE_KEY].get('name'))



@app.route('/games', methods=['GET', 'POST'])
@requires_auth
def manageGames():
    # add game; edit game; delete game; dump games
    # handle guests too
    app.logger.debug('Rendering manageGames')
    noPlayersForm = formHandler.AddGame_NoPlayers()
    games = ourDB.getAllGames()
    gameLabels = formHandler.createLabelsForGames(games)
    editGameForm = formHandler.EditGameSelectForm()
    editGameForm.game.choices = gameLabels
    deleteGameForm = formHandler.DeleteGameSelectForm()
    deleteGameForm.game.choices = gameLabels

    #if noPlayersForm.validate_on_submit():
    if noPlayersForm.submit.data and noPlayersForm.validate():
        redirectToNewGame = url_for('newGame', players=noPlayersForm.noPlayers.data)
        return redirect(redirectToNewGame)

    return render_template("manageGames.html",
                           allGames=ourDB.getAllGames(),
                           form=noPlayersForm,
                           editGameform=editGameForm,
                           deleteGameform=deleteGameForm,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/newgame/<int:players>', methods=['GET','POST'])
@requires_auth
def newGame(players):
    app.logger.debug('Rendering newgame with players' + str(players))
    booker = session[constants.PROFILE_KEY].get('name')
    newGameDefaults = ourDB.getDefaultsForNewGame(booker)
    noPlayersForm = formHandler.GameDetails(players, obj=newGameDefaults)
    if ourDB.newManager():
        flash("TIP: When adding a game, a player will be created if it doesn't already exist")

    if noPlayersForm.validate_on_submit():
        ourDB.addGame(formHandler.gameFormToFootball(noPlayersForm))
        flash("Game on {} for {} players has been added".format(noPlayersForm.gameDate.data,
                                                                        players))
        return redirect(url_for('entryScreen'))

    return render_template("newGame.html", noOfPlayers=players,
                           form=noPlayersForm,
                          activePlayerList = ourDB.getActivePlayersForNewGame(),
                           cffauser=session[constants.PROFILE_KEY].get('name')
                           )

@app.route('/editgame', methods=['POST'])
@requires_auth
def editGame():
    games = ourDB.getAllGames()
    gameLabels = formHandler.createLabelsForGames(games)
    selectGameForm = formHandler.EditGameSelectForm()
    selectGameForm.game.choices = gameLabels
    deleteGameForm = formHandler.DeleteGameSelectForm()

    app.logger.debug("Got into editGame" + str(selectGameForm))

    if selectGameForm.validate_on_submit():
        choice = selectGameForm.game.data
        app.logger.debug("choice was" + str(choice))
        return redirect(url_for('applyEditGame', choice=choice))

    # we should not get here as this is always called with a POST request for edit via manageGames.
    app.logger.warning("Should not get here in editGame without a successful POST entry condition. Or rather there are no games in DB!")
    flash("Unable to edit selected game")
    return redirect(url_for('entryScreen'))


@app.route('/applyEditGame/<int:choice>', methods=['GET', 'POST'])
@requires_auth
def applyEditGame(choice):
    app.logger.debug("Entering applyEditGame()")
    games = ourDB.getAllGames()
    editGameDetails = ourDB.getGameDetailsForEditDeleteForm(games[choice].get("_id"), True)
    players = 0  # 0 = supresses the validation logic for number of players selected in form.
    editPlayersForm = formHandler.GameDetails(players, obj=editGameDetails)

    # need to check form itself and set players based on checked players in submitted form before validation

    if editPlayersForm.validate_on_submit():
        flash("Game on date {} has been edited".format(editPlayersForm.gameDate.data))
        ourDB.editGame(games[choice].get("_id"), formHandler.gameFormToFootball(editPlayersForm))
        return redirect(url_for('entryScreen'))

    return render_template("editGame.html",
                           form=editPlayersForm
                           )



@app.route('/deletegame', methods=['POST'])
@requires_auth
def deleteGame():
    app.logger.debug("Entering deletegame")
    games = ourDB.getAllGames()
    gameLabels = formHandler.createLabelsForGames(games)
    selectGameForm = formHandler.EditGameSelectForm()
    selectGameForm.game.choices = gameLabels
    deleteGameForm = formHandler.DeleteGameSelectForm()
    deleteGameForm.game.choices = gameLabels

    if deleteGameForm.validate_on_submit():
        choice = deleteGameForm.game.data
        app.logger.debug("delete choice was" + str(choice))
        return redirect(url_for('applyDeleteGame', choice=choice))

    app.logger.warning("Should not get here in deleteGame without a successful POST entry condition. Or rather there are no games in DB!")
    flash("Unable to delete selected game")
    return redirect(url_for('entryScreen'))

@app.route('/applyDeletegame/<int:choice>', methods=['GET', 'POST'])
@requires_auth
def applyDeleteGame(choice):
    app.logger.debug("Entering applyDeleteGame")
    games = ourDB.getAllGames()
    dbid = games[choice].get("_id")
    deleteGameDetails = ourDB.getGameDetailsForEditDeleteForm(dbid, False)
    deleteConfirmationForm = formHandler.ConfirmDelete()
    if deleteConfirmationForm.validate_on_submit():
        flash("Submitting deletion request:", format(deleteGameDetails.gameDate))
        flashMessage = ourDB.deleteGame(dbid)
        flash(flashMessage)
        return redirect(url_for('entryScreen'))

    return render_template("deleteGame.html",
                           form=deleteConfirmationForm,
                           gamedetails=deleteGameDetails,
                           cffauser=session[constants.PROFILE_KEY].get('name'))



@app.route('/players', methods=['GET', 'POST'])
@requires_auth
def managePlayers():
    # add player, edit player, cannot delete player if they have played a game
    # dump players
    app.logger.debug("Entering managePlayers()")
    allPlayers = ourDB.getAllPlayerDetailsForPlayerEdit()  # in obj classes
    addPlayerForm = formHandler.NewPlayer(formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="allplayers"))
    editPlayerForm = formHandler.SelectPlayerToEdit(obj=allPlayers)
    editPlayerForm.oldPlayer.choices=formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="allplayers")
    retirePlayerForm = formHandler.RetirePlayer()
    retirePlayerForm.retirePlayer.choices=formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="retire")
    reactivatePlayerForm = formHandler.ReactivatePlayer()
    reactivatePlayerForm.reactivatePlayer.choices=formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="reactivate")

    if addPlayerForm.validate_on_submit():
        flashMessage = ourDB.addPlayer(formHandler.newPlayerFormToFootball(addPlayerForm))
        flash(flashMessage)
        return redirect(url_for('entryScreen'))

    return render_template("managePlayers.html",
                           addPlayerForm=addPlayerForm,
                           editPlayerForm=editPlayerForm,
                           retirePlayerForm=retirePlayerForm,
                           reactivatePlayerForm=reactivatePlayerForm,
                           cffauser=session[constants.PROFILE_KEY].get('name'))

@app.route('/editSelectPlayer', methods=['GET', 'POST'])
@requires_auth
def editSelectPlayer():
    app.logger.debug("We got to editSelectPlayer")
    allPlayers = ourDB.getAllPlayerDetailsForPlayerEdit()  # in obj classes
    playerList = formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="allplayers")
    editPlayerForm = formHandler.SelectPlayerToEdit(obj=allPlayers)
    editPlayerForm.oldPlayer.choices=playerList

    if editPlayerForm.validate_on_submit():
        # only got the player to edit, now redirect to
        return redirect(url_for('editPlayer', player=editPlayerForm.oldPlayer.data))

    # we should never get here
    app.logger.info(" We should not get to this part of editSelectPlayer")
    return(False)


@app.route('/editPlayer/<int:player>', methods=['GET', 'POST'])
@requires_auth
def editPlayer(player):
    app.logger.debug('Entering editPlayer')
    playerList = formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="allplayers")
    ourPlayers = dict(playerList)
    playerDefaults = ourDB.getPlayerDefaultsForEdit(ourPlayers.get(player))
    # remove own player name from playerList for validation
    playerList.pop(player)
    editPlayerForm = formHandler.EditPlayer(playerList, obj=playerDefaults)

    if editPlayerForm.validate_on_submit():
        message = ourDB.editPlayer(ourPlayers.get(player), formHandler.editPlayerFormToFootball(editPlayerForm))
        flash(message)
        return redirect(url_for('entryScreen'))

    return render_template("editPlayer.html",
                           editPlayerForm=editPlayerForm)



@app.route('/retirePlayer', methods=['GET', 'POST'])
@requires_auth
def retirePlayer():
    app.logger.debug('We got to retire player')
    allPlayers = ourDB.getAllPlayerDetailsForPlayerEdit()  # in obj classes
    playerList = formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="retire")
    retirePlayerForm = formHandler.RetirePlayer()
    retirePlayerForm.retirePlayer.choices=playerList

    if retirePlayerForm.validate_on_submit():
        ourPlayers = dict(playerList)
        flashMessage = ourDB.retirePlayer(ourPlayers.get(retirePlayerForm.retirePlayer.data))
        flash(flashMessage)
        return redirect(url_for('entryScreen'))

    # TO DO we should never get here as this should only be called with a POST
    app.logger.info(" Should not get this far in retirePlayer() unless there are no players to Retire")
    flash("Unable to retire the selected player")
    return redirect(url_for('entryScreen'))


@app.route('/reactivatePlayer', methods=['GET', 'POST'])
@requires_auth
def reactivatePlayer():
    app.logger.debug('We got to reactivate player')
    playerList = formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="reactivate")
    reactivatePlayerForm = formHandler.ReactivatePlayer()
    reactivatePlayerForm.reactivatePlayer.choices=playerList

    if reactivatePlayerForm.validate_on_submit():
        ourPlayers = dict(playerList)
        flashMessage = ourDB.reactivatePlayer(ourPlayers.get(reactivatePlayerForm.reactivatePlayer.data))
        flash(flashMessage)
        return redirect(url_for('entryScreen'))

    # TO DO we should never get here as this should only be called with a POST
    app.logger.info(" Should not get this far in reactivatePlayer() unless there are no players available to reactivate")
    flash("Unable to reactivate the selected player")
    return redirect(url_for('entryScreen'))


@app.route('/transactions', methods=['GET', 'POST'])
@requires_auth
def manageTransactions():
    # add payment, edit payment, remove payment, autopayquick, view all transactions
    # needs to sort on transaction from recent first.
    app.logger.debug('We got to transactions()')
    transactionDefaults = ourDB.getDefaultsForTransactionForm(session[constants.PROFILE_KEY].get('name'))
    addTransactionForm = formHandler.NewTransaction(obj=transactionDefaults)
    addTransactionForm.player.choices=formHandler.createLabelsForPlayers(ourDB.getAllPlayers(), action="allplayers")
    quickAutoPayForm = formHandler.AutopayforCurrentUser()

    if addTransactionForm.validate_on_submit():
        playerList = dict(addTransactionForm.player.choices)
        flashMessage = ourDB.addTransaction(formHandler.newTransactionFormToFootball(addTransactionForm,
                                                                                     playerList.get(addTransactionForm.player.data, None)))
        flash(flashMessage)
        return redirect(url_for('manageTransactions'))

    return render_template("manageTransactions.html",
                           addTransactionForm=addTransactionForm,
                           quickAutoPayForm=quickAutoPayForm,
                           autoPayDetails=ourDB.getAutoPayDetails(session[constants.PROFILE_KEY].get('name')),
                           allTransactions=ourDB.getAllTransactions(),
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/autoPay', methods=['GET', 'POST'])
@requires_auth
def autoPay():
    app.logger.info('Got to autoPay()')
    quickAutoPayForm = formHandler.AutopayforCurrentUser()

    if quickAutoPayForm.validate_on_submit():
        flashMessage = ourDB.addTransaction(ourDB.getAutoPayDetails(session[constants.PROFILE_KEY].get('name')))
        flash(flashMessage)
        return redirect(url_for('manageTransactions'))

    app.logger.debug("Should not get here in autoPay logic unless autopay is pressed without any previous game")
    flash("Unable to autopay - was there any previous games played?")
    return redirect(url_for('entryScreen'))

@app.route('/settings', methods=['GET', 'POST'])
@requires_auth
def manageSettings():
    # edit team name, export and import db json for all collections\
    app.logger.debug("Got to manageSettings()")
    ourSettings = ourDB.getAppSettings()
    settingsChangeForm = formHandler.CFFASettings(obj=ourSettings)
    dbExportForm = formHandler.DownloadJSON()  # just a submit button to redirect to url
    dbRecoveryForm = formHandler.UploadJSON()

    if settingsChangeForm.validate_on_submit():
        flashMessage = ourDB.updateTeamName(settingsChangeForm.teamName.data, session[constants.PROFILE_KEY].get('user_id', None))
        flash(flashMessage)
        return redirect(url_for('entryScreen'))

    return render_template("manageSettings.html",
                           settingsChangeForm=settingsChangeForm,
                           dbExportForm=dbExportForm,
                           dbRecoveryForm=dbRecoveryForm,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/downloadjson', methods=['GET', 'POST'])
@requires_auth
def downloadJSON():
    app.logger.debug(" we got to downloadJSON")
    # call to extract all tables as json and place into zip to download via sendfile
    filename = fileManager.exportarchive()
    return send_file(filename,
                     mimetype='application/zip',
                     as_attachment=True)   # tell client  not to view file but download


@app.route('/uploadjson', methods=['GET', 'POST'])
@requires_auth
def uploadJSON():
    app.logger.debug("We got to uploadJSON()")
    return(False)


@app.route('/manageUserAccess', methods=['GET', 'POST'])
@requires_auth
def manageUserAccess():
    app.logger.debug("Got to manageUserAccess()")
    userAccessData = ourDB.getUserAccessData(session[constants.PROFILE_KEY].get('user_id', None))
    addAccessForm = formHandler.addAccess()
    selectEditUserAccessForm = formHandler.selectEditUserAccess(obj=userAccessData)
    selectEditUserAccessForm.editUser.choices = formHandler.createLabelsForUsers(userAccessData)

    # selectEditUserAccessForm and selectRevokeUserAccessForm redirect to different urls
    if addAccessForm.validate_on_submit():
        flashMessage = ourDB.addUserAccess(addAccessForm.name.data,
                                           addAccessForm.authID.data,
                                           addAccessForm.type.data,
                                           session[constants.PROFILE_KEY].get('user_id', None))
        flash(flashMessage)
        return redirect(url_for('manageUserAccess'))

    return render_template("manageUserAccess.html",
                           Users=userAccessData,
                           addAccessForm=addAccessForm,
                           editUserForm=selectEditUserAccessForm,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/editSelectUser', methods=['GET', 'POST'])
@requires_auth
def editSelectUser():
    app.logger.debug("Got to editSelectUser()")
    userAccessData = ourDB.getUserAccessData(session[constants.PROFILE_KEY].get('user_id', None))
    addAccessForm = formHandler.addAccess()
    selectEditUserAccessForm = formHandler.selectEditUserAccess(obj=userAccessData)
    selectEditUserAccessForm.editUser.choices = formHandler.createLabelsForUsers(userAccessData)

    if selectEditUserAccessForm.validate_on_submit():
        # only got the player to edit, now redirect to
        return redirect(url_for('editUserAccess', user=selectEditUserAccessForm.editUser.data))

    # we should never get here
    app.logger.info(" We should not get to this part of editSelectUser")
    return(None)

@app.route('/editUserAccess/<int:user>', methods=['GET', 'POST'])
@requires_auth
def editUserAccess(user):
    app.logger.debug('Entering editUserAccess')
    userAccessData = ourDB.getUserAccessData(session[constants.PROFILE_KEY].get('user_id', None))
    #ourUsers = dict(userAccessData)  # so we can turn index numbers into keys
    # userData = ourDB.getUserAccessDefaultsForEdit(ourUsers.get(user))
    userData = userAccessData[user] # should return footballClasses user object

    editUserAccessForm = formHandler.EditUserAccess(obj=userData)

    if editUserAccessForm.validate_on_submit():
        message = ourDB.editUserAccess (userData.name, formHandler.editUserAccessFormToFootball(editUserAccessForm))
        flash(message)
        return redirect(url_for('manageUserAccess'))

    return render_template("editUserAccess.html",
                           editUserForm=editUserAccessForm)


@app.route('/playerSummary')
@requires_auth
def playerSummaryOnly():
    if ourDB.loadTeamTablesForUserId(session[constants.PROFILE_KEY].get('user_id', None)) == False:
        # this should not happen as this redirect page only occurs if the user_id exists already and is marked as a player.
        # as safety lets redirect to logout!
        logger.critical("User has gone to player Summary without valid userID")
        return(redirect(url_for('logout')))

    app.logger.debug('Rendering playerSummary.html')
    return render_template("playerSummary.html",
                           summary = ourDB.getSummaryForPlayer(session[constants.PROFILE_KEY].get('name', None)),
                           ledger = ourDB.calcLedgerForPlayer(session[constants.PROFILE_KEY].get('name', None)),
                           recentGames = ourDB.getGamesForPlayer(session[constants.PROFILE_KEY].get('name', None)),
                           cffauser=session[constants.PROFILE_KEY].get('name'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=env.get('PORT', 5000))

