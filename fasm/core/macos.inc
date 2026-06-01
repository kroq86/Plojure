; Common Darwin/macOS x86_64 syscall definitions for runnable examples.

SYS_exit equ 02000001h
SYS_read equ 02000003h
SYS_write equ 02000004h
SYS_open equ 02000005h
SYS_close equ 02000006h
SYS_lseek equ 020000C7h
SYS_mmap equ 020000C5h

STDIN equ 0
STDOUT equ 1
STDERR equ 2

EXIT_SUCCESS equ 0
EXIT_FAILURE equ 1

O_RDONLY equ 0000h
O_WRONLY equ 0001h
O_RDWR equ 0002h
O_CREAT equ 0200h
O_TRUNC equ 0400h
O_APPEND equ 0008h

macro syscall1 number, a
{
	mov rax, number
	mov rdi, a
	syscall
}

macro syscall2 number, a, b
{
	mov rax, number
	mov rdi, a
	mov rsi, b
	syscall
}

macro syscall3 number, a, b, c
{
	mov rax, number
	mov rdi, a
	mov rsi, b
	mov rdx, c
	syscall
}

macro syscall4 number, a, b, c, d
{
	mov rax, number
	mov rdi, a
	mov rsi, b
	mov rdx, c
	mov r10, d
	syscall
}

macro syscall6 number, a, b, c, d, e, f
{
	mov rax, number
	mov rdi, a
	mov rsi, b
	mov rdx, c
	mov r10, d
	mov r8, e
	mov r9, f
	syscall
}

macro exit code
{
	mov rax, SYS_exit
	mov rdi, code
	syscall
}

macro open_file filename, flags, mode
{
	syscall3 SYS_open, filename, flags, mode
}

macro read_file fd, buffer, size
{
	syscall3 SYS_read, fd, buffer, size
}

macro write_file fd, buffer, size
{
	syscall3 SYS_write, fd, buffer, size
}

macro close_file fd
{
	syscall1 SYS_close, fd
}
