format ELF64

public coroutine_init
public coroutine_yield
public coroutine_restore_context
public coroutine_go

coroutine_init:
    ret

coroutine_yield:
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    pushfq
    push [rsp+8*7]
    mov rax, rsp
    and rsp, -16
    ret

coroutine_restore_context:
    mov rsp, rdi
    pop [rsp]
    popfq
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret

coroutine_go:
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    pushfq
    mov rax, rsp
    mov rsp, rsi
    and rsp, -16
    call rdi
    ; clean stack
    mov rsp, rax
    popfq
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
