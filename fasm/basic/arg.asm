format ELF64 executable 3
entry main

include "../core/platform.inc"

BUFFER_SIZE equ 1024

segment readable executable

main:
	cmp qword [rsp], 2
	jb usage_error

	mov r12, [rsp + 16]
	open_file r12, O_RDONLY, 0
	jump_if_syscall_error open_error
	mov r12, rax

.read_loop:
	read_file r12, buffer, BUFFER_SIZE
	jump_if_syscall_error read_error
	test rax, rax
	jz .done
	mov r15, rax
	write_file STDOUT, buffer, r15
	jump_if_syscall_error write_error
	jmp .read_loop

.done:
	close_file r12
	exit EXIT_SUCCESS

usage_error:
	write_file STDERR, usage_msg, usage_msg_len
	exit EXIT_FAILURE

open_error:
	write_file STDERR, open_msg, open_msg_len
	exit EXIT_FAILURE

read_error:
	write_file STDERR, read_msg, read_msg_len
	exit EXIT_FAILURE

write_error:
	exit EXIT_FAILURE

segment readable writeable

buffer rb BUFFER_SIZE

usage_msg db "usage: arg <file>", 10
usage_msg_len = $ - usage_msg
open_msg db "failed to open file", 10
open_msg_len = $ - open_msg
read_msg db "failed to read file", 10
read_msg_len = $ - read_msg
