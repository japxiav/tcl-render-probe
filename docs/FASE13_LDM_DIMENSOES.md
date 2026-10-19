# TCL C6K V643 · Fase 13 · Primeira leitura LDM independente

Data: 2026-10-19. Modelo: TCL 55C6K, Android 14, MediaTek.

## Evidência de execução real

Saída informada pelo usuário, executando o artefato ARM32 do Build #13 com `--read-block-num-native`:

```text
RENDER_SERVICE_PING_OK
EXPERIMENTAL_NATIVE_SELECTOR: signed=-234881025 hex=0xf1ffffff
result_code=0 nested_present=1
reported_type=0 width=18 height=10 product=180
READ_ONLY_QUERY_COMPLETED (dimensions not yet validated against hardware).
```

- Serviço: `vendor.mediatek.hardware.render.IRender/default`.
- Transação AIDL: `147` (`GetLdmBlockNum`), somente leitura.
- Seletor: `0xF1FFFFFF`, localizado em `MI_RENDER_GetLdmBlockNum` (libmi3_hwc_hal.so).
- Tipo informado na resposta: `0`.
- Resposta: `result_code=0`; largura `18`; altura `10`; produto `180`.
- A API TCL anterior também relatava 18 linhas e 10 colunas. O número de posições é coerente com 180 blocos, mas não prova telemetria por bloco em tempo real.

## Limites do experimento

- O `ping` é apenas conectividade Binder.
- `GetLdmBlockNum` consulta dimensões dos blocos, **não** o brilho, PWM ou mapa dinâmico das zonas.
- Não foi realizado root ou gravação de firmware; o teste chamou uma operação de leitura AIDL.
- O significado formal do seletor `0xF1FFFFFF` permanece desconhecido.
- A saída `result_code=0` valida o êxito reportado pela função; não prova a existência de uma API pública, estável ou segura para terceiros.

## Próximo marco técnico

Reconstruir offline a serialização de `GetLdmBlockData` (transação 158), identificando e limitando rigorosamente:

1. Semântica dos tipos de dado `0/1/2`.
2. Unidade do campo `int64` de tamanho (bytes ou elementos), limites máximos e relação com DMA.
3. Papel do vetor de entrada `char16` e formato do retorno `RetGetLdmBlockData`.
4. Falhas possíveis de permissão, ausência de suporte, alocação de buffer e parâmetros incorretos.

**Não enviar transação 158 à TV antes de validar os argumentos. Não chamar diretamente `drmIoctl`. Não executar operações `SetLdm*`.**

As bibliotecas offline já disponíveis para análise são: `vendor.mediatek.hardware.render-V1-ndk.so`, `vendor.mediatek.hardware.render-impl.so`, `libmi3_hwc_hal.so`.
