# x86-64 SysV: perceptual 8-bit luminance approximation for accent contrast.
.text
.globl rice_luma_u8
.type rice_luma_u8, @function
rice_luma_u8:
    imull $54, %edi, %edi
    imull $183, %esi, %esi
    imull $19, %edx, %edx
    leal (%rdi,%rsi), %eax
    addl %edx, %eax
    shrl $8, %eax
    ret
.size rice_luma_u8, .-rice_luma_u8
.section .note.GNU-stack,"",@progbits
