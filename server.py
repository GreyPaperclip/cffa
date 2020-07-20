""" CFFA server V0.2. Casual Football Finance Manager with multi-tenancy project

This code file contains all endpoints for the CFFA flask web service. It requires the cffadb library integrate with a
mongoDB backend. Authentication is integrated with the Auth0 authentication service. Execute this code file with
Flask / gunicorn.

The application uses port 5000.

Environment Variables
---------------------

AUTH0_CLIENT_ID=[as provided by Auth0 for this application]
AUTH0_DOMAIN=[as provided by Auth0]
AUTH0_CLIENT_SECRET=[as provided by Auth0 for this application]
AUTH0_CALLBACK_URL=https://yourwebsite.com:port/callback
AUTH0_AUDIENCE=https://[as advised by Auth0]]/userinfo

BACKEND_DBPWD=[mongoDB backend DB password]
BACKEND_DBUSR=[mongoDB backend username for football DB]
BACKEND_DBHOST=[IP address/hostnames of mongoDB server/s]
BACKEND_DBPORT=[Port number for MongoDB]
BACKEND_DBNAME=[Database name, such as footballDB]

SECRET_KEY=[used for CSRF/session encryption protection in forms with flask ]
PYTHONPATH=[should include link to cffadb, altough some debate better methods could be used]
EXPORTDIRECTORY=[Directory to use to build database json exports]

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

-- This will respond to any clients and supports SSL using either an approved or self-signed certificate in
development mode. Do not use development mode in Production.

B)

#!/bin/bash
source venv/bin/activate
exec gunicorn -b :5000 --certfile=cffa-signed.crt \
--keyfile=/cffa-signed.key --access-logfile - --error-logfile - -w 1 server:app

Starts production class CFFA on port 5000 with logs to stdout with signed certificates. Would typically be used
alongside a nginx reverse proxy to redirect https to port 5000. (ngninx does not decrypt https in this case as
Auth0 authenticates with flask not nginx.

"""
from functools import wraps
import json
from os import environ as env
import os
from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, redirect, render_template, session, url_for, flash, send_file, send_from_directory
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

from cffadb import dbinterface
import importExportCFFA
import importDataFromGoogle
from werkzeug.utils import secure_filename

pp = pprint.PrettyPrinter()

app = Flask(__name__, static_url_path='/static', static_folder='./static')
app.secret_key = constants.SECRET_KEY
app.debug = True
csrf.init_app(app)
bootstrap = Bootstrap(app)

if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/cffa_webserver.log', maxBytes=1024000, backupCount=10000)
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
mongoConnectString = "mongodb://" + BACKEND_DBUSR + \
                     ":" + BACKEND_DBPWD + \
                     "@" + BACKEND_DBHOST + \
                     ":" + BACKEND_DBPORT + \
                     "/" + BACKEND_DBNAME

try:
    ourDB = dbinterface.FootballDB(mongoConnectString, BACKEND_DBNAME)
    EXPORT_DIR = env.get(constants.EXPORTDIRECTORY)
    app.logger.info("Export Dir is:" + EXPORT_DIR)
    fileManager = importExportCFFA.CFFAImportExport(ourDB, EXPORT_DIR)
except Exception as e:
    app.logger.critical("ABORT. CFFA initialisation with DB failed with " +
                        mongoConnectString + ". " +
                        getattr(e, 'message', repr(e)))
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


def requires_manager_role(f):
    """ Additional wrap to ensure that only manager role CFFA users can access the endpoint.
     """

    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session[constants.PROFILE_KEY].get('user_id')
        player_confirmed = ourDB.validate_user_as_player_role(user_id)
        if player_confirmed:
            return redirect('/playerSummary')

        return f(*args, **kwargs)

    return decorated


def set_tenancy(f):
    """ A decorator wrap to ensure the tenancy is set on every endpoint call.
    In a kubernetes cluster of multiple CFFA flask apps, a load balancer will forward the request
    onto any flask webserver. This also ensures concurrent user access with different tenancies do not
    pick up the wrong tenancy in their session

    Note to self: perhaps the ourDB object should be part of the session object as this would be retained
    between each user request. This would mean the tenancy collection would be global and initialised on start up, and
    ourDB would be set in the callback endpoint

    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ourDB.load_team_tables_for_user_id(session[constants.PROFILE_KEY].get('user_id', None)):
            # new manager entry point, redirect to onboarding wizard
            return redirect(url_for('onboarding'))

        return f(*args, **kwargs)

    return decorated


# Controllers API
@app.route('/')
def home():
    """ Derived from Auth0 python example for single web pages. Provides a log in button before being shown the login
    AUth0 dialog, or if already authenticated, the entry_screen endpoint.

     """
    return render_template('home.html')


@app.route('/callback')
def callback_handling():
    """ Derived from Auth0 python example for single web pages. Setting up session variables prior to redirection
    to home screen (entry_screen)

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
@requires_manager_role
@set_tenancy
def entry_screen():
    """ Main screen for manager. If user collections do not exist assumes new user and redirects to onboarding screen.
     """
    # from username lets check tenancy. Use metadata in Auth0 for userID. This will be unique.
    if not ourDB.load_team_tables_for_user_id(session[constants.PROFILE_KEY].get('user_id', None)):
        # new manager entry point, redirect to onboarding wizard
        return redirect(url_for('onboarding'))

    app.logger.debug('Rendering entry_screen.html')
    return render_template("entryScreen.html",
                           playerSummaries=ourDB.get_active_player_summary(),
                           allPlayers=ourDB.get_full_summary(),
                           recentGames=ourDB.get_recent_games(),
                           allGames=ourDB.get_all_games(),
                           transactions=ourDB.get_recent_transactions(),
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/onboarding', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
def onboarding():
    """Onboarding screen to prompt for team name for new managers.
    """
    app.logger.debug("Entering onboarding")
    add_team_form = formHandler.AddTeam(ourDB.get_list_of_all_tenant_names())

    if add_team_form.validate_on_submit():
        # before adding team, if this is a new user auth0 metadata is not set -
        if session[constants.PROFILE_KEY].get('user_id', None) is None:
            # fatal, every login from auth0 will have user_id set.
            app.logger.critical("No user_id set in authenticator, cannot onboard")
            message = "No user_id set in authenticator. Cannot on-board this user"
        else:
            message = ourDB.add_team(add_team_form.teamname.data,
                                     session[constants.PROFILE_KEY].get('user_id', None),
                                     session[constants.PROFILE_KEY].get('name'))

        flash(message)
        # when switching back to entry_screen we will end up switching the db collections to the tenant

        return redirect(url_for('entry_screen'))

    return render_template("newTeam.html",
                           addTeamForm=add_team_form,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/games', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def manage_games():
    """ Functionality to manage games - add, edit, remove. The logic handles the response when adding a new game, but
    edit and delete game are redirected to their endpoints via the form action setting in the manage_games.html
    template.
    """
    # add game; edit game; delete game; dump games
    # handle guests too
    app.logger.debug('Rendering manage_games')
    no_players_form = formHandler.AddGameNoPlayers()
    games = ourDB.get_all_games()
    game_labels = formHandler.create_labels_for_games(games)
    edit_game_form = formHandler.EditGameSelectForm()
    edit_game_form.game.choices = game_labels
    delete_game_form = formHandler.DeleteGameSelectForm()
    delete_game_form.game.choices = game_labels

    # if no_players_form.validate_on_submit():
    if no_players_form.submit.data and no_players_form.validate():
        redirect_to_new_game = url_for('new_game', players=no_players_form.noplayers.data)
        return redirect(redirect_to_new_game)

    return render_template("manageGames.html",
                           allGames=ourDB.get_all_games(),
                           form=no_players_form,
                           editGameform=edit_game_form,
                           deleteGameform=delete_game_form,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/newgame/<int:players>', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def new_game(players):
    """ Renders and processes the new game form.

    Parameters
    ----------

    players : int
        Number of players that played in the new game. Used in form validation.
    """

    app.logger.debug('Rendering new_game with players' + str(players))
    booker = session[constants.PROFILE_KEY].get('name')
    new_game_defaults = ourDB.get_defaults_for_new_game(booker)
    no_players_form = formHandler.GameDetails(players, obj=new_game_defaults)
    if ourDB.new_manager():
        flash("TIP: When adding a game, a player will be created if it doesn't already exist")

    if no_players_form.validate_on_submit():
        ourDB.add_game(formHandler.game_form_to_football(no_players_form))
        flash("Game on {} for {} players has been added".format(no_players_form.gamedate.data, players))
        return redirect(url_for('entry_screen'))

    return render_template("newGame.html", noOfPlayers=players,
                           form=no_players_form,
                           activePlayerList=ourDB.get_active_players_for_new_game(),
                           cffauser=session[constants.PROFILE_KEY].get('name')
                           )


@app.route('/editgame', methods=['POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def edit_game():
    """  Processes edit game select form (ie: which game to edit).
    """
    games = ourDB.get_all_games()
    game_labels = formHandler.create_labels_for_games(games)
    select_game_form = formHandler.EditGameSelectForm()
    select_game_form.game.choices = game_labels
    delete_game_form = formHandler.DeleteGameSelectForm()

    app.logger.debug("Got into edit_game" + str(select_game_form))

    if select_game_form.validate_on_submit():
        choice = select_game_form.game.data
        app.logger.debug("choice was" + str(choice))
        return redirect(url_for('apply_edit_game', choice=choice))

    # we should not get here as this is always called with a POST request for edit via manage_games.
    app.logger.warning("Should not get here in edit_game without a successful POST entry condition. Or rather "
                       "there are no games in DB!")
    flash("Unable to edit selected game")
    return redirect(url_for('entry_screen'))


@app.route('/applyEditGame/<int:choice>', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def apply_edit_game(choice):
    """  Processes edit game form rendering and form input processing. Unlike new game form this does not check the
    number of players selected.

        choice : int
        Index to selected game (in list obtained from get_all_games(). Possible flaw if another user adds a new game for
        te same team whilst in this workflow. (edge case)

    """
    app.logger.debug("Entering apply_edit_game()")
    games = ourDB.get_all_games()
    edit_game_details = ourDB.get_game_details_for_edit_delete_form(games[choice].get("_id"), True)
    players = 0  # 0 = supresses the validation logic for number of players selected in form.
    edit_players_form = formHandler.GameDetails(players, obj=edit_game_details)

    # need to check form itself and set players based on checked players in submitted form before validation

    if edit_players_form.validate_on_submit():
        flash("Game on date {} has been edited".format(edit_players_form.gamedate.data))
        ourDB.edit_game(games[choice].get("_id"), formHandler.game_form_to_football(edit_players_form))
        return redirect(url_for('entry_screen'))

    return render_template("editGame.html",
                           form=edit_players_form
                           )


@app.route('/deletegame', methods=['POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def delete_game():
    """  Processes delete game select form (ie: which game to delete). As it has been redirected from a completed
    form we should not get to the end of the function unless there are no games.
 TO DO: Probably can delete the edit game form logic below.
    """

    app.logger.debug("Entering delete_game")
    games = ourDB.get_all_games()
    game_labels = formHandler.create_labels_for_games(games)
    select_game_form = formHandler.EditGameSelectForm()
    select_game_form.game.choices = game_labels
    delete_game_form = formHandler.DeleteGameSelectForm()
    delete_game_form.game.choices = game_labels

    if delete_game_form.validate_on_submit():
        choice = delete_game_form.game.data
        app.logger.debug("delete choice was" + str(choice))
        return redirect(url_for('apply_delete_game', choice=choice))

    app.logger.warning("Should not get here in delete_game without a successful POST entry condition. "
                       "Or rather there are no games in DB!")
    flash("Unable to delete selected game")
    return redirect(url_for('entry_screen'))


@app.route('/applyDeletegame/<int:choice>', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def apply_delete_game(choice):
    """  Processes delete game form rendering and form input processing.

        choice : int
        Index to selected game (in list obtained from getAllGames(). Possible flaw if another user adds a new game for
        te same team whilst in this workflow. (edge case)

    """
    app.logger.debug("Entering apply_delete_game")
    games = ourDB.get_all_games()
    db_id = games[choice].get("_id")
    delete_game_details = ourDB.get_game_details_for_edit_delete_form(db_id, False)
    delete_confirmation_form = formHandler.ConfirmDelete()
    if delete_confirmation_form.validate_on_submit():
        flash_message = ourDB.delete_game(db_id)
        flash(flash_message)
        return redirect(url_for('entry_screen'))

    return render_template("deleteGame.html",
                           form=delete_confirmation_form,
                           gamedetails=delete_game_details,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/players', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def manage_players():
    """ Functionality to manage players - add, edit, retire and reactivate. The logic handles the response when
    adding a new player, but edit, retire and reactivate players  are redirected to their endpoints via the form
    action setting in the managePlayers.html template.
    """
    # add player, edit player, cannot delete player if they have played a game
    # dump players
    app.logger.debug("Entering manage_players()")
    all_players = ourDB.get_all_player_details_for_player_edit()  # in obj classes
    add_player_form = formHandler.NewPlayer(
        formHandler.create_labels_for_players(ourDB.get_all_players(), action="allplayers"))
    edit_player_form = formHandler.SelectPlayerToEdit(obj=all_players)
    edit_player_form.oldplayer.choices = formHandler.create_labels_for_players(ourDB.get_all_players(),
                                                                               action="allplayers")
    retire_player_form = formHandler.RetirePlayer()
    retire_player_form.retireplayer.choices = formHandler.create_labels_for_players(ourDB.get_all_players(),
                                                                                    action="retire")
    reactivate_player_form = formHandler.ReactivatePlayer()
    reactivate_player_form.reactivateplayer.choices = formHandler.create_labels_for_players(ourDB.get_all_players(),
                                                                                            action="reactivate")

    if add_player_form.validate_on_submit():
        flash_message = ourDB.add_player(formHandler.new_player_form_to_football(add_player_form))
        flash(flash_message)
        return redirect(url_for('entry_screen'))

    return render_template("managePlayers.html",
                           addPlayerForm=add_player_form,
                           editPlayerForm=edit_player_form,
                           retirePlayerForm=retire_player_form,
                           reactivatePlayerForm=reactivate_player_form,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/editSelectPlayer', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def edit_select_player():
    """  Processes edit player select form (ie: which player to edit) and then redirects to edit player endpoint. Form
    should always validate as endpoint is a post redirect from the manage_players page.

    TO DO: Remove GET method from function.
    """
    app.logger.debug("We got to edit_select_player")
    all_players = ourDB.get_all_player_details_for_player_edit()  # in obj classes
    player_list = formHandler.create_labels_for_players(ourDB.get_all_players(), action="allplayers")
    edit_player_form = formHandler.SelectPlayerToEdit(obj=all_players)
    edit_player_form.oldplayer.choices = player_list

    if edit_player_form.validate_on_submit():
        # only got the player to edit, now redirect to
        return redirect(url_for('edit_player', player=edit_player_form.oldplayer.data))

    # we should never get here
    app.logger.info(" We should not get to this part of edit_select_player")
    return False


@app.route('/editPlayer/<int:player>', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def edit_player(player):
    """  Renders and post processes the edit player form for the selected player.

        player : int
        Index to selected player (in list obtained from create_labels_for_players() and removes selected player from
        list. This is for validation to prevent a player name duplicate occurring during edit.

    """
    app.logger.debug('Entering edit_player')
    player_list = formHandler.create_labels_for_players(ourDB.get_all_players(), action="allplayers")
    our_players = dict(player_list)
    player_defaults = ourDB.get_player_defaults_for_edit(our_players.get(player))
    # remove own player name from player_list for validation
    player_list.pop(player)
    edit_player_form = formHandler.EditPlayer(player_list, obj=player_defaults)

    if edit_player_form.validate_on_submit():
        message = ourDB.edit_player(our_players.get(player), formHandler.edit_player_form_to_football(edit_player_form))
        flash(message)
        return redirect(url_for('entry_screen'))

    return render_template("editPlayer.html",
                           editPlayerForm=edit_player_form)


@app.route('/retirePlayer', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def retire_player():
    """  Processes retire player select form (ie: which player to retire). Form
    should always validate as endpoint is a post redirect from the manage_players page.

    TO DO: Remove GET method from function.
    """
    app.logger.debug('We got to retire player')
    all_players = ourDB.get_all_player_details_for_player_edit()  # in obj classes
    player_list = formHandler.create_labels_for_players(ourDB.get_all_players(), action="retire")
    retire_player_form = formHandler.RetirePlayer()
    retire_player_form.retireplayer.choices = player_list

    if retire_player_form.validate_on_submit():
        our_players = dict(player_list)
        flash_message = ourDB.retire_player(our_players.get(retire_player_form.retireplayer.data))
        flash(flash_message)
        return redirect(url_for('entry_screen'))

    # TO DO we should never get here as this should only be called with a POST
    app.logger.info(" Should not get this far in retire_player() unless there are no players to Retire")
    flash("Unable to retire the selected player")
    return redirect(url_for('entry_screen'))


@app.route('/reactivatePlayer', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def reactivate_player():
    """  Processes reactivate (from retirement) player select form (ie: which player to reactivate). Form
    should always validate as endpoint is a post redirect from the manage_players page.

    TO DO: Remove GET method from function.
    """
    app.logger.debug('We got to reactivate player')
    player_list = formHandler.create_labels_for_players(ourDB.get_all_players(), action="reactivate")
    reactivate_player_form = formHandler.ReactivatePlayer()
    reactivate_player_form.reactivateplayer.choices = player_list

    if reactivate_player_form.validate_on_submit():
        our_players = dict(player_list)
        flash_message = ourDB.reactivate_player(our_players.get(reactivate_player_form.reactivateplayer.data))
        flash(flash_message)
        return redirect(url_for('entry_screen'))

    # TO DO we should never get here as this should only be called with a POST
    app.logger.info(
        " Should not get this far in reactivate_player() unless there are no players available to reactivate")
    flash("Unable to reactivate the selected player")
    return redirect(url_for('entry_screen'))


@app.route('/transactions', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def manage_transactions():
    """ Functionality to manage transactions - add, edit, and show all. The logic handles the response when adding a new
    transaction, but edit and list transactions are redirected to their endpoints via the form action setting in the
    manageTransactions.html template. Note there is no functionality to remove transactions so any user errors require
    additional transactions to adjust.

    """
    # add payment, edit payment, remove payment, autopayquick, view all transactions
    # needs to sort on transaction from recent first.
    app.logger.debug('We got to transactions()')
    transaction_defaults = ourDB.get_defaults_for_transaction_form(session[constants.PROFILE_KEY].get('name'))
    add_transaction_form = formHandler.NewTransaction(obj=transaction_defaults)
    add_transaction_form.player.choices = formHandler.create_labels_for_players(ourDB.get_all_players(),
                                                                                action="allplayers")
    quick_autopay_form = formHandler.AutopayforCurrentUser()

    if add_transaction_form.validate_on_submit():
        player_list = dict(add_transaction_form.player.choices)
        flash_message = \
            ourDB.add_transaction(formHandler.new_transaction_form_to_football(add_transaction_form,
                                                                               player_list.get(
                                                                                   add_transaction_form.player.data,
                                                                                   None)))
        flash(flash_message)
        return redirect(url_for('manage_transactions'))

    return render_template("manageTransactions.html",
                           addTransactionForm=add_transaction_form,
                           quickAutoPayForm=quick_autopay_form,
                           autoPayDetails=ourDB.get_autopay_details(session[constants.PROFILE_KEY].get('name')),
                           allTransactions=ourDB.get_all_transactions(),
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/autoPay', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def autopay():
    """  Processes thw autopay logic to automatically credit the manager (logged in user) with the value of the
     last played game. Form should always validate as endpoint is a post redirect from the manage_transactions page.

    TO DO: Remove GET method from function.
    TO DO: Stop multiple actions for the same game to avoid accidental usage.
    """
    app.logger.info('Got to autopay()')
    quick_autopay_form = formHandler.AutopayforCurrentUser()

    if quick_autopay_form.validate_on_submit():
        flash_message = ourDB.add_transaction(ourDB.get_autopay_details(session[constants.PROFILE_KEY].get('name')))
        flash(flash_message)
        return redirect(url_for('manage_transactions'))

    app.logger.debug("Should not get here in autopay logic unless autopay is pressed without any previous game")
    flash("Unable to autopay - was there any previous games played?")
    return redirect(url_for('entry_screen'))


@app.route('/settings', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def manage_settings():
    """ Functionality to manage settings and similar behaviour including edit team name, export and import data, import
     google sheet data and reset DB.  The logic handles the response when changing the team name  but the other actions
     are redirected to their endpoints via the form action setting in the
    manageSettings.html template. Note that import from json is not implemented yet.

    """
    # edit team name, export and import db json for all collections\
    app.logger.debug("Got to manage_settings()")
    our_settings = ourDB.get_app_settings()
    settings_change_form = formHandler.CFFASettings(obj=our_settings)
    db_export_form = formHandler.DownloadJSON()  # just a submit button to redirect to url
    db_recovery_form = formHandler.UploadJSON()
    google_upload_form = formHandler.PopulateFromGoogleSheet()
    delete_all_form = formHandler.DeleteAll()

    if settings_change_form.validate_on_submit():
        flash_message = ourDB.update_team_name(settings_change_form.teamname.data,
                                               session[constants.PROFILE_KEY].get('user_id', None))
        flash(flash_message)
        return redirect(url_for('entry_screen'))

    return render_template("manageSettings.html",
                           settingsChangeForm=settings_change_form,
                           dbExportForm=db_export_form,
                           dbRecoveryForm=db_recovery_form,
                           dbImportGsheetForm=google_upload_form,
                           deleteAllForm=delete_all_form,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/downloadjson', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def download_json():
    """  Processes download of the DB in json format.  Form
    should always validate as endpoint is a post redirect from the manage_settings page.

    TO DO: Remove GET method from function.
    """
    app.logger.debug(" we got to download_json")
    # call to extract all tables as json and place into zip to download via sendfile
    filename = fileManager.exportarchive()
    return send_file(filename,
                     mimetype='application/zip',
                     as_attachment=True)  # tell client  not to view file but download


@app.route('/uploadjson', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def upload_json():
    """  Processes upload of the DB in json format.

    TO DO: Implement. The False return value will generate an error.
    """
    app.logger.debug("We got to upload_json()")
    return False


@app.route('/uploadGoogleConnector', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def upload_google_connector():
    """  Processes the completed google import form. Form
    should always validate as endpoint is a post redirect from the manage_settings page.

    TO DO: Remove GET method from function.
    TO DO: Better error handling.
    """
    app.logger.debug("We got to upload_google_connector()")

    google_upload_form = formHandler.PopulateFromGoogleSheet()
    if google_upload_form.validate_on_submit():
        filename = secure_filename(google_upload_form.googlefile.data.filename)
        google_upload_form.googlefile.data.save('uploads/' + filename)
        google_connector = importDataFromGoogle.GoogleImporter(ourDB,
                                                               "uploads/" + filename,
                                                               google_upload_form.sheetname.data,
                                                               google_upload_form.transactionsheetname.data,
                                                               google_upload_form.gamesheetname.data,
                                                               google_upload_form.summarysheetname.data,
                                                               google_upload_form.summarysheetstartrow.data,
                                                               google_upload_form.summarysheetendrow.data)

        flash_message = google_connector.download_data()
        flash(flash_message)
        return redirect(url_for('entry_screen'))

    # should not get here
    app.logger.critical("Managed to get past validate on uploadGoogleCollector(). Unexpected")
    return False


@app.route('/deleteAll', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def delete_all_data():
    """  Processes the DB deletion. Form
    should always validate as endpoint is a post redirect from the manage_settings page.

    TO DO: Remove GET method from function.
    TO DO: Logic should drop the tenancy table but only the rows for the user's tenancy. Current behaviour aids
    complete reset of DB and debugging/test cases.
    """
    app.logger.warning("Entered delete_all_data() - about to reset DB")
    delete_all_form = formHandler.DeleteAll()
    if delete_all_form.validate_on_submit():
        app.logger.warning("Deleting database")
        message = ourDB.drop_all_collections(session[constants.PROFILE_KEY].get('user_id', None))
        flash(message)
        return redirect(url_for('entry_screen'))

    # should not get here
    app.logger.critical("Managed to get past validate on delete_all_data(). Unexpected")
    return False


@app.route('/manageUserAccess', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def manage_user_access():
    """ Functionality to manage user access including adding users and editing users. The logic handles the response
    when adding a new user but editing user is redirected to that endpoint via the form action setting in the
    manageUserAccess.html template.

    """
    app.logger.debug("Got to manage_user_access()")
    user_access_data = ourDB.get_user_access_data(session[constants.PROFILE_KEY].get('user_id', None))
    add_access_form = formHandler.AddAccess()
    select_edit_user_access_form = formHandler.SelectEditUserAccess(obj=user_access_data)
    select_edit_user_access_form.edituser.choices = formHandler.create_labels_for_users(user_access_data)

    # select_edit_user_access_form and SelectRevokeUserAccessForm redirect to different urls
    if add_access_form.validate_on_submit():
        flash_message = ourDB.add_user_access(add_access_form.name.data,
                                              add_access_form.authid.data,
                                              add_access_form.type.data,
                                              session[constants.PROFILE_KEY].get('user_id', None))
        flash(flash_message)
        return redirect(url_for('manage_user_access'))

    return render_template("manageUserAccess.html",
                           Users=user_access_data,
                           addAccessForm=add_access_form,
                           editUserForm=select_edit_user_access_form,
                           cffauser=session[constants.PROFILE_KEY].get('name'))


@app.route('/editSelectUser', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def edit_select_user():
    """  Renders and processes the edit User form for user access. Form
    should always validate as endpoint is a post redirect from the manage_user_access page.

    TO DO: Remove GET method from function.
    TO DO: There is no validation in the forms for duplicate user names/IDs etc
    Big TO DO: Ideally integrate with a service that provides Auth0 functionality to obtain Auth0 IDs based on name/
    email address etc.
    """
    app.logger.debug("Got to edit_select_user()")
    user_access_data = ourDB.get_user_access_data(session[constants.PROFILE_KEY].get('user_id', None))
    add_access_form = formHandler.AddAccess()
    select_edit_user_access_form = formHandler.SelectEditUserAccess(obj=user_access_data)
    select_edit_user_access_form.edituser.choices = formHandler.create_labels_for_users(user_access_data)

    if select_edit_user_access_form.validate_on_submit():
        # only got the player to edit, now redirect to
        return redirect(url_for('edit_user_access', user=select_edit_user_access_form.edituser.data))

    # we should never get here
    app.logger.info(" We should not get to this part of edit_select_user")
    return None


@app.route('/editUserAccess/<int:user>', methods=['GET', 'POST'])
@requires_auth
@requires_manager_role
@set_tenancy
def edit_user_access(user):
    """  Renders and post processes the edit user access  form for the selected user.

        player : int
        Index to selected user (in list obtained from getUserAccessData().

        Note: TO DO: No logic yet implemented to handle duplicate names in edit form.

    """
    app.logger.debug('Entering edit_user_access')
    user_access_data = ourDB.get_user_access_data(session[constants.PROFILE_KEY].get('user_id', None))
    # ourUsers = dict(user_access_data)  # so we can turn index numbers into keys
    # user_data = ourDB.getUserAccessDefaultsForEdit(ourUsers.get(user))
    user_data = user_access_data[user]  # should return footballClasses user object

    edit_user_access_form = formHandler.EditUserAccess(obj=user_data)

    if edit_user_access_form.validate_on_submit():
        message = ourDB.edit_user_access(user_data.name,
                                         formHandler.edit_user_access_form_to_football(edit_user_access_form))
        flash(message)
        return redirect(url_for('manage_user_access'))

    return render_template("editUserAccess.html",
                           editUserForm=edit_user_access_form)


@app.route('/playerSummary')
@requires_auth
@set_tenancy
def player_summary_only():
    """  Processes the page for player role users. This offers no form functionality but summary data of their accounts,
    game activity and other stats. Also provides a bank statement style transaction view since they started playing.

    """
    if not ourDB.load_team_tables_for_user_id(session[constants.PROFILE_KEY].get('user_id', None)):
        # this should not happen as this redirect page only occurs if the user_id exists already and is
        # marked as a player as safety lets redirect to logout!
        app.logger.critical("User has gone to player Summary without valid userID")
        return redirect(url_for('logout'))

    app.logger.debug('Rendering playerSummary.html')
    return render_template("playerSummary.html",
                           summary=ourDB.get_summary_for_player(session[constants.PROFILE_KEY].get('name', None)),
                           ledger=ourDB.calc_ledger_for_player(session[constants.PROFILE_KEY].get('name', None)),
                           recentGames=ourDB.get_games_for_player(session[constants.PROFILE_KEY].get('name', None)),
                           cffauser=session[constants.PROFILE_KEY].get('name'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=env.get('PORT', 5000))
