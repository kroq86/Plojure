format ELF64 executable 3
entry main

include "../core/platform.inc"

segment readable executable

main:
	mov r12, 1
	mov r13, 1
	mov r14, 10

.loop:
	mov rdi, r12
	call print_u64

	mov rax, r12
	add rax, r13
	mov r12, r13
	mov r13, rax

	dec r14
	jnz .loop

	exit EXIT_SUCCESS

print_u64:
	lea rsi, [number_buffer + 31]
	mov byte [rsi], 10
	mov rcx, 10

.digit:
	xor rdx, rdx
	mov rax, rdi
	div rcx
	add dl, '0'
	dec rsi
	mov [rsi], dl
	mov rdi, rax
	test rax, rax
	jnz .digit

	lea rdx, [number_buffer + 32]
	sub rdx, rsi
	syscall3 SYS_write, STDOUT, rsi, rdx
	ret

segment readable writeable

number_buffer rb 32
