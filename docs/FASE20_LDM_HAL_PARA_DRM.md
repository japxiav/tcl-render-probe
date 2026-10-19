# Fase 20 — Caminho do Local Dimming até DRM (V643)

## Achados verificados

- Kernel da TCL C6K em execução: `5.15.180-android14-11`, segundo `adb shell uname -r` enviado pelo proprietário.
- Repositório público [TCLOpenSource/mt9655](https://github.com/TCLOpenSource/mt9655), `Makefile`: kernel **5.15.148**.
- O [diretório DRM MediaTek do código TCL publicado](https://github.com/TCLOpenSource/mt9655/tree/main/drivers/gpu/drm/mediatek) compila `mediatek-drm.o` genérico, mas **não inclui o módulo `mediatek-drm-tv.ko` específico da TV**.
- O módulo `mediatek_drm_tv` aparece carregado nos dados `/proc/modules` enviados pelo proprietário. Também aparecem `mtk_tvpqu`, `spi_mt5896`, `pwmscan_mt5896`, `pwmseg_mtktv` e outros; a presença dos módulos não comprova transporte dos valores de zona por SPI/PWM.

## Elo confirmado pela desmontagem nativa

Biblioteca original `libmi3_hwc_hal.so`, SHA-256:
`608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500`.

- `MI_RENDER_GetLdmBlockNum` em `0x76a08` compara o seletor `0xF1FFFFFF` em `0x76a58–0x76a5e`.
- `0x76af4` e `0x76afa` constroem comando **`0xC0246461`**; `0x76b04` chama `drmIoctl`. O código retorna dimensões via estrutura de resposta.
- `MI_RENDER_GetLdmBlockData` em `0x78440` prepara **o mesmo comando `0xC0246461`** em `0x785c8–0x785ce`, chamando `drmIoctl` em `0x785dc`.
- Decodificação Linux do comando: tipo `'d'` (DRM), número `0x61`, tamanho codificado `0x24` (36 bytes), direção de leitura+escrita. Isso **não determina ainda o handler de kernel nem o significado dos dados**.

**Não chamar a operação Binder 158:** auditorias anteriores encontraram risco plausível de acesso indevido a buffer na implementação do fornecedor.

## Próximo passo correto

Obter uma cópia somente leitura do **módulo efetivamente instalado** na TV, para auditá-lo no computador:

```cmd
adb pull /vendor_dlkm/lib/modules/mediatek-drm-tv.ko
```

Com o ELF copiado, identificar tabela/handler DRM do `0xC0246461`, funções LDM e possível caminho para o controlador dos LEDs. Não usar root, não escrever em sysfs, não forçar leituras bloqueadas.

## Limites

**Confirmado no hardware:** consulta AIDL 147 retorna 18 × 10 = 180, sem root. **Confirmado offline:** a HAL chega ao DRM pelo ioctl citado. **Não confirmado:** valores individuais das 180 zonas, fluxo até LEDs físicos, API legível sem privilégios. `getMicroLocalDimmingData` é via processamento de vídeo e não prova LDM físico.
