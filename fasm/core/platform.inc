; Platform syscall layer for small runnable examples.
;
; The fasm-mac shim passes `-d TARGET_OS=macos` for Mach-O output and
; `-d TARGET_OS=linux` for ELF output. Use one of those values when invoking
; the upstream fasm host directly.

match =macos, TARGET_OS {
	SYS_exit equ 02000001h
	SYS_read equ 02000003h
	SYS_write equ 02000004h
	SYS_open equ 02000005h
	SYS_close equ 02000006h
	SYS_lseek equ 020000C7h

	O_RDONLY equ 0000h
	O_WRONLY equ 0001h
	O_RDWR equ 0002h
	O_CREAT equ 0200h
	O_TRUNC equ 0400h
	O_APPEND equ 0008h
}

match =linux, TARGET_OS {
	SYS_read equ 0
	SYS_write equ 1
	SYS_open equ 2
	SYS_close equ 3
	SYS_lseek equ 8
	SYS_exit equ 60

	O_RDONLY equ 0
	O_WRONLY equ 1
	O_RDWR equ 2
	O_CREAT equ 64
	O_TRUNC equ 512
	O_APPEND equ 1024
}

STDIN equ 0
STDOUT equ 1
STDERR equ 2

EXIT_SUCCESS equ 0
EXIT_FAILURE equ 1

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

macro jump_if_syscall_error target
{
	match =macos, TARGET_OS \{
		jc target
	\}
	match =linux, TARGET_OS \{
		test rax, rax
		js target
	\}
}
