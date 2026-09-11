.section .data

archivo_entrada:
    .asciz "datos.txt"

archivo_salida:
    .asciz "resultado.txt"

txt_max:
    .asciz "MAX="

txt_min:
    .asciz "MIN="

txt_prom:
    .asciz "AVG="

txt_cant:
    .asciz "COUNT="

salto:
    .asciz "\n"


.section .bss

.lcomm buffer, 1024
.lcomm salida, 32


.section .text

.global _start


_start:

    mov x0, #-100
    ldr x1, =archivo_entrada
    mov x2, #0
    mov x3, #0
    mov x8, #56
    svc #0

    mov x19, x0

    mov x0, x19
    ldr x1, =buffer
    mov x2, #1024
    mov x8, #63
    svc #0

    mov x20, x0

    mov x21, #0
    mov x22, #0
    mov x23, #0
    mov x24, #0
    mov x25, #0
    mov x26, #0
    mov x27, #0
    mov x29, #0


leer_caracter:

    cmp x21, x20
    b.ge terminar_lectura

    ldrb w0, [x1, x21]
    add x21, x21, #1

    cmp w0, #36
    b.eq terminar_lectura

    cmp w0, #10
    b.eq procesar_numero

    cmp w0, #13
    b.eq procesar_numero

    sub w0, w0, #'0'

    mov x2, #10
    mul x26, x26, x2
    add x26, x26, x0

    mov x29, #1

    b leer_caracter


procesar_numero:

    cmp x29, #1
    b.ne reiniciar_linea

    add x23, x23, x26
    add x22, x22, #1

    cmp x27, #0
    b.eq primer_dato

    cmp x26, x24
    csel x24, x26, x24, gt

    cmp x26, x25
    csel x25, x26, x25, lt

    b reiniciar_linea


primer_dato:

    mov x24, x26
    mov x25, x26
    mov x27, #1


reiniciar_linea:

    mov x26, #0
    mov x29, #0

    b leer_caracter


terminar_lectura:

    cmp x29, #1
    b.ne calcular_promedio

    add x23, x23, x26
    add x22, x22, #1

    cmp x27, #0
    b.eq ultimo_primer_dato

    cmp x26, x24
    csel x24, x26, x24, gt

    cmp x26, x25
    csel x25, x26, x25, lt

    b calcular_promedio


ultimo_primer_dato:

    mov x24, x26
    mov x25, x26
    mov x27, #1


calcular_promedio:

    mov x0, x19
    mov x8, #57
    svc #0

    cmp x22, #0
    b.eq promedio_cero

    udiv x28, x23, x22

    b abrir_salida


promedio_cero:

    mov x28, #0


abrir_salida:

    mov x0, #-100
    ldr x1, =archivo_salida
    mov x2, #577
    mov x3, #0644
    mov x8, #56
    svc #0

    mov x19, x0


    mov x0, x19
    ldr x1, =txt_max
    mov x2, #4
    mov x8, #64
    svc #0

    mov x0, x24
    ldr x1, =salida
    bl convertir_numero

    mov x2, x0
    mov x0, x19
    ldr x1, =salida
    mov x8, #64
    svc #0

    mov x0, x19
    ldr x1, =salto
    mov x2, #1
    mov x8, #64
    svc #0


    mov x0, x19
    ldr x1, =txt_min
    mov x2, #4
    mov x8, #64
    svc #0

    mov x0, x25
    ldr x1, =salida
    bl convertir_numero

    mov x2, x0
    mov x0, x19
    ldr x1, =salida
    mov x8, #64
    svc #0

    mov x0, x19
    ldr x1, =salto
    mov x2, #1
    mov x8, #64
    svc #0


    mov x0, x19
    ldr x1, =txt_prom
    mov x2, #4
    mov x8, #64
    svc #0

    mov x0, x28
    ldr x1, =salida
    bl convertir_numero

    mov x2, x0
    mov x0, x19
    ldr x1, =salida
    mov x8, #64
    svc #0

    mov x0, x19
    ldr x1, =salto
    mov x2, #1
    mov x8, #64
    svc #0


    mov x0, x19
    ldr x1, =txt_cant
    mov x2, #6
    mov x8, #64
    svc #0

    mov x0, x22
    ldr x1, =salida
    bl convertir_numero

    mov x2, x0
    mov x0, x19
    ldr x1, =salida
    mov x8, #64
    svc #0

    mov x0, x19
    ldr x1, =salto
    mov x2, #1
    mov x8, #64
    svc #0


    mov x0, x19
    mov x8, #57
    svc #0

    mov x0, #0
    mov x8, #93
    svc #0


convertir_numero:

    mov x2, x1
    add x3, x1, #31
    mov x4, #0

    cmp x0, #0
    b.ne convertir_loop

    mov w5, #'0'
    strb w5, [x2]

    mov x0, #1
    ret


convertir_loop:

    mov x5, #10
    udiv x6, x0, x5
    msub x7, x6, x5, x0

    add w7, w7, #'0'

    sub x3, x3, #1
    strb w7, [x3]

    add x4, x4, #1

    mov x0, x6

    cbnz x0, convertir_loop

    mov x8, x3
    mov x9, x2
    mov x10, x4


copiar_loop:

    ldrb w11, [x8]
    strb w11, [x9]

    add x8, x8, #1
    add x9, x9, #1
    sub x10, x10, #1

    cbnz x10, copiar_loop

    mov x0, x4

    ret
    
