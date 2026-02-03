OOP lang on top of FASM

sudo apt update
sudo apt install fasm

[oop](fasm/oop_game)
chmod +x build.sh 
./build.sh 
python run_game.py 

SYNTAX.md	Language spec: classes, fields, methods, this, return, assignments, if/else, comments.
game.oop	Same game as oop_game: Entity (type, health; get_health, set_health) and GameState (player, enemy, status, winner; init, get_player_health, get_enemy_health, tick, is_over, get_winner).
compiler.py	Compiler: reads game.oop → writes generated/game.asm and generated/wrapper.c. Parses classes/fields/methods, builds struct layout, emits FASM (structs + method bodies) and C (structs + externs + py_* wrappers). tick is emitted as a fixed ASM block (same logic as hand-written game).
build.sh	Runs python3 compiler.py, then FASM and gcc on generated/ to produce mylib.so.
run_game.py	Same game loop as oop_game/game.py: loads mylib.so, alloc GameState, random damage, py_game_state_tick, until game over, then prints winner.
README.md	Describes the language, layout, build/run, and relation to oop_game.
