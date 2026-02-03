; OOP-on-FASM POC: Entity + GameState "classes" for a minimal combat game.
; SysV x64 calling: rdi, rsi, rdx, rcx, r8, r9; return rax/eax.
; Struct layouts must match wrapper.c.

format ELF64

; === Entity "class" (8 bytes) ===
struc Entity {
    .type   dd 0    ; 0=player, 1=enemy
    .health dd 0
}
virtual at 0
    Entity Entity
    sizeof.Entity = $
end virtual

; === GameState "class" (24 bytes) ===
struc GameState {
    .player Entity  ; offset 0, 8 bytes
    .enemy  Entity  ; offset 8, 8 bytes
    .status dd 0    ; 0=ongoing, 1=over
    .winner dd 0    ; 0=none, 1=player, 2=enemy, 3=tie
}
virtual at 0
    GameState GameState
    sizeof.GameState = $
end virtual

section '.text' executable

; --- Entity "methods" (rdi = this) ---

; int entity_get_health(void* entity)
public entity_get_health
entity_get_health:
    mov eax, [rdi + Entity.health]
    ret

; void entity_set_health(void* entity, int health)
public entity_set_health
entity_set_health:
    mov [rdi + Entity.health], esi
    ret

; --- GameState "methods" (rdi = this) ---

; void game_state_init(void* gs) — in-place init: player/enemy health=100, status=ongoing
public game_state_init
game_state_init:
    mov dword [rdi + GameState.player + Entity.type], 0
    mov dword [rdi + GameState.player + Entity.health], 100
    mov dword [rdi + GameState.enemy + Entity.type], 1
    mov dword [rdi + GameState.enemy + Entity.health], 100
    mov dword [rdi + GameState.status], 0
    mov dword [rdi + GameState.winner], 0
    ret

; int game_state_get_player_health(void* gs)
public game_state_get_player_health
game_state_get_player_health:
    mov eax, [rdi + GameState.player + Entity.health]
    ret

; int game_state_get_enemy_health(void* gs)
public game_state_get_enemy_health
game_state_get_enemy_health:
    mov eax, [rdi + GameState.enemy + Entity.health]
    ret

; void game_state_tick(void* gs, int player_damage_to_enemy, int enemy_damage_to_player)
; Applies damage, clamps health to >=0, sets status/winner if game over.
public game_state_tick
game_state_tick:
    push rbx
    push r12
    ; rdi=gs, rsi=player_damage, rdx=enemy_damage
    mov r12, rdi
    mov ebx, esi
    mov ecx, edx

    ; Enemy health -= player_damage; clamp to 0
    mov eax, [r12 + GameState.enemy + Entity.health]
    sub eax, ebx
    cmp eax, 0
    jge .enemy_ok
    xor eax, eax
.enemy_ok:
    mov [r12 + GameState.enemy + Entity.health], eax

    ; Player health -= enemy_damage; clamp to 0
    mov eax, [r12 + GameState.player + Entity.health]
    sub eax, ecx
    cmp eax, 0
    jge .player_ok
    xor eax, eax
.player_ok:
    mov [r12 + GameState.player + Entity.health], eax

    ; Check game over: status still 0, set status=1 and winner if either health <= 0
    mov eax, [r12 + GameState.status]
    cmp eax, 1
    je .done
    mov eax, [r12 + GameState.player + Entity.health]
    mov r8d, [r12 + GameState.enemy + Entity.health]
    cmp eax, 0
    jle .game_over
    cmp r8d, 0
    jle .game_over
    jmp .done
.game_over:
    mov dword [r12 + GameState.status], 1
    cmp eax, 0
    jle .player_dead
    ; Player alive, enemy dead -> player wins
    mov dword [r12 + GameState.winner], 1
    jmp .done
.player_dead:
    cmp r8d, 0
    jle .both_dead
    ; Player dead, enemy alive -> enemy wins
    mov dword [r12 + GameState.winner], 2
    jmp .done
.both_dead:
    mov dword [r12 + GameState.winner], 3
.done:
    pop r12
    pop rbx
    ret

; int game_state_is_over(void* gs) -> 1 if over, 0 else
public game_state_is_over
game_state_is_over:
    mov eax, [rdi + GameState.status]
    ret

; int game_state_get_winner(void* gs) -> 0=none, 1=player, 2=enemy, 3=tie
public game_state_get_winner
game_state_get_winner:
    mov eax, [rdi + GameState.winner]
    ret
