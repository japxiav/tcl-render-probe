# Fase 20 · Onde o caminho do LDM termina no código disponível

Data: 2026-10-19. Investigação documental e comparação com resultados ADB da TCL 55C6K V643.

## Resultado essencial

**Caminho de software parcialmente identificado:** componentes TCL PQ -> API de Render MediaTek via Binder AIDL -> `vendor.mediatek.hardware.render-impl.so` -> `libmi3_hwc_hal.so` -> chamada `drmIoctl`. Na operação de leitura de dimensões LDM (147) foi obtido sucesso e matriz **18×10=180** na TV.

**Não identificado:** o manipulador concreto no kernel para o ioctl de LDM, o estágio que calcula/serializa o brilho de cada uma das 180 zonas, o protocolo para os controladores LED e uma interface não privilegiada para ler tais valores.

## Auditoria da fonte pública oficial

Repositório: https://github.com/TCLOpenSource/mt9655

- `OSS_INFO.txt` identifica `NAME=Android Common Kernel`, `VERSION=android14-5.15` e o URL upstream `https://android.googlesource.com/kernel/common/+/refs/heads/android14-5.15`.
- `Makefile` na branch `main` declara kernel **5.15.148**.
- `drivers/gpu/drm/mediatek/Kconfig` declara o módulo genérico **`mediatek-drm`**, não o módulo de TV observado.
- Não foi encontrado entre os nomes de arquivos dessa árvore genérica o `mediatek-drm-tv.ko`, nem o código do driver de LDM específico de TV. O índice recursivo inicial do GitHub foi truncado, então essa avaliação foi complementada inspecionando diretamente `drivers/gpu/drm/mediatek/`; **não declarar uma prova matemática de que nenhum arquivo correspondente existe em qualquer subárvore**.

Arquivos:
- https://github.com/TCLOpenSource/mt9655/blob/main/OSS_INFO.txt
- https://github.com/TCLOpenSource/mt9655/blob/main/Makefile
- https://github.com/TCLOpenSource/mt9655/blob/main/drivers/gpu/drm/mediatek/Kconfig

## Evidência da TV

Saídas ADB fornecidas pelo usuário:
- `uname -r` = **5.15.180-android14-11**, diferente da versão do kernel no repositório TCL `mt9655`.
- `/proc/modules` lista `mediatek_drm_tv`, `mtk_tvpqu`, `mtk_pq`, `spi_mt5896`, `pwmscan_mt5896`, `pwm_mt5896` como módulos ativos, além de outros componentes da MediaTek.
- `/vendor_dlkm/lib/modules/` contém, segundo listagem do aparelho, `mediatek-drm-tv.ko`, `mtk-tvpqu.ko` e `spi-mt5896.ko`.
- Quatro arquivos sysfs `support_render_ldm*` existem, mas tentar `cat` como usuário ADB shell retorna `Permission denied`. Isso **não autoriza alterar permissões nem tentar burlar SELinux**.

## Próximo passo com maior retorno e menor risco

Estudar **offline** cópias dos módulos ELF reais `mediatek-drm-tv.ko` e `mtk-tvpqu.ko` da V643. Priorizar:

1. Seções ELF `.modinfo`, `__versions`, `.symtab` (se presentes), strings e informações de build.
2. Nomes/símbolos de LDM, PWM, PWM scan, writeback, backlight, IRQ, DRM ioctl, DMA e SPI e dependências.
3. Reconstruir o manipulador do ioctl de dimensões `GetLdmBlockNum` na rota já validada, e seguir até o cálculo/mapeamento das zonas.
4. Identificar apenas **observabilidade documentada e segura**, sem executar novos ioctls nem expor interfaces de escrita.

Consulta útil, se o usuário aprovar, feita no próprio computador onde o ADB já funciona e sem alterar o dispositivo:

```cmd
adb pull /vendor_dlkm/lib/modules/mediatek-drm-tv.ko mediatek-drm-tv.ko
```

Se falhar por permissão, não tentar escalação. O módulo pode ter centenas de KB a MB; não confundir a presença de um símbolo com uma API de leitura utilizável.

## Cautelas de interpretação

O fluxo `HAL -> drmIoctl` **não é ainda prova de qual driver recebe cada chamada**. A presença de `spi_mt5896` e módulos de PWM **não prova** que o tráfego por zona seja SPI nem que a API exponha PWM individual. `MicroDimming` de PQ pode ser contraste digital, não comando físico para os 180 LEDs. O `GetLdmBlockData(158)` permanece bloqueado pelos riscos de ponteiro/capacidade relatados nas fases 16–18.

**Conclusão:** identificamos o limite atual da observação e o artefato exato mais útil para destravar a investigação: o módulo real de DRM da TV, não o kernel genérico público.
