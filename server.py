""" CFFA server V0.2. Casual Football Finance Manager with multi-tenancy project

This code file contains all endpoints for the CFFA flask web service. It requires the cffadb library integrate with a mongoDB
bckend. Authentication is integrated with the Auth0 authentication service. Execute this code file with Flask / gunicorn.

The application uses port 5000.

Environment Variables
---------------------

AUTH0_CLIENT_ID=[as provided by Auth0 for this application]
AUTH0_DOMAIN=[as provided by Auth0]
AUTH0_CLIENT_SECRET=[as provided by Auth0 for this application]
AUTH0_CALLBACK_URL=https://yourwebsite.com:port/callback
AUTH0_AUDIENCE=https://[as advised by Auth0]]/userinfo

BACKEND_DBPWD=[mongpDB backend DB password]
BACKEND_DBUSR=[mongoDB backend username for football DB]
BACKEND_DBHOST=[IP address/hostnames of mongoDB server/s]
BACKEND_DBPORT=[Port number for MongoDB]
BACKEND_DBNAME=[Database name, such as footballDB]

SECRET_KEY=[used for CSRF/session encryption protection in forms with flask ]
PYTHONPATH=[should include link to cffadb, altough some debate better methods could be used]
EXPORTDIRECTORY=[Directory to use to build databasee json exports]

GOOGLEKEYFILE=[Only used by testScript.py as keyfile is now uploaded server side]
GOOGLE_SHEET=[Only used by testScript.py as gsheet name is set via cffa webpage]
TRANSACTION_SRC_WKSHEET=[Only used by testScript.py as worksheet name is set via cffa webpage]
GAME_SRC_WKSHEET=[Only used by testScript.py as worksheet name is set via cffa webpage]
CFFA_USERID=[Only used by testScript.py to configure DB database from gsheet]
SUMMARY_SRC_WKSHEET=[Only used by testScript.py as worksheet name is set via cffa webpage]

Example
-------

A)

export PYTHONPATH=<path to cffa>:<path to cffa db>
export FLASK_APP=server.py ; export FLASK_ENV=development
flask run --host 0.0.0.0 --cert your_cert.pem --key your_key.pem

-- This will respond to any clients and supports SSL using either an approved or self-signed certificate in development
mode. Do not use development mode in Production.

B)

#!/bin/bash
source venv/bin/activate
exec gunicorn -b :5000 --certfile=cffa-signed.crt \
--keyfile=/cffa-signed.key --access-logfile - --error-logfile - -w 1 server:app

Starts production class CFFA on port 5000 with logs to stdout with signed certificates. Would typically be used alongside
a nginx reverse proxy to redirect https to port 5000. (ngninx does not decript https in this case as Auth0 authenticates
with flask not nginx.

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
import importDataFromGoogle
import autometadata_handler
from werkzeug.utils import secure_filename

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
    """ Derived from Auth0 python example for single web pages. Handles authentication errors.

     """
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
    """ Derived from Auth0 python example for single web pages. Wrapper for each entry point to ensure user is
    authenticated.

     """
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated

def requires_managerRole(f):
    """ Additional wrap to ensure that only manager role CFFA users can access the endpoint.
     """
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
    """ Derived from Auth0 python example for single web pages. Provides a log in button before being shown the login
    AUth0 dialog, or if already authenticated, the entryScreen endpoint.

     """
    return render_template('home.html')


@app.route('/callback')
def callback_handling():
    """ Derived from Auth0 python example for single web pages. Setting up session variables prior to redirection
    to home screen (entryScreen)

     """
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
    """ Derived from Auth0 python example for single web pages. Shows usual Auth0 login dialog.
     """
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)


@app.route('/logout')
def logout():
    """ Derived from Auth0 python example for single web pages. Logs out AUth0 user.
     """
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/dashboard')
@requires_auth
def dashboard():
    """ Derived from Auth0 python example for single web pages. Not used.
     """
    return render_template('dashboard.html',
                           userinfo=session[constants.PROFILE_KEY],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))

@app.route('/favicon.ico')
def favicon():
    """ Added to provide favicon file as highlighted when using chrome/safari debugger.
    """
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/cffa')
@requires_auth
@requires_managerRole
def entryScreen():
    """ Main screen for manager. If user collections do not exist assuems new user and redirects to onboarding screen.
     """
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
@requires_managerRole
def onboarding():
    """Onboarding screen to prompt for team name for new managers.
    """
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
@requires_managerRole
def manageGames():
    """ Functionality to manage games - add, edit, remove. The logic handles the response when adding a new game, but
    edit and delete game are redirected to their endpoints via the form action setting in the manageGames.html template.
    """
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
@requires_managerRole
def newGame(players):
    """ Renders and processings the new game form.

    Parameters
    ----------

    players : int
        Number of players that played in the new game. Used in form validation.
    """

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
@requires_managerRole
def editGame():
    """  Processes edit game select form (ie: which game to edit).
    """
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
    """  Processes edit game form rendering and form input processing. Unlike new game form this does not check the
    number of players selected.

        choice : int
        Index to selected game (in list obtained from getAllgames(). Possible flaw if another user adds a new game for
        te same team whilst in this workflow. (edge case)

    """
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
@requires_managerRole
def deleteGame():
    """  Processes delete game select form (ie: which game to delete). As it has been redirected from a completed
    form we should not get to the end of the function unless there are no games.
 TO DO: Probably can delete the edit game form logic below.
    """

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
@requires_managerRole
def applyDeleteGame(choice):
    """  Processes delete game form rendering and form input processing.

        choice : int
        Index to selected game (in list obtained from getAllGames(). Possible flaw if another user adds a new game for
        te same team whilst in this workflow. (edge case)

    """
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
@requires_managerRole
def managePlayers():
    """ Functionality to manage players - add, edit, retire and reactivate. The logic handles the response when adding a new player, but
    edit, retire and reactivate players  are redirected to their endpoints via the form action setting in the managePlayers.html template.
    """
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
@requires_managerRole
def editSelectPlayer():
    """  Processes edit player select form (ie: which player to edit) and then redirects to edit player endpoint. Form
    should always validate as endpoint is a post redirect from the managePlayers page.

    TO DO: Remove GET method from function.
    """
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
@requires_managerRole
def editPlayer(player):
    """  Renders and post processes the edit player form for the selected player.

        player : int
        Index to selected player (in list obtained from createLabelsForPlayers() and removes selected player from list.
        This is for validation to prevent a player name duplicate occurring during edit.

    """
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
@requires_managerRole
def retirePlayer():
    """  Processes retire player select form (ie: which player to retire). Form
    should always validate as endpoint is a post redirect from the managePlayers page.

    TO DO: Remove GET method from function.
    """
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
@requires_managerRole
def reactivatePlayer():
    """  Processes reactivate (from retirement) player select form (ie: which player to reactivate). Form
    should always validate as endpoint is a post redirect from the managePlayers page.

    TO DO: Remove GET method from function.
    """
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
@requires_managerRole
def manageTransactions():
    """ Functionality to manage transactions - add, edit, and show all. The logic handles the response when adding a new
    transaction, but edit and list transactions are redirected to their endpoints via the form action setting in the
    manageTransactions.html template. Note there is no functionality to remove transactions so any user errors require
    additional transactions to adjust.

    """
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
@requires_managerRole
def autoPay():
    """  Processes thw autopay logic to automatically credit the manager (logged in user) with the value of the
     last played game. Form should always validate as endpoint is a post redirect from the manageTransactions page.

    TO DO: Remove GET method from function.
    TO DO: Stop multiple actions for the same game to avoid accidental usage.
    """
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
@requires_managerRole
def manageSettings():
    """ Functionality to manage settings and similiar b adehavour including edit team name, export and import data, import
     google sheet data and reset DB.  The logic handles the response when changing the team name  but the other actions
     are redirected to their endpoints via the form action setting in the
    manageSettings.html template. Note that import from json is not implemented yet.

    """
    # edit team name, export and import db json for all collections\
    app.logger.debug("Got to manageSettings()")
    ourSettings = ourDB.getAppSettings()
    settingsChangeForm = formHandler.CFFASettings(obj=ourSettings)
    dbExportForm = formHandler.DownloadJSON()  # just a submit button to redirect to url
    dbRecoveryForm = formHandler.UploadJSON()
    googleUploadForm = formHandler.PopulateFromGoogleSheet()
    deleteAllForm = formHandler.DeleteAll()

    if settingsChangeForm.validate_on_submit():
        flashMessage = ourDB.updateTeamName(settingsChangeForm.teamName.data, session[constants.PROFILE_KEY].get('user_id', None))
        flash(flashMessage)
        return redirect(url_for('entryScreen'))

    return render_template("manageSettings.html",
                           settingsChangeForm=settingsChangeForm,
                           dbExportForm=dbExportForm,
                           dbRecoveryForm=dbRecoveryForm,
                           dbImportGsheetForm=googleUploadForm,
                           deleteAllForm=deleteAllForm,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/downloadjson', methods=['GET', 'POST'])
@requires_auth
@requires_managerRole
def downloadJSON():
    """  Processes download of the DB in json format.  Form
    should always validate as endpoint is a post redirect from the manageSettings page.

    TO DO: Remove GET method from function.
    """
    app.logger.debug(" we got to downloadJSON")
    # call to extract all tables as json and place into zip to download via sendfile
    filename = fileManager.exportarchive()
    return send_file(filename,
                     mimetype='application/zip',
                     as_attachment=True)   # tell client  not to view file but download


@app.route('/uploadjson', methods=['GET', 'POST'])
@requires_auth
@requires_managerRole
def uploadJSON():
    """  Processes upload of the DB in json format.

    TO DO: Implement. The False return value will generate an error.
    """
    app.logger.debug("We got to uploadJSON()")
    return(False)

@app.route('/uploadGoogleConnector', methods=['GET', 'POST'])
@requires_auth
@requires_managerRole
def uploadGoogleConnector():
    """  Processes the completed google import form. Form
    should always validate as endpoint is a post redirect from the manageSettings page.

    TO DO: Remove GET method from function.
    TO DO: Better error handling.
    """
    app.logger.debug("We got to uploadGoogleConnector()")

    googleUploadForm = formHandler.PopulateFromGoogleSheet()
    if googleUploadForm.validate_on_submit():
        filename = secure_filename(googleUploadForm.googleFile.data.filename)
        googleUploadForm.googleFile.data.save('uploads/' + filename)
        googleConnector = importDataFromGoogle.GoogleImporter(ourDB,
                                                              "uploads/"+filename,
                                                              googleUploadForm.sheetName.data,
                                                              googleUploadForm.transactionSheetName.data,
                                                              googleUploadForm.gameSheetName.data,
                                                              googleUploadForm.summarySheetName.data,
                                                              googleUploadForm.summarySheetStartRow.data,
                                                              googleUploadForm.summarySheetEndRow.data)

        flashMessage = googleConnector.downloadData()
        flash(flashMessage)
        return redirect(url_for('entryScreen'))


    # should not get here
    app.logger.critical("Managed to get past validate on uploadGoogleCollector(). Unexpected")
    return(False)


@app.route('/deleteAll', methods=['GET', 'POST'])
@requires_auth
@requires_managerRole
def deleteAllData():
    """  Processes the DB deletion. Form
    should always validate as endpoint is a post redirect from the manageSettings page.

    TO DO: Remove GET method from function.
    TO DO: Logic should drop the tenancy table but only the rows for the user's tenancy. Current behaviour aids
    complete reset of DB and debugging/test cases.
    """
    app.logger.warning("Entered deleteAllData() - about to reset DB")
    deleteAllForm = formHandler.DeleteAll()
    if deleteAllForm.validate_on_submit():
        app.logger.warning("Deleting database")
        message = ourDB.dropAllCollections(session[constants.PROFILE_KEY].get('user_id', None))
        flash(message)
        return redirect(url_for('entryScreen'))

    # should not get here
    app.logger.critical("Managed to get past validate on deleteAllData(). Unexpected")
    return(False)


@app.route('/manageUserAccess', methods=['GET', 'POST'])
@requires_auth
@requires_managerRole
def manageUserAccess():
    """ Functionality to manage user access including adding users and editing users. The logic handles the response
    when adding a new user but editing user is redirected to that endpoint via the form action setting in the
    manageUserAccess.html template.

    """
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
@requires_managerRole
def editSelectUser():
    """  Renders and processes the edit User form for user access. Form
    should always validate as endpoint is a post redirect from the manageUserAccess page.

    TO DO: Remove GET method from function.
    TO DO: There is no validation in the forms for duplicate user names/IDs etc
    Big TO DO: Ideally integrate with a service that provides Auth0 functionality to obtain Auth0 IDs based on name/
    email address etc.
    """
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
@requires_managerRole
def editUserAccess(user):
    """  Renders and post processes the edit user access  form for the selected user.

        player : int
        Index to selected user (in list obtained from getUserAccessData().

        Note: TO DO: No logic yet implemented to handle duplicate names in edit form.

    """
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
    """  Processes the page for player role users. This offers no form functionality but summary data of their accounts,
    game activity and other stats. Also provides a bank statement style transaction view since they started playing.

    """
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

