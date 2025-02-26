format ELF64
public dot_product
section '.text' executable
dot_product:
    ; Calculate dot product of two vectors
    ; Parameters:
    ;   rdi: Pointer to the first vector
    ;   rsi: Pointer to the second vector
    ;   rdx: Length of the vectors
    ; Returns:
    ;   xmm0: Dot product

    xorpd xmm0, xmm0  ; Initialize sum to 0
    mov rcx, rdx      ; Set counter to vector length
loop_start:
    movsd xmm1, qword [rdi]  ; Load element from first vector
    movsd xmm2, qword [rsi]  ; Load element from second vector
    mulsd xmm1, xmm2         ; Multiply elements
    addsd xmm0, xmm1         ; Add to sum
    add rdi, 8               ; Move to next element in first vector
    add rsi, 8               ; Move to next element in second vector
    loop loop_start
    ret
