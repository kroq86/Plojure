format ELF64 executable 3
entry main

include "../../core/platform.inc"

segment readable executable

main:
	mov rdi, array
	mov rsi, array_size
	mov edx, 2
	call binary_search

	mov rdi, rax
	call print_i64
	exit EXIT_SUCCESS

binary_search:
	xor r8, r8
	mov r9, rsi
	dec r9

.loop:
	cmp r8, r9
	ja .not_found
	mov r10, r8
	add r10, r9
	shr r10, 1
	movzx r11d, byte [rdi + r10]
	cmp r11d, edx
	je .found
	jb .go_right
	dec r10
	mov r9, r10
	jmp .loop

.go_right:
	inc r10
	mov r8, r10
	jmp .loop

.found:
	mov rax, r10
	ret

.not_found:
	mov rax, -1
	ret

print_i64:
	cmp rdi, 0
	jge print_u64
	push rdi
	write_file STDOUT, minus_sign, 1
	pop rdi
	neg rdi

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
	write_file STDOUT, rsi, rdx
	ret

segment readable writeable

array db 1, 2, 3, 4
array_size = $ - array
minus_sign db "-"
number_buffer rb 32
