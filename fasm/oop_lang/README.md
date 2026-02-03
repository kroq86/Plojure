# OOP-on-FASM language

A **new OOP language** that compiles to FASM. The same game as `../oop_game` (Entity + GameState, player vs enemy) is written in this language and compiled to ASM + C, then linked into a shared library.

**Existing files in `../oop_game` are not modified.** All language and game code live here.

## Layout

| File | Role |
|------|------|
| **SYNTAX.md** | Language grammar and semantics |
| **game.oop** | Game source (Entity, GameState, methods) in the OOP language |
| **compiler.py** | Compiler: reads `.oop` → emits `generated/game.asm` and `generated/wrapper.c` |
| **build.sh** | Runs compiler, FASM, gcc → `mylib.so` |
| **run_game.py** | Python driver: loads `mylib.so`, runs the same game loop as `../oop_game/game.py` |
| **generated/** | Output of compiler (game.asm, wrapper.c, game.o, wrapper.o); do not edit by hand |

## Build and run

```bash
./build.sh
python3 run_game.py
```

## Flow

1. **game.oop** — classes `Entity` and `GameState`, fields, methods (`get_health`, `set_health`, `init`, `get_player_health`, `get_enemy_health`, `tick`, `is_over`, `get_winner`).
2. **compiler.py** — parses `.oop`, builds struct layout, emits FASM (structs + method bodies) and C (structs + externs + `py_*` wrappers). The `tick` method is emitted as a fixed ASM block (same logic as hand-written `../oop_game/game.asm`).
3. **build.sh** — `python3 compiler.py` → `fasm generated/game.asm` → `gcc -c generated/wrapper.c` → `gcc -shared ...` → `mylib.so`.
4. **run_game.py** — ctypes load `mylib.so`, alloc GameState, loop: read health, roll damage, `py_game_state_tick`, until game over, then print winner.

## Relation to `../oop_game`

- **Same behavior**: same struct layout (Entity 8 bytes, GameState 24 bytes), same SysV x64 calling convention, same game rules.
- **Different source**: game logic is written in the new OOP language (`.oop`) and compiled to FASM instead of hand-written `game.asm`.
