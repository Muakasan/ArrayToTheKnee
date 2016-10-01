#!/usr/bin/python2
import socket
import json
import os
import random
import sys
from socket import error as SocketError
import errno
sys.path.append("../..")
import src.game.game_constants as game_consts
from src.game.character import *
from src.game.gamemap import *

# Game map that you can use to query
gameMap = GameMap()

# --------------------------- SET THIS IS UP -------------------------
teamName = "RushWarriors"
enemyMark = {}
# ---------------------------------------------------------------------
def manhattanDist(hero1, hero2): # Cuz DotA > League
    pos1 = hero1.position
    pos2 = hero2.position

    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
# Set initial connection data
def initialResponse():
# ------------------------- CHANGE THESE VALUES -----------------------
    return {'TeamName': "RushWarriors",
            'Characters': [
                {"CharacterName": "Warrior",
                 "ClassId": "Warrior"},
                {"CharacterName": "Warrior2",
                 "ClassId": "Warrior"},
                {"CharacterName": "Warrior3",
                 "ClassId": "Warrior"},
            ]}
# ---------------------------------------------------------------------
#helper functions
def isStunned(hero):
    return hero.attributes.get_attribute("Stunned")

def isRooted(hero):
    return hero.attributes.get_attribute("Rooted")
# Determine actions to take on a given turn, given the server response
def processTurn(serverResponse):
# --------------------------- CHANGE THIS SECTION -------------------------
    # Setup helper variables
    actions = []
    myteam = []
    enemyteam = []

    def attackEnemy(hero, enemy):
        actions.append({
            "Action": "Attack",
            "CharacterId": hero.id,
            "TargetId": enemy.id,
             })

    def castSkill(hero, enemy, num):
        actions.append({
            "Action": "Cast",
            "CharacterId": hero.id,
            "TargetId": enemy.id if game_consts.abilitiesList[num]["StatChanges"][0]["Change"] < 0 else hero.id,
            "AbilityId": num,
             })

    def moveHero(hero, enemy):
        actions.append({
            "Action": "Move",
            "CharacterId": hero.id,
            "TargetId": enemy.id,
             })
    # Find each team and serialize the objects
    for team in serverResponse["Teams"]:
        if team["Id"] == serverResponse["PlayerInfo"]["TeamId"]:
            for characterJson in team["Characters"]:
                character = Character()
                character.serialize(characterJson)
                myteam.append(character)
        else:
            for characterJson in team["Characters"]:
                character = Character()
                character.serialize(characterJson)
                enemyteam.append(character)

# ------------------ You shouldn't change above but you can ---------------

    for character in enemyteam:
        if not character.is_dead() and not isStunned(character) and not isRooted(character):
            enemyMark[character.id%3] = 0
        else:
            enemyMark[character.id%3] = 1

    # Choose a target
    # Choose the lowest HP target
    def getTarget(key):
        target = None
        least_health = None

        for character in enemyteam:
            if character.is_dead():
                continue
            if least_health == None or character.attributes.health < least_health:
                least_health = character.attributes.health
                target = character

        if key == "attack":
            return target
        elif key == "cc":
            for character in enemyteam:
                if enemyMark.get(character.id%3) == 0:
                    return character
        return target

    # If we found a target
    for character in myteam:
        # If I am in range, attack
        ccTarget = getTarget("cc")
        atkTarget = getTarget("attack")

        if character.casting is None:
            cast = False
            if ccTarget and character.in_range_of(ccTarget, gameMap) and character.abilities[1] == 0:
                castSkill(character, ccTarget, 1)
                enemyMark[ccTarget.id % 3] = 1
            elif atkTarget and character.in_range_of(atkTarget, gameMap):
                attackEnemy(character, atkTarget)
            else: # Not in range, move towards
                moveHero(character, atkTarget)

    # Send actions to the server
    return {
        'TeamName': teamName,
        'Actions': actions
    }
# ---------------------------------------------------------------------

# Main method
# @competitors DO NOT MODIFY
if __name__ == "__main__":
    # Config
    conn = ('localhost', 1337)
    if len(sys.argv) > 2:
        conn = (sys.argv[1], int(sys.argv[2]))

    # Handshake
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(conn)

    # Initial connection
    s.sendall(json.dumps(initialResponse()) + '\n')

    # Initialize test client
    game_running = True
    members = None

    # Run game
    try:
        data = s.recv(1024)
        while len(data) > 0 and game_running:
            value = None
            if "\n" in data:
                data = data.split('\n')
                if len(data) > 1 and data[1] != "":
                    data = data[1]
                    data += s.recv(1024)
                else:
                    value = json.loads(data[0])

                    # Check game status
                    if 'winner' in value:
                        game_running = False

                    # Send next turn (if appropriate)
                    else:
                        msg = processTurn(value) if "PlayerInfo" in value else initialResponse()
                        s.sendall(json.dumps(msg) + '\n')
                        data = s.recv(1024)
            else:
                data += s.recv(1024)
    except SocketError as e:
        if e.errno != errno.ECONNRESET:
            raise  # Not error we are looking for
        pass  # Handle error here.
    s.close()
