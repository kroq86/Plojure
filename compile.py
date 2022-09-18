def compile_program(program):
    with open("plojure.asm", "w") as asm:
        asm.write("extern printf\n")
        asm.write("global main\n")
        asm.write("section .text\n")
        asm.write("main:\n")
        dct = {
            "move":
            lambda: asm.write("    push %d\n" % _[1]),
            "plus":
            lambda:
            (asm.write("    pop rax\n"), asm.write("    pop rbx\n"),
             asm.write("    add rax, rbx\n"), asm.write("    push rax\n")),
            "minus":
            lambda:
            (asm.write("    pop rax\n"), asm.write("    pop rbx\n"),
             asm.write("    sub rbx, rax\n"), asm.write("    push rbx\n")),
            "dump":
            lambda:
            (asm.write("    mov rdi,printf_format\n"),
             asm.write("    mov rsi,rax\n"), asm.write("    xor rax,rax\n"),
             asm.write("    call printf\n"))
        }
        for _ in program:
            dct[str(_[0][1])]()
        asm.write("    mov rax,60	; exit\n")
        asm.write("    syscall\n")
        asm.write("section .data\n")
        asm.write("    printf_format: db '%d',10,0\n")
