""" Unused file to scope out CFFA classes.

TO DO: Remove from CFFA

"""


class Player:

    name = "No Player set"
    played_last_game = False

    def __init__(self, db_id, name, played_last_game):
        self.db_id = db_id
        self.name = name
        self.played_last_game = played_last_game


class Game:

    game_cost = float(0.00)
    player_list = []

    def __init__(self, game_cost, player_list):
        self.game_cost = game_cost
        self.player_list = player_list

