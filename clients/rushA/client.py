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
teamName = "ArrayToTheKnee"
# ---------------------------------------------------------------------

# Set initial connection data
def initialResponse():
# ------------------------- CHANGE THESE VALUES -----------------------
    return {'TeamName': teamName,
            'Characters': [
                {"CharacterName": "Assassin1",
                 "ClassId": "Assassin"},
                {"CharacterName": "Assassin2",
                 "ClassId": "Assassin"},
                {"CharacterName": "Asssassin3",
                 "ClassId": "Assassin"},
            ]}
# ---------------------------------------------------------------------

# Determine actions to take on a given turn, given the server response
def processTurn(serverResponse):
# --------------------------- CHANGE THIS SECTION -------------------------
    # Setup helper variables
    actions = []
    myteam = []
    enemyteam = []
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
    
    # Choose the lowest HP target
   
    '''
    target = None
    least_health = None
    for character in enemyteam:
      if character.is_dead():
          continue
      if least_health == None or character.attributes.health < least_health:
          least_health = character.attributes.health
          target = character	
    '''

    def manhattanDist(hero1, hero2): # Cuz DotA > League
        pos1 = hero1.position
        pos2 = hero2.position
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    if (character.attributes.get_attribute("Stunned") or character.attributes.get_attribute("Rooted")) and character.abilities[0] == 0:
        actions.append({
            "Action": "Cast",
            "CharacterId": character.id,
            "TargetId": character.id,
            "AbilityId": 0
            })
    else:
        target = None
        if enemyteam:

            sList = filter(lambda x: not x.is_dead(), sorted(enemyteam, key=lambda x:  manhattanDist(x, myteam[0])*10000 + x.attributes.health + (x.classId == "Paladin" or x.classId == "Druid")*-1000000))
            target = sList[0]
        # If we found a target
        if target:
            for character in myteam:
                # If I am in range, either move towards target
                if character.in_range_of(target, gameMap):
                    if character.casting is None:
                        cast = False
                        if character.abilities[11] == 0:
                              actions.append({
                                   "Action": "Cast",
                                   "CharacterId": character.id,
                                   "TargetId": target.id,
                                   "AbilityId": 11,
                                   })
                        else:
                             actions.append({
                                  "Action": "Attack",
                                  "CharacterId": character.id,
                                  "TargetId": target.id,
                             })
                else: # Not in range, move towards
                    if character.casting is None:
                         cast = False
                         if character.abilities[12] == 0:
                              actions.append({
                                   "Action": "Cast",
                                   "CharacterId": character.id,
                                   "TargetId": character.id,
                                   "AbilityId": 12,
                              })
                         else:
                              actions.append({
                                   "Action": "Move",
                                   "CharacterId": character.id,
                                   "TargetId": target.id,
                              })

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
