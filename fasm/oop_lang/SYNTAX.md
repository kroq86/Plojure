# OOP-on-FASM Language Syntax

A minimal OOP language that compiles to FASM (ELF64, SysV x64). Same semantics as the hand-written game.asm: classes = structs, methods = functions with `this` in RDI.

## Programs

- A program is a sequence of **class** definitions.
- No global statements; entry point is via C/Python calling exported methods.

## Classes

```
class ClassName
  field_type field_name
  ...
  def method_name(param_type param_name, ...) -> return_type
    statement
    ...
  end
  ...
end
```

- **ClassName**: identifier (PascalCase by convention).
- **field_type**: `int` or another class name (nested struct).
- **field_name**: identifier. Layout order = declaration order; alignment 4 bytes for int, 8 for nested class (two ints).
- **def** ... **end**: method. First argument is implicit `this` (pointer in RDI). Params in RSI, RDX, ...; return in EAX.

## Statements

- **this** . **field** = **expr**  
  Store into field (field can be nested: `this.player.health`).
- **return** **expr**  
  EAX = expr, then ret.
- **if** **expr** **relop** **expr**  
  **then** block (or newline and indented lines)  
  **else** block (optional)  
  **end**
- **int** **var** = **expr**  
  Local (implemented as register); only in method body.

## Expressions

- **literal**  
  Integer: 0, 1, 100, etc.
- **this** . **field** [ . **field** ] ...  
  Load from struct (e.g. `this.health`, `this.player.health`).
- **expr** - **expr**  
  Subtraction (for damage: `this.health - damage`).
- **expr** **relop** **expr**  
  Comparison; **relop** = `<`, `<=`, `==`, `>`, `>=`, `!=`.

## Method export

- All methods are exported as **classname_methodname** (lowercase, e.g. `entity_get_health`, `game_state_tick`).
- **init** on a class is used as the constructor (in-place init); name emitted as `classname_init`.

## Comments

- Lines starting with `#` or `//` are ignored.

## Example (fragment)

```
class Entity
  int type
  int health

  def get_health() -> int
    return this.health
  end

  def set_health(int h) -> void
    this.health = h
  end
end
```

## Compilation

- **compiler.py** reads `.oop` and emits `generated/game.asm` and `generated/wrapper.c`.
- **build.sh** runs the compiler, then FASM and gcc to produce `mylib.so`.
- **run_game.py** loads `mylib.so` and runs the same game loop as the hand-written POC.
