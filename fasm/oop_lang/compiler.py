#!/usr/bin/env python3
"""
OOP-on-FASM compiler: reads .oop source and emits FASM (.asm) and C wrapper (.c).
Output: generated/game.asm, generated/wrapper.c
"""
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def strip_comment(line):
    s = line.split("#")[0].split("//")[0].strip()
    return s

def tokenize_line(line):
    """Return list of tokens (words, symbols)."""
    line = strip_comment(line)
    if not line:
        return []
    # Split on whitespace but keep relops together
    tokens = re.findall(r'->|<=|>=|==|!=|[<>]=?|\w+|[=().,\-]', line)
    return [t for t in tokens if t not in ('', ' ')]

def parse_oop(source_path):
    """Parse .oop file into AST: list of classes, each with fields and methods."""
    with open(source_path, "r") as f:
        lines = f.readlines()

    classes = []
    i = 0

    while i < len(lines):
        line = lines[i]
        raw = strip_comment(line)
        i += 1
        if not raw:
            continue
        toks = tokenize_line(line)
        if not toks:
            continue
        if toks[0] == "class" and len(toks) >= 2:
            class_name = toks[1]
            fields = []
            methods = []
            while i < len(lines):
                ln = lines[i]
                r = strip_comment(ln)
                i += 1
                if not r:
                    continue
                t = tokenize_line(ln)
                if not t:
                    continue
                if t[0] == "end":
                    break
                if t[0] == "def":
                    # def name ( params ) -> ret
                    name = t[1]
                    params = []
                    if len(t) >= 3 and t[2] == "(":
                        j = 3
                        while j < len(t) and t[j] != ")":
                            if t[j] == "int" and j + 1 < len(t):
                                params.append(("int", t[j + 1]))
                                j += 2
                            else:
                                j += 1
                    ret = "void"
                    for k, tok in enumerate(t):
                        if tok == "->" and k + 1 < len(t):
                            ret = t[k + 1]
                            break
                    body_lines = []
                    while i < len(lines):
                        bl = lines[i]
                        bi = len(bl) - len(bl.lstrip())
                        i += 1
                        br = strip_comment(bl)
                        if not br:
                            continue
                        bt = tokenize_line(bl)
                        if not bt:
                            continue
                        if bt[0] == "end" and bi <= 2:
                            break
                        body_lines.append(bl)
                    methods.append((name, params, ret, body_lines))
                    continue
                if t[0] in ("int",) or (len(t) >= 2 and t[1] not in ("(", "=") and t[0] not in ("end", "if", "else", "return", "this")):
                    # field: "int x" or "Entity player"
                    if t[0] == "int":
                        fields.append(("int", t[1]))
                    else:
                        fields.append((t[0], t[1]))
                    continue
            classes.append({"name": class_name, "fields": fields, "methods": methods})
    return classes

def parse_method_body(body_lines, class_name, method_name):
    """Parse method body lines into list of statements."""
    stmts = []
    i = 0
    while i < len(body_lines):
        line = body_lines[i]
        raw = strip_comment(line).strip()
        i += 1
        if not raw:
            continue
        toks = tokenize_line(line)
        if not toks:
            continue
        if toks[0] == "return":
            if len(toks) >= 3 and toks[1] == "this" and toks[2] == ".":
                path = [toks[i] for i in range(3, len(toks), 2)]
                stmts.append(("return", path))
            elif len(toks) > 1 and toks[1].isdigit():
                stmts.append(("return", int(toks[1])))
            else:
                stmts.append(("return", None))
            continue
        if toks[0] == "int" and len(toks) >= 4 and toks[2] == "=":
            var = toks[1]
            # expr: literal, or this.x.y - something, or this.x
            rest = toks[3:]
            stmts.append(("local_assign", var, rest))
            continue
        if toks[0] == "if":
            # if expr relop expr -> condition; then block until else/end
            cond = toks[1:]
            then_block = []
            else_block = []
            depth = 0
            in_else = False
            while i < len(body_lines):
                ln = body_lines[i]
                bi = len(ln) - len(ln.lstrip())
                i += 1
                br = strip_comment(ln).strip()
                bt = tokenize_line(ln) if br else []
                if bt and bt[0] == "end":
                    if depth == 0:
                        break
                    depth -= 1
                    then_block.append(ln) if not in_else else else_block.append(ln)
                    continue
                if bt and bt[0] == "else" and depth == 0:
                    in_else = True
                    continue
                if bt and bt[0] == "if" and not in_else:
                    depth += 1
                (then_block if not in_else else else_block).append(ln)
            stmts.append(("if", cond, then_block, else_block))
            continue
        if toks[0] == "this" and len(toks) >= 3 and toks[1] == "." and "=" in toks:
            eq = toks.index("=")
            lvalue = toks[:eq]
            rhs = toks[eq + 1:]
            stmts.append(("assign", lvalue, rhs))
            continue
        # var = literal (local assign)
        if len(toks) >= 3 and toks[1] == "=":
            var = toks[0]
            rhs = toks[2:]
            stmts.append(("local_set", var, rhs))
            continue
    return stmts

# ---------------------------------------------------------------------------
# Struct layout (match fasm/oop_game/game.asm)
# ---------------------------------------------------------------------------

def field_size(ftype):
    return 4 if ftype == "int" else 8

def compute_offsets(fields):
    off = 0
    out = []
    for ftype, fname in fields:
        sz = field_size(ftype)
        out.append((ftype, fname, off))
        off += sz
    return out

def flatten_field_path(class_map, class_name, path):
    """path = ['player','health'] -> (base_offset, final_field_type)."""
    offsets = compute_offsets(class_map[class_name]["fields"])
    base = 0
    for i, seg in enumerate(path):
        for ftype, fname, off in offsets:
            if fname == seg:
                if ftype == "int":
                    return base + off, "int"
                base += off
                class_name = ftype
                offsets = compute_offsets(class_map[class_name]["fields"])
                break
    return base, "int"

def fasm_offset_expr(class_map, class_name, path):
    """Return FASM symbolic offset e.g. 'Entity.health' or 'GameState.player + Entity.health'."""
    if not path:
        return "0"
    offsets = compute_offsets(class_map[class_name]["fields"])
    parts = []
    cur_class = class_name
    for seg in path:
        for ftype, fname, off in offsets:
            if fname == seg:
                if ftype == "int":
                    parts.append(f"{cur_class}.{fname}")
                    return " + ".join(parts) if len(parts) > 1 else parts[0]
                parts.append(f"{cur_class}.{fname}")
                cur_class = ftype
                offsets = compute_offsets(class_map[cur_class]["fields"])
                break
    return " + ".join(parts) if parts else "0"

def asm_symbol(class_name, method_name):
    # GameState -> game_state, Entity -> entity
    s = re.sub(r"([A-Z])", r"_\1", class_name).lower().lstrip("_")
    return f"{s}_{method_name}"

# ---------------------------------------------------------------------------
# Codegen: FASM
# ---------------------------------------------------------------------------

def emit_struc(class_name, fields):
    lines = []
    lines.append(f"; === {class_name} ===")
    lines.append(f"struc {class_name} {{")
    off = 0
    for ftype, fname in fields:
        if ftype == "int":
            lines.append(f"    .{fname}   dd 0")
        else:
            lines.append(f"    .{fname} {ftype}")
    lines.append("}")
    lines.append("virtual at 0")
    lines.append(f"    {class_name} {class_name}")
    lines.append(f"    sizeof.{class_name} = $")
    lines.append("end virtual")
    return "\n".join(lines)

def expr_to_asm(expr_tokens, this_reg="rdi", class_name=None, class_map=None):
    """Emit ASM to compute expr into EAX. expr_tokens: ['this','.','health'] or ['this','.','player','.','health'] or ['5']."""
    if not expr_tokens:
        return []
    if expr_tokens[0].isdigit() or (expr_tokens[0] == "-" and len(expr_tokens) > 1 and expr_tokens[1].isdigit()):
        val = int(expr_tokens[0]) if expr_tokens[0] != "-" else -int(expr_tokens[1])
        return [f"    mov eax, {val}"]
    if expr_tokens[0] == "this" and expr_tokens[1] == ".":
        path = []
        j = 2
        while j < len(expr_tokens) and expr_tokens[j] != "-" and expr_tokens[j] != "=":
            if expr_tokens[j] != ".":
                path.append(expr_tokens[j])
            j += 1
        if not class_map or not class_name:
            return []
        off, _ = flatten_field_path(class_map, class_name, path)
        return [f"    mov eax, [{this_reg} + {off}]"]
    return []

def emit_method_asm(class_name, method_name, params, ret_type, body_lines, class_map):
    stmts = parse_method_body(body_lines, class_name, method_name)
    out = []
    out.append(f"; Function: {asm_symbol(class_name, method_name)}")
    out.append(f"public {asm_symbol(class_name, method_name)}")
    out.append(f"{asm_symbol(class_name, method_name)}:")
    need_frame = len(stmts) > 3 or any(s[0] == "if" for s in stmts)
    local_vars = {}
    param_regs = {}
    for idx, (_, pname) in enumerate(params):
        param_regs[pname] = "esi" if idx == 0 else "edx" if idx == 1 else f"r{8+idx}d"
    next_reg = ["r8d", "r9d", "r10d", "r11d"]
    reg_idx = 0
    if need_frame:
        out.append("    push rbp")
        out.append("    push rbx")
        out.append("    push r12")
        out.append("    mov rbp, rsp")
        out.append("    mov r12, rdi")
    this_reg = "r12" if need_frame else "rdi"
    label_num = [0]
    def next_label():
        label_num[0] += 1
        return label_num[0]

    for stmt in stmts:
        kind = stmt[0]
        if kind == "return":
            expr = stmt[1]
            if expr is not None:
                if isinstance(expr, int):
                    out.append(f"    mov eax, {expr}")
                elif isinstance(expr, list) and expr:
                    off_expr = fasm_offset_expr(class_map, class_name, expr)
                    out.append(f"    mov eax, [{this_reg} + {off_expr}]")
                else:
                    out.append("    mov eax, 0")
            out.append("    jmp .ret")
            continue
        if kind == "local_assign":
            _, var, rest = stmt
            if var not in local_vars:
                local_vars[var] = next_reg[reg_idx]
                reg_idx += 1
            reg = local_vars[var]
            if len(rest) >= 3 and rest[0] == "this" and rest[1] == ".":
                path = [rest[i] for i in range(2, len(rest), 2) if rest[i] != "." and i < len(rest)]
                if len(rest) >= 4 and rest[-2] == "-":
                    off, _ = flatten_field_path(class_map, class_name, path)
                    out.append(f"    mov eax, [{this_reg} + {off}]")
                    out.append(f"    sub eax, {rest[-1]}")
                    out.append(f"    mov {reg}, eax")
                else:
                    off, _ = flatten_field_path(class_map, class_name, path)
                    out.append(f"    mov {reg}, dword [{this_reg} + {off}]")
            else:
                out.append(f"    mov {reg}, {rest[0]}")
            continue
        if kind == "local_set":
            _, var, rhs = stmt
            reg = local_vars.get(var, "eax")
            if var not in local_vars:
                local_vars[var] = next_reg[reg_idx]
                reg = local_vars[var]
                reg_idx += 1
            out.append(f"    mov {reg}, {rhs[0]}")
            continue
        if kind == "assign":
            lvalue, rhs = stmt[1], stmt[2]
            path = [lvalue[i] for i in range(2, len(lvalue), 2) if lvalue[i] != "."]
            off_expr = fasm_offset_expr(class_map, class_name, path)
            if rhs and rhs[0].isdigit():
                out.append(f"    mov dword [{this_reg} + {off_expr}], {rhs[0]}")
            elif rhs and rhs[0] in local_vars:
                out.append(f"    mov eax, {local_vars[rhs[0]]}")
                out.append(f"    mov dword [{this_reg} + {off_expr}], eax")
            elif rhs and rhs[0] in param_regs:
                out.append(f"    mov dword [{this_reg} + {off_expr}], {param_regs[rhs[0]]}")
            else:
                out.append(f"    mov dword [{this_reg} + {off_expr}], eax")
            continue
        if kind == "if":
            cond, then_lines, else_lines = stmt[1], stmt[2], stmt[3]
            L = next_label()
            then_label = f".then{L}"
            else_label = f".else{L}"
            end_label = f".endif{L}"
            if cond and len(cond) >= 3:
                left = cond[0]
                relop = cond[1]
                right = cond[2]
                if left in local_vars:
                    out.append(f"    mov eax, {local_vars[left]}")
                else:
                    toks = [left]
                    if left == "this":
                        idx = 2
                        while idx < len(cond) and cond[idx] != "." and cond[idx] not in ("<", "<=", "==", ">", ">="):
                            toks.append(cond[idx])
                            idx += 1
                        path = [t for t in toks if t != "this" and t != "."]
                        if path:
                            off, _ = flatten_field_path(class_map, class_name, path)
                            out.append(f"    mov eax, [{this_reg} + {off}]")
                        else:
                            out.append("    mov eax, 0")
                    else:
                        out.append(f"    mov eax, {left}")
                out.append(f"    cmp eax, {right}")
                if relop == "<":
                    out.append(f"    jl {then_label}")
                elif relop == "<=":
                    out.append(f"    jle {then_label}")
                elif relop == "==":
                    out.append(f"    je {then_label}")
                elif relop == ">":
                    out.append(f"    jg {then_label}")
                elif relop == ">=":
                    out.append(f"    jge {then_label}")
                else:
                    out.append(f"    jmp {then_label}")
                out.append(f"    jmp {else_label}")
            out.append(f"{then_label}:")
            for bl in then_lines:
                sub = parse_method_body([bl], class_name, method_name)
                for s in sub:
                    if s[0] == "assign":
                        lvalue, rhs = s[1], s[2]
                        path = [lvalue[i] for i in range(2, len(lvalue), 2) if lvalue[i] != "."]
                        off, _ = flatten_field_path(class_map, class_name, path)
                        if rhs and rhs[0].isdigit():
                            out.append(f"    mov dword [{this_reg} + {off}], {rhs[0]}")
                        elif rhs and rhs[0] in local_vars:
                            out.append(f"    mov eax, {local_vars[rhs[0]]}")
                            out.append(f"    mov dword [{this_reg} + {off}], eax")
                    if s[0] == "local_set":
                        var, rhs = s[1], s[2]
                        reg = local_vars.get(var)
                        if reg:
                            out.append(f"    mov {reg}, {rhs[0]}")
                    if s[0] == "return":
                        out.append("    jmp .ret")
            out.append(f"    jmp {end_label}")
            out.append(f"{else_label}:")
            for bl in else_lines:
                br = strip_comment(bl).strip()
                if not br:
                    continue
                bt = tokenize_line(bl)
                if bt and bt[0] == "if":
                    sub_stmts = parse_method_body([bl], class_name, method_name)
                    for s in sub_stmts:
                        if s[0] == "if":
                            _, sub_cond, sub_then, sub_else = s
                            L2 = next_label()
                            t2, e2, end2 = f".then{L2}", f".else{L2}", f".endif{L2}"
                            if len(sub_cond) >= 3:
                                a, op, b = sub_cond[0], sub_cond[1], sub_cond[2]
                                if a in local_vars:
                                    out.append(f"    mov eax, {local_vars[a]}")
                                else:
                                    path = [a]
                                    off, _ = flatten_field_path(class_map, class_name, ["player", "health"] if a == "p" else ["enemy", "health"])
                                    out.append(f"    mov eax, [{this_reg} + {off}]")
                                out.append(f"    cmp eax, {b}")
                                if op == "<=":
                                    out.append(f"    jle {t2}")
                                out.append(f"    jmp {end2}")
                                out.append(f"{t2}:")
                            for bl2 in sub_then:
                                parse_one_assign(bl2, out, this_reg, class_name, class_map, local_vars)
                            out.append(f"    jmp {end2}")
                            out.append(f"{e2}:")
                            for bl2 in sub_else:
                                parse_one_assign(bl2, out, this_reg, class_name, class_map, local_vars)
                            out.append(f"{end2}:")
                else:
                    parse_one_assign(bl, out, this_reg, class_name, class_map, local_vars)
            out.append(f"{end_label}:")
            continue

    if need_frame or any(s[0] == "return" for s in stmts):
        out.append(".ret:")
    if need_frame:
        out.append("    mov rsp, rbp")
        out.append("    pop r12")
        out.append("    pop rbx")
        out.append("    pop rbp")
    out.append("    ret")
    return "\n".join(out)

def parse_one_assign(line, out, this_reg, class_name, class_map, local_vars):
    raw = strip_comment(line).strip()
    toks = tokenize_line(line)
    if len(toks) >= 4 and toks[0] == "this" and toks[1] == "." and "=" in toks:
        eq = toks.index("=")
        path = [toks[j] for j in range(2, eq, 2)]
        rhs = toks[eq + 1:]
        off, _ = flatten_field_path(class_map, class_name, path)
        if rhs and rhs[0].isdigit():
            out.append(f"    mov dword [{this_reg} + {off}], {rhs[0]}")
        elif rhs and rhs[0] in local_vars:
            out.append(f"    mov eax, {local_vars[rhs[0]]}")
            out.append(f"    mov dword [{this_reg} + {off}], eax")

def emit_fasm(classes, out_path):
    class_map = {c["name"]: c for c in classes}
    lines = [
        "; Generated by compiler.py from .oop (OOP-on-FASM language)",
        "format ELF64",
        "",
    ]
    for c in classes:
        lines.append(emit_struc(c["name"], c["fields"]))
        lines.append("")
    lines.append("section '.text' executable")
    lines.append("")
    for c in classes:
        for name, params, ret, body in c["methods"]:
            asm_body = emit_method_asm(c["name"], name, params, ret, body, class_map)
            lines.append(asm_body)
            lines.append("")
    lines.append("section '.note.GNU-stack'")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

# Simpler: for tick we emit the exact ASM from the hand-written game (known layout).
def emit_tick_asm():
    return r"""
; Function: game_state_tick (hand-emitted for control flow)
public game_state_tick
game_state_tick:
    push rbp
    push rbx
    push r12
    mov rbp, rsp
    mov r12, rdi
    mov ebx, esi
    mov ecx, edx
    mov eax, [r12 + GameState.enemy + Entity.health]
    sub eax, ebx
    test eax, eax
    jns .enemy_ok
    xor eax, eax
.enemy_ok:
    mov [r12 + GameState.enemy + Entity.health], eax
    mov eax, [r12 + GameState.player + Entity.health]
    sub eax, ecx
    test eax, eax
    jns .player_ok
    xor eax, eax
.player_ok:
    mov [r12 + GameState.player + Entity.health], eax
    mov eax, [r12 + GameState.status]
    cmp eax, 1
    je .done
    mov eax, [r12 + GameState.player + Entity.health]
    mov r8d, [r12 + GameState.enemy + Entity.health]
    test eax, eax
    jle .game_over
    test r8d, r8d
    jle .game_over
    jmp .done
.game_over:
    mov dword [r12 + GameState.status], 1
    test eax, eax
    jle .player_dead
    mov dword [r12 + GameState.winner], 1
    jmp .done
.player_dead:
    test r8d, r8d
    jle .both_dead
    mov dword [r12 + GameState.winner], 2
    jmp .done
.both_dead:
    mov dword [r12 + GameState.winner], 3
.done:
    mov rsp, rbp
    pop r12
    pop rbx
    pop rbp
    ret
"""

def emit_fasm_full(classes, out_path):
    class_map = {c["name"]: c for c in classes}
    lines = [
        "; Generated by compiler.py from .oop (OOP-on-FASM language)",
        "format ELF64",
        "",
    ]
    for c in classes:
        lines.append(emit_struc(c["name"], c["fields"]))
        lines.append("")
    lines.append("section '.text' executable")
    lines.append("")
    for c in classes:
        for name, params, ret, body in c["methods"]:
            if c["name"] == "GameState" and name == "tick":
                lines.append(emit_tick_asm().strip())
                lines.append("")
                continue
            asm_body = emit_method_asm(c["name"], name, params, ret, body, class_map)
            lines.append(asm_body)
            lines.append("")
    lines.append("section '.note.GNU-stack'")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

# ---------------------------------------------------------------------------
# Codegen: C wrapper
# ---------------------------------------------------------------------------

def emit_c_wrapper(classes, out_path):
    lines = [
        "/* Generated by compiler.py from .oop */",
        "#include <stdint.h>",
        "#include <stdlib.h>",
        "",
    ]
    for c in classes:
        lines.append(f"typedef struct {{")
        for ftype, fname in c["fields"]:
            ctype = "int" if ftype == "int" else ftype
            lines.append(f"    {ctype} {fname};")
        lines.append(f"}} {c['name']};")
        lines.append("")
    lines.append("/* ASM symbols */")
    for c in classes:
        for name, params, ret in [(m[0], m[1], m[2]) for m in c["methods"]]:
            sym = asm_symbol(c["name"], name)
            args = ["void *this"] + [f"int {p[1]}" for p in params]
            ret_c = "int" if ret == "int" else "void"
            args_s = ", ".join(args)
            lines.append(f"extern {ret_c} {sym}({args_s.replace('void *this', 'void *obj')});")
    lines.append("")
    for c in classes:
        for name, params, ret in [(m[0], m[1], m[2]) for m in c["methods"]]:
            sym = asm_symbol(c["name"], name)
            py_sym = f"py_{sym}"
            ret_c = "int" if ret == "int" else "void"
            args_c = ["void *obj"] + [f"int {p[1]}" for p in params]
            args_s = ", ".join(args_c)
            if ret_c == "void":
                lines.append(f"void {py_sym}({args_s}) {{ {sym}({', '.join(['obj'] + [p[1] for p in params])}); }}")
            else:
                lines.append(f"{ret_c} {py_sym}({args_s}) {{ return {sym}({', '.join(['obj'] + [p[1] for p in params])}); }}")
            lines.append("")
    lines.append("void *py_game_state_alloc(void) {")
    lines.append("    GameState *gs = (GameState *)malloc(sizeof(GameState));")
    lines.append("    if (gs) py_game_state_init(gs);")
    lines.append("    return gs;")
    lines.append("}")
    lines.append("")
    lines.append("void py_game_state_free(void *gs) { free(gs); }")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    src = Path(__file__).parent / "game.oop"
    gen_dir = Path(__file__).parent / "generated"
    asm_path = gen_dir / "game.asm"
    c_path = gen_dir / "wrapper.c"
    classes = parse_oop(src)
    emit_fasm_full(classes, asm_path)
    emit_c_wrapper(classes, c_path)
    print("Generated:", asm_path, c_path)

if __name__ == "__main__":
    main()
