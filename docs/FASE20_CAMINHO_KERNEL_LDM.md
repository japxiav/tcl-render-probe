# Fase 20 | Rastreamento do driver físico de Local Dimming

**19/10/2026 | TCL C6K 55 polegadas | firmware V643 | investigação offline e leitura de fontes públicas**

## O que realmente sabemos

Na TCL real o usuário informou:
- `uname -r`: `5.15.180-android14-11`;
- módulos carregados: `mediatek_drm_tv`, `mtk_tvpqu`, `mtk_pq`, `spi_mt5896`, `pwmscan_mt5896`, `pnl_cust`;
- módulos em `/vendor/lib/modules`: **`mediatek-drm-tv.ko`** e **`mtk-tvpqu.ko`**;
- os caminhos em `/sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm*` existem, mas a leitura retorna **Permission denied** para o usuário `shell`. Não tentar contornar a restrição;
- `GetLdmBlockNum` (AIDL 147) com seletor `0xF1FFFFFF` retornou `result_code=0`, `18 × 10 = 180`.

### Restrições do kernel-source publicado

No índice oficial `TCLOpenSource/TCL_Kernel_OpenSource`, a TCL associa **C6K** ao repositório `TCLOpenSource/mt9655` descrito com versão **5.15.148**. A TV observada usa **5.15.180**, portanto não há correspondência exata.

No repositório público `TCLOpenSource/mt9655`, `drivers/gpu/drm/mediatek/` contém o driver DRM MediaTek **genérico** (`mtk_drm_drv.c`, `mtk_drm_crtc.c`, etc.), **não** a implementação `mediatek-drm-tv.ko` própria do kernel da TV. Uma busca por símbolos `mtk_tv_drm_ldm` e pelos arquivos sysfs `support_render_ldm` nesse repositório não retornou correspondências. Não assumir que o driver genérico implementa os controles físicos de backlight.

Fontes públicas:
- https://github.com/TCLOpenSource/TCL_Kernel_OpenSource
- https://github.com/TCLOpenSource/mt9655/tree/main/drivers/gpu/drm/mediatek

## Caminho com evidência nos ELFs V643

1. `vendor.mediatek.hardware.render.IRender/default`: AIDL `GetLdmBlockNum(147)` já funcionou na TV.
2. `vendor.mediatek.hardware.render-impl.so`: a implementação `Render::GetLdmBlockNum` encaminha a chamada ao HAL.
3. `libmi3_hwc_hal.so` (SHA256 `608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500`) contém `MI_RENDER_GetLdmBlockNum` e `MI_RENDER_GetLdmBlockData`.
4. A biblioteca emite `drmIoctl` com o request **`0xc0246461`** nos caminhos de consulta LDM. Decodificação Linux `_IOC`: direção leitura+escrita, magic `'d'` (DRM), número `0x61`, struct de **36 bytes**. O nome e a disposição concreta da struct no driver privado ainda **não** foram confirmados.
5. A mesma biblioteca referencia **`/dev/dma_heap/mtk_ldm_data_uncached`** e o estado de buffers `_stRenderDmaParamLdmData`. É uma pista forte para troca de dados LDM por memória dedicada, **não comprovação de medição dos 180 LEDs**.
6. Os módulos carregados `mediatek_drm_tv` e `mtk_tvpqu` são candidatos prioritários para encontrar o tratamento do request `0x61` e as propriedades LDM. A responsabilidade exata do controlador de backlight, PWM/SPI, MCU e localização do cálculo ainda **não** foi demonstrada.

**Não misturar duas rotas:** o getter TCL Binder `getLocalDimmingData` foi identificado como stub que retornava zeros; isso não demonstra acesso à rota DRM privada. `GetMicroLocalDimmingData` pode refletir MicroDimming digital em vez dos 180 canais físicos.

## Gaps para encerrar a cadeia

- Onde o módulo `mediatek-drm-tv.ko` registra e trata o ioctl `0xc0246461`?
- O dispositivo possui alguma interface de *leitura* legítima, não privilegiada, para o buffer LDM?
- Qual módulo/firmware calcula valores por zona e quem os envia ao controlador LED por SPI, PWM ou outra ligação?
- O kernel `5.15.180` contém mudanças proprietárias além do snapshot público `5.15.148`?

## Próximo passo seguro

**Analisar offline os módulos da própria V643.** Eles foram vistos em `/vendor/lib/modules/` e podem ser copiados, se o sistema permitir leitura, pelo ADB **sem invocar nenhuma função do driver**:

```cmd
adb pull /vendor/lib/modules/mediatek-drm-tv.ko
adb pull /vendor/lib/modules/mtk-tvpqu.ko
```

Não modificar permissões, não usar root e não tentar outro caminho caso haja `Permission denied`; apenas registrar a mensagem. Não publicar os ELFs proprietários no GitHub público. Analisar localmente hashes, `.modinfo`, tabela de símbolos, strings e relocations, depois fazer correlação com os ELFs do HAL já identificados.

## Decisão de segurança

Manter `GetLdmBlockData` (AIDL **158**) BLOQUEADA: Fases 16–18 apontaram uma possível incompatibilidade de buffer de resposta. Evitar `drmIoctl` manual, comandos de escrita sysfs, reboot, root ou sondagem de SPI. A investigação de módulos será **estritamente offline**.

**Status:** caminho Render -> HAL -> DRM está rastreado, mas o caminho DRM -> controlador físico das 180 zonas **não está demonstrado**. Não afirmar conclusão até obter evidência dos módulos exatos.
