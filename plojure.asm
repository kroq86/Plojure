extern printf
global main
section .text
main:
    push 23
    push 22
    pop rax
    pop rbx
    sub rax, rbx
    push rax
    mov rdi,printf_format
    mov rsi,rax
    xor rax,rax
    call printf
    push 23
    push 11
    pop rax
    pop rbx
    add rax, rbx
    push rax
    mov rdi,printf_format
    mov rsi,rax
    xor rax,rax
    call printf
    mov rax,60	; exit
    syscall
section .data
    printf_format: db '%d',10,0
