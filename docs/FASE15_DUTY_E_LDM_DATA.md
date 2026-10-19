# TCL C6K V643 · Fase 15 — Duty estático e risco da operação 158

**Data:** 2026-10-19. **Método:** leitura experimental pelo usuário + revisão estática *offline* de binários MediaTek.

## Resultado observado de GetDimmingDutyInfo (143)

O usuário executou duas vezes `adb shell /data/local/tmp/tcl_render_probe --read-duty` com o resultado idêntico em ambas:

```text
RENDER_SERVICE_PING_OK
duty_result_code=0 nested_present=1
duty_fields_raw=0,0,255 (semantics unknown)
DUTY_READ_COMPLETED: raw fields only; not a 180-zone brightness map.
```

**Fato:** não houve diferença entre as duas amostras. A saída não especifica o que estava sendo exibido na TV em cada amostra; correlação com imagem preta vs. clara depende dessa confirmação. O número 255 é um valor de 8 bits observado, e **não** prova brilho de 100%, PWM ou duty percentual.

## Análise offline da operação 158 — por que continua bloqueada

Bibliotecas V643 analisadas:

- `vendor.mediatek.hardware.render-impl.so`, função `Render::GetLdmBlockData`, endereço Thumb **0x2e814**;
- `libmi3_hwc_hal.so`, função `MI_RENDER_GetLdmBlockData`, endereço Thumb **0x78440**;
- `vendor.mediatek.hardware.render-V1-ndk.so`, serialização AIDL de `ST_LDM_BLOCK_DATA_INFO` e `RetGetLdmBlockData`.

### Estruturas e tamanho

Na entrada AIDL, `ST_LDM_BLOCK_DATA_INFO` contém tipo (`int32`), vetor de unidades de 16 bits e comprimento (`int64`).

Na implementação do serviço:

1. `0x2e83c–0x2e846`: inicializa **16 bytes** no stack (`sp+0x10…0x1f`) com zero.
2. `0x2e854`: lê o **primeiro word** do comprimento de 64 bits na entrada (`input+0x10`). Em `0x2e862`, essa contagem é usada para dimensionar um vetor temporário de elementos de 16 bits.
3. `0x2e866–0x2e86a`: grava o ponteiro para o vetor na posição `sp+0x14` da estrutura nativa temporária. Em `0x2e8b0`, grava o tipo em `sp+0x10`.
4. `0x2e8c4–0x2e8c8`: entrega o endereço de `sp+0x10` à função HAL nativa. **Não foi identificada gravação em `sp+0x18`** entre a inicialização com zero e a chamada (campo nativo de comprimento).
5. O HAL em `0x784ea–0x784fc` usa o comprimento em **`native+8`** para validar contra o buffer DRM; em `0x785e6–0x785ec`, `__aeabi_memcpy8` copia o comprimento nativo para o destino. Se estiver zerado, a chamada pode não copiar dados apesar de `result_code=0`.
6. A implementação Render usa em `0x2e91e–0x2e92c` um **`__aeabi_memcpy`** com o comprimento solicitado na entrada (`input+0x10`) e ponteiros de vetor. O destino é obtido de `RetGetLdmBlockData+0x0c`. É necessário validar rigorosamente o estado e a capacidade desse vetor antes de supor segurança com comprimento diferente de zero.

### Consequência

Há uma **assimetria suspeita**: o serviço dimensiona um vetor com base no comprimento do AIDL, mas aparentemente passa **comprimento nativo zero** para a HAL. Além disso, existe uma cópia posterior baseada no comprimento solicitado. Esses detalhes precisam ser resolvidos antes de qualquer requisição real.

Não se pode concluir ainda que a API sempre retorna zeros, nem que seja inútil. Entretanto, **não é responsável executar uma chamada de teste arbitrária**, porque buffers nativos, driver DRM e estado de processo privilegiado estão envolvidos. Uma operação nominalmente de leitura pode falhar ou interromper o serviço gráfico da TV.

## Situação comprovada

- AIDL 147 (GetLdmBlockNum): **18 × 10 = 180** com seletor `0xF1FFFFFF` e retorno `0`.
- AIDL 143 (GetDimmingDutyInfo): duas amostras `0,0,255`, sem diferença observada.
- AIDL 158 (GetLdmBlockData): **não executada**; ainda sem validação segura de tamanho/buffers.
- Nenhuma operação `SetLdm*`, `drmIoctl` manual, root ou firmware modificado foi usada.

## Próximos passos que não exigem acesso à TV

1. Confirmar se o stack `sp+0x18` recebe comprimento em algum caminho alternativo (e o que representa esse campo no ABI nativo).
2. Examinar a inicialização e a capacidade do vetor de saída `RetGetLdmBlockData` no binder stub e em chamadores legítimos.
3. Criar testes unitários locais de serialização AIDL **sem chamar o serviço**, inclusive limites, retorno nulo e overflow.
4. Só considerar uma consulta no aparelho após avaliação explícita de risco e mapeamento de tamanho, tipo e destino de memória.

**Decisão:** encerrar experimentos com `--read-duty`; bloquear `--read-block-data` até resolver os itens acima.
