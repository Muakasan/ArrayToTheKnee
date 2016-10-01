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
teamName = "vaCCuum"
roundNum = 0
# ---------------------------------------------------------------------

# Set initial connection data
def initialResponse():
# ------------------------- CHANGE THESE VALUES -----------------------
    return {'TeamName': teamName,
            'Characters': [
                {"CharacterName": "Kayle",
                 "ClassId": "Paladin"},
                {"CharacterName": "Garen",
                 "ClassId": "Warrior"},
                {"CharacterName": "Darius",
                 "ClassId": "Warrior"},
            ]}
# ---------------------------------------------------------------------
#My helper functions

def isStunned(hero):
    return hero.attributes.get_attribute("Stunned")

def isRooted(hero):
    return hero.attributes.get_attribute("Rooted")

# Determine actions to take on a given turn, given the server response
def processTurn(serverResponse):
# --------------------------- CHANGE THIS SECTION -------------------------
    # Setup helper variables
    global roundNum
    actions = []
    myteam = []
    enemyteam = []
    enemyteamwithoutstun = []
    roundNum += 1

    def healWeakest(hero, weakhero):
        actions.append({
            "Action": "Cast",
            "CharacterId": hero.id,
            "TargetId": weakhero.id,
            "AbilityId": 3,
             })

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
                enemyteamwithoutstun.append(character)
# ------------------ You shouldn't change above but you can ---------------

    # Choose a target
    def getTarget(key):
        target = None
        least_health = None
        if key == "attack":
            for enemy in enemyteam:
                if enemy.is_dead():
                    continue
                if least_health == None or enemy.attributes.health < least_health:
                    least_health = enemy.attributes.health
                    target = enemy
            return target
        elif key == "cc":
            for enemy in enemyteamwithoutstun:
                if not isStunned(enemy) and not isRooted(enemy):
                    return enemy
        return target

    #Find lowest hp team member
    weakcharacter = None
    least_health = None
    for character in myteam:
        if character.is_dead():
            continue
        if least_health == None or character.attributes.health < least_health:
            least_health = character.attributes.health
            weakcharacter = character

    # If we found a target
    for character in myteam:
        #If current character is Paladin
        if character.classId == "Paladin":
            if character.casting is None:
                # print "We can cast rite?"
                if character.attributes.health * 4 < 3 * character.attributes.maxHealth and character.abilities[3] == 0 and roundNum < 120:
                    castSkill(character, character, 3)
                    continue
                ccTarget = getTarget("cc")
                atkTarget = getTarget("attack")
                if not ccTarget and not atkTarget:
                    print "No target found!"
                    continue
                if ccTarget and character.in_ability_range_of(ccTarget, gameMap, 14) and character.abilities[14] == 0:
                    castSkill(character, ccTarget, 14)
                    enemyteamwithoutstun.remove(ccTarget)
                elif atkTarget and character.in_range_of(atkTarget, gameMap):
                    attackEnemy(character, atkTarget)
                else:
                    if ccTarget:
                        moveHero(character, ccTarget)
                    else:
                        moveHero(character, atkTarget)
            else:
                target = getTarget("attack")
                if target and character.in_range_of(target, gameMap):
                    attackEnemy(character, target)
                else:
                    moveHero(character, target)
        #If current character is Warrior
        if character.classId == "Warrior":
            if character.casting is None:
                # print "Warrior can smash rite?"
                ccTarget = getTarget("cc")
                atkTarget = getTarget("attack")
                if ccTarget and character.in_ability_range_of(ccTarget, gameMap, 1, False) and character.abilities[1] == 0:
                    castSkill(character, ccTarget, 1)
                    enemyteamwithoutstun.remove(ccTarget)
                elif atkTarget and character.in_range_of(atkTarget, gameMap):
                    attackEnemy(character, atkTarget)
                else:
                    if ccTarget:
                        moveHero(character, ccTarget)
                    else:
                        moveHero(character, atkTarget)
            else:
                target = getTarget("attack")
                if target and character.in_range_of(target, gameMap):
                    attackEnemy(character, target)
                else: # Not in range, move towards
                    moveHero(character, target)
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
