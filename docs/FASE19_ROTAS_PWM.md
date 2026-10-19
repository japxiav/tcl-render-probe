# Fase 19 · Rota alternativa de telemetria: GetDvPwmInfo (162)

Data: 19/10/2026. TCL C6K 55", V643. **Análise estática offline** das bibliotecas originais, sem leitura de PWM no hardware nesta fase.

## Por que mudamos de rota

A operação AIDL `GetLdmBlockData` (158) apresenta uma incompatibilidade suspeita de ponteiros/capacidade do vetor de retorno. Está **bloqueada** no executável. `GetLdmBlockNum` (147) confirmou na TV `18 × 10 = 180`, e `GetDimmingDutyInfo` (143) deu `0,0,255` em duas amostras. Nenhuma delas comprovou PWM por zona.

## Três candidatos pesquisados

| Leitura | AIDL | MediaTek | Potencial | Limitações |
|---|---:|---|---|---|
| `GetDvPwmInfo` | **162 (0xa2)** | `MI_RENDER_GetDvPwmInfo`, `0x79d94` | Dois bytes derivados de resposta do driver; possível telemetria PWM | Pode ser PWM global ou específico de Dolby Vision. Significado dos bytes desconhecido |
| `GetBacklightStatus` | **169 (0xa9)** | `MI_RENDER_GetBacklightStatus`, `0x7b1d8` | Um indicador booleano de estado de backlight | Não corresponde ao nível nem ao mapa de 180 zonas |
| `GetDimmingControlInfo` | **145 (0x91)** | `MI_RENDER_GetDimmingControlInfo`, `0x76370` | Informações globais do controle de dimming | Exige estrutura de entrada de seleção; não autorizar até mapear valores |

**Outra pista que não comprova iluminação por zona:** `PQBase::videoGetMicroDimmingData` em `libtpq.so`, `0x7a5e8`. O nome é promissor, mas é uma interface de microdimming do processamento de vídeo, sem evidência de acesso à luminosidade real dos 180 LEDs; exige exame dos chamadores e da memória de saída.

## Análise do GetDvPwmInfo

Hashes SHA-256 das bibliotecas utilizadas:

- `vendor.mediatek.hardware.render-V1-ndk.so`: `de7d548884f7fadd141e9bce9a075039367ccb6a3065cfc23bdba09350254ed0`.
- `vendor.mediatek.hardware.render-impl.so`: `7daa84de2d0b306fa0704498d0b8f10ddff51d812de34225c9598b9c1655ec7c`.
- `libmi3_hwc_hal.so`: `608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500`.

Evidências específicas:

1. `BpRender::GetDvPwmInfo` em `render-V1-ndk.so`, `0x3adb4`, usa **transação 0xa2 = 162**.
2. `MI_RENDER_GetDvPwmInfo` (`libmi3_hwc_hal.so`) compara o seletor `0xF1FFFFFF` em `0x79de4–0x79dea`, mesmo valor já validado no GetLdmBlockNum.
3. Em `0x79e10–0x79e30`, a HAL inicializa um **uint16 local**, consulta `drmIoctl` e grava os 16 bits na estrutura de saída quando a consulta retorna normalmente. O ioctl é caminho interno do fornecedor, **não é autorizado para chamadas manuais**.
4. `Render::GetDvPwmInfo` (`render-impl.so`), na rota `0x2f0f4–0x2f0fe`, lê **dois bytes** da saída local e retorna à serialização AIDL; o ramo geral em `0x2f0a8–0x2f0ae` constrói o `uint16` a partir dos bytes.
5. `ST_DV_PWM_INFO::writeToParcel` na AIDL, `0x4b9d6` e `0x4b9e4`, escreve **dois int8**, não `int16[]` nem `vector`. `RetGetDvPwmInfo::writeToParcel`, `0x4464c`, escreve resultado inteiro e campo aninhado.
6. Nenhum vetor de comprimento variável foi identificado no caminho de retorno desta consulta. **Isto reduz um risco específico**, mas não garante segurança absoluta para driver proprietário.

## TCL Render Probe v0.5

Foi acrescentado **exclusivamente** o modo voluntário `--read-dv-pwm`, que envia só o seletor fixo `0xF1FFFFFF` à transação 162, valida o código de retorno e decodifica **dois bytes** em representação bruta. Os números só devem ser interpretados após comparação com diferentes conteúdos e modos de vídeo. `--read-block-data` não existe e 158 continua bloqueada.

A v0.5 **não foi executada na TV durante esta fase**. GitHub Actions testa o build ARM32 e as regressões de bloqueio da 158.

### Potencial próximo experimento (opcional e isolado)

Depois de compilação aprovada, executar uma única vez `--read-dv-pwm` com a TV em condições normais, sem alterar configuração. Se houver erro, interromper. Não assumir que mudança do PWM equivale a mudança de uma zona física. Se o objetivo for confirmar sensibilidade ao conteúdo, comparar de forma controlada estados SDR/HDR/Dolby Vision e níveis estáveis, sempre com cautela.

## Resumo

**Comprovado:** o firmware fornece rota nativa de pequena resposta associada a DV PWM. **Não comprovado:** acesso a PWM individual, escala de brilho, resposta dinâmica, estabilidade de leitura e segurança absoluta na C6K real.
