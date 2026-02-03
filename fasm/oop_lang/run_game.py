#!/usr/bin/env python3
"""
Run the same game as fasm/oop_game/game.py, but the game is written in the
OOP-on-FASM language (game.oop) and compiled to FASM by compiler.py.
"""
import ctypes
import random
import os

_lib_path = os.path.join(os.path.dirname(__file__), "mylib.so")
if not os.path.isfile(_lib_path):
    raise FileNotFoundError(
        f"Build first: cd {os.path.dirname(__file__)} && ./build.sh"
    )

mylib = ctypes.CDLL(_lib_path)

mylib.py_game_state_alloc.argtypes = []
mylib.py_game_state_alloc.restype = ctypes.c_void_p

mylib.py_game_state_free.argtypes = [ctypes.c_void_p]
mylib.py_game_state_free.restype = None

mylib.py_game_state_get_player_health.argtypes = [ctypes.c_void_p]
mylib.py_game_state_get_player_health.restype = ctypes.c_int

mylib.py_game_state_get_enemy_health.argtypes = [ctypes.c_void_p]
mylib.py_game_state_get_enemy_health.restype = ctypes.c_int

mylib.py_game_state_tick.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
]
mylib.py_game_state_tick.restype = None

mylib.py_game_state_is_over.argtypes = [ctypes.c_void_p]
mylib.py_game_state_is_over.restype = ctypes.c_int

mylib.py_game_state_get_winner.argtypes = [ctypes.c_void_p]
mylib.py_game_state_get_winner.restype = ctypes.c_int


def game_loop():
    gs = mylib.py_game_state_alloc()
    if not gs:
        raise RuntimeError("py_game_state_alloc failed")

    try:
        print("OOP-on-FASM language game (game.oop -> FASM -> mylib.so)")
        print("Player vs Enemy; damage rolled in Python.\n")

        while mylib.py_game_state_is_over(gs) == 0:
            player_h = mylib.py_game_state_get_player_health(gs)
            enemy_h = mylib.py_game_state_get_enemy_health(gs)
            print(f"Player health: {player_h}  Enemy health: {enemy_h}")

            player_damage = 5 + random.randint(0, 10)
            enemy_damage = 5 + random.randint(0, 10)
            print(f"Player attacks enemy for {player_damage} damage")
            print(f"Enemy attacks player for {enemy_damage} damage")

            mylib.py_game_state_tick(gs, player_damage, enemy_damage)
            print("---")

        winner = mylib.py_game_state_get_winner(gs)
        player_h = mylib.py_game_state_get_player_health(gs)
        enemy_h = mylib.py_game_state_get_enemy_health(gs)

        print("\nGame over!")
        if winner == 1:
            print("Player wins!")
        elif winner == 2:
            print("Enemy wins!")
        else:
            print("It's a tie!")
        print(f"Final health - Player: {player_h}  Enemy: {enemy_h}")
    finally:
        mylib.py_game_state_free(gs)


if __name__ == "__main__":
    game_loop()
