format ELF64 executable 3
entry main

include "../core/platform.inc"

BUFFER_SIZE equ 1024

segment readable executable

main:
	write_file STDOUT, start_msg, start_msg_len

	open_file filename, O_RDONLY, 0
	jump_if_syscall_error open_failed
	mov r12, rax

.read_loop:
	read_file r12, buffer, BUFFER_SIZE
	jump_if_syscall_error read_failed
	test rax, rax
	jz .done
	mov r15, rax
	write_file STDOUT, buffer, r15
	jump_if_syscall_error read_failed
	jmp .read_loop

.done:
	close_file r12
	exit EXIT_SUCCESS

open_failed:
	write_file STDERR, open_failed_msg, open_failed_msg_len
	exit EXIT_FAILURE

read_failed:
	write_file STDERR, read_failed_msg, read_failed_msg_len
	exit EXIT_FAILURE

segment readable writeable

filename db "lol.txt", 0
buffer rb BUFFER_SIZE

start_msg db "Start", 10
start_msg_len = $ - start_msg
open_failed_msg db "Failed to open lol.txt", 10
open_failed_msg_len = $ - open_failed_msg
read_failed_msg db "Failed to read lol.txt", 10
read_failed_msg_len = $ - read_failed_msg
