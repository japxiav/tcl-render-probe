# Fase 14 · Consulta somente leitura de dimming duty

**TCL C6K / V643 · 19/10/2026**

A Fase 13 obteve `GetLdmBlockNum` (AIDL 147) usando o seletor `0xF1FFFFFF`, retornando `result_code=0`, `width=18` e `height=10` (180 blocos).

## Nova operação

`GetDimmingDutyInfo(int, RetGetDimmingDutyInfo*)` é uma leitura declarada na AIDL do fornecedor MediaTek.

- `BpRender::GetDimmingDutyInfo` em `vendor.mediatek.hardware.render-V1-ndk.so` prepara a transação **143** (`0x8f`).
- `MI_RENDER_GetDimmingDutyInfo` em `libmi3_hwc_hal.so`, endereço `0x75e6c`, verifica o seletor especial `0xF1FFFFFF` e encaminha uma consulta DRM.
- `RetGetDimmingDutyInfo` contém um código de resultado e um objeto aninhado `ST_DIMMING_DUTY_INFO`.
- `ST_DIMMING_DUTY_INFO::writeToParcel` (ELF `0x4b55c`) grava três campos `int32` após o cabeçalho de tamanho; o significado e as unidades dos campos ainda não estão estabelecidos.

A v0.4 adicionou `--read-duty` com **somente a transação de consulta 143**, uma chamada por execução. A resposta é limitada a tamanhos pequenos e exibe os três campos como números brutos. Nenhuma operação de escrita do painel foi adicionada.

## Teste de referência

Após baixar o artefato do Build #14, substituir o programa em `/data/local/tmp`, rodar uma única vez:

```cmd
adb shell /data/local/tmp/tcl_render_probe --read-duty
```

O código de retorno do serviço pode indicar indisponibilidade, acesso negado ou ausência de dados. Interromper após um erro ou um comportamento anormal.

## Importante: operação 158 permanece bloqueada

A estrutura `ST_LDM_BLOCK_DATA_INFO` contém um tipo, um vetor `char16_t` e um `int64`. O caminho de leitura inferior manipula DMA/DRM e copia dados para um buffer. O relacionamento entre **tamanho do vetor, contagem de elementos, comprimento da cópia e estado do buffer** não foi validado o suficiente para testar em hardware sem riscos adicionais.

A saída da operação 143, mesmo bem-sucedida, **não deve ser descrita como intensidade individual das 180 zonas** antes de ser interpretada e correlacionada com o conteúdo exibido na TV.
