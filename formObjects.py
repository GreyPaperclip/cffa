class player:

    name = "No Player set"
    playedLastGame = False

    def __init__(self, dbid, name, playedLastGame):
        self.dbid - dbid
        self.name = name
        self.playedLastGame - playedLastGame

class game:

    gamecost = float (0.00)
    playerList = []

    def __init__(self, gameCost, playerList):
        self.gameCost = gameCost
        self.playerList = playerList

