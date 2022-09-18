extern printf
global main
section .text
main:
    push 22
    push 11
    pop rax
    pop rbx
    sub rbx, rax
    push rbx
    mov rdi,printf_format
    mov rsi,rax
    call printf
    mov rax,60	; exit
    syscall
section .data
    printf_format: db '%d',10,0
