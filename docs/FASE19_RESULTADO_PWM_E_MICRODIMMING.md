# Fase 19 · Resultado PWM real e rota alternativa MicroDimming

**TCL C6K 55 · V643 · 19/10/2026**

## Resposta real da TV

O usuário executou uma única consulta `--read-dv-pwm`, TCL Render Probe v0.5 (AIDL 162), com a saída:

```text
RENDER_SERVICE_PING_OK
dv_pwm_result_code=0 nested_present=1
dv_pwm_raw_bytes=0,0  combined_be=0 combined_le=0
DV_PWM_READ_COMPLETED: raw diagnostic only; format/units unverified.
```

A transação foi processada e retornou dados válidos de protocolo, mas os **dois bytes de PWM são zero**. A fonte de vídeo/modo SDR-HDR-Dolby Vision **não foi informada** nessa amostra; não atribuir o valor zero a DV desligado, brilho mínimo, backlight desligado ou LDM inativo.

A implementação `MI_RENDER_GetDvPwmInfo` em `libmi3_hwc_hal.so`, `0x79d94`, inicializa um valor local de 16 bits em `0x79e10`, emite `drmIoctl` em `0x79e20` e, no ramo de sucesso, copia 16 bits à saída em `0x79e2c–0x79e30`. Em `render-impl.so`, `Render::GetDvPwmInfo` em `0x2f0f4–0x2f0fe` extrai dois bytes. Portanto, **o programa não gera esses zeros artificialmente**, embora eles possam representar valor retornado pelo driver, estado padrão ou valor não significativo nessa condição.

### Próxima validação possível, sem software novo

Se houver conteúdo inequivocamente **Dolby Vision** reproduzido na TV, com a indicação Dolby Vision confirmada na interface, executar `--read-dv-pwm` **uma única vez** e comparar. Não testar em PS5 presumindo Dolby Vision nem forçar HDR com configuração desconhecida. Se não houver DV disponível, registrar a ausência de teste; não vale adivinhar outros parâmetros.

## Nova rota identificada offline: matriz MicroDimming da TCL

A biblioteca **`libtpq.so`** (SHA-256 `8313137ce090761e07a5c2f74a503a76db902a877aa9366c36266017ec5dcbbc`) contém uma implementação diferente de `TvPanelManager::getLocalDimmingData` (stub).

Funções e endereços ARM (ELF com instruções em modo ARM, **não Thumb**):
- `TvPqManagerService::getMicroLocalDimmingData(char*)` em `0x15a588`;
- `StatusMgr::getMicroDimmingBlockNum(unsigned int*,unsigned int*)` em `0x18a340`;
- `StatusMgr::getMicroDimmingData(unsigned int,unsigned int,unsigned short*)` em `0x18a650`;
- `PQBase::videoGetMicroDimmingData(unsigned int,unsigned int,unsigned short*,char const*)` em `0x7a5e8`;
- `PQBase::PQPortingMgr::videoGetMicroDimmingData(unsigned int,unsigned int,unsigned short*)` em `0x7a810`.

### Cadeia de chamadas identificada

No alto nível `getMicroLocalDimmingData`, a função:
1. Recupera dimensões com `StatusMgr::getMicroDimmingBlockNum` (chamada por PLT `0x57fa0` em `0x15a5f4`).
2. Calcula **largura × altura** em `0x15a600`.
3. Aloca **largura × altura × 2 bytes** em `0x15a618–0x15a620`.
4. Chama `StatusMgr::getMicroDimmingData` em `0x15a648` via PLT `0x58528`.
5. Percorre os valores de 16 bits e os concatena como texto ao ponteiro `char*` fornecido pelo chamador (trecho `0x15a658–0x15a6d8`).

O `StatusMgr::getMicroDimmingData` encaminha para `PQBase::videoGetMicroDimmingData`; este encaminha para `PQPortingMgr::videoGetMicroDimmingData`. Nesta última, `0x7a8b8–0x7a8f4` multiplica largura × altura, multiplica por dois para calcular o tamanho e chama a função importada **`thal_video_get_effect`** (PLT `0x56650`) com código `0x10`, seletor 0 e ponteiro de saída.

Essas informações são **estáticas, não testadas na TV**, e não comprovam o significado dos valores de MicroDimming. A matriz pode ser relacionada ao processamento digital de vídeo, não ao controle de PWM das **180 zonas físicas**.

### Novo risco a esclarecer

`TvPqManagerService::getMicroLocalDimmingData(char*)` recebe um `char*` **sem argumento de capacidade visível na assinatura** e anexa texto repetidamente (`strcat` via PLT `0x5a658`). **Não invocar essa função a partir de um programa experimental até identificar quem aloca o destino, quanto espaço ele tem, se há limite de dimensão e se o chamador normalmente passa buffer suficiente.** Uma falha em código privilegiado pode comprometer o serviço gráfico. É um risco a auditar, não uma vulnerabilidade comprovada.

**Não há motivo para alterar, liberar ou chamar a transação AIDL 158.** O caminho MicroDimming deve ser investigado em separado com análise de buffers, ABI, origem dos dados e permissões.

## Próximas ações somente offline

- Rastrear o chamador legítimo de `getMicroLocalDimmingData` e localizar a inicialização/capacidade do buffer de texto.
- Confirmar como `thal_video_get_effect` trata o efeito 0x10, quantidade e tamanho de bytes, sem invocar no hardware.
- Descobrir se MicroDimming e LocalDimming usam grids iguais e, se sim, se isso é uma coincidência de layout ou dado ligado ao backlight.
- Montar testes sintéticos para prevenir overflow; somente depois considerar um cliente de leitura isolado, não root.

### Marco atual

Comprovado na TV: **GetLdmBlockNum → 18 × 10 = 180**; GetDimmingDutyInfo → `0,0,255`; GetDvPwmInfo → `0,0`. Nenhuma telemetria individual de brilho dos LEDs foi demonstrada.
