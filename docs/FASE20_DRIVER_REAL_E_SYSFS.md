# Fase 20 — Corrigir a rota: driver DRM realmente carregado

Data: 2026-10-19. Fonte primária: comandos ADB fornecidos pelo proprietário da TCL C6K 55 (V643). Pesquisa complementar: TCLOpenSource e kernel Linux.

## Evidência direta do aparelho

```text
adb shell uname -r
5.15.180-android14-11
```

Em `/proc/modules`, os módulos relevantes **carregados**, não apenas arquivos disponíveis, incluem:

- `mediatek_drm_tv` (equivalente a `mediatek-drm-tv.ko`),
- `mtk_tvpqu`,
- `mtk_pq`,
- `mtk_srccap`,
- `mtk_tvcpuif`,
- `pwmscan_mt5896`,
- `pwmseg_mtktv`,
- `pwm_mt5896`,
- `spi_mt5896`.

O usuário listou `/sys/devices/platform/mediatek-drm-tv-kms/capability/` e nele constam:

```text
support_render_ldm_support
support_render_ldm_global_dimming_support
support_render_ldm_support_dv_gd
support_render_ldm_vrr_support
```

**Importantíssimo:** só vimos NOMES de atributos, **não seus valores**. Esses arquivos revelam que a plataforma implementa consultas de capacidade LDM, não que todos os recursos estejam ativados nem que seja possível ler 180 intensidades. Ler com `cat` é uma operação nominalmente de observação (sem alteração de configuração).

A saída de `/vendor/lib/modules` também contém **`mediatek-drm-tv.ko`**, **`mtk-tvpqu.ko`**, **`mtk-pq.ko`** e **`pwmscan-mt5896.ko`**. Há arquivos iguais em `/vendor_dlkm/lib/modules`; a listagem não confirma que ambas as cópias são arquivos independentes em vez de bind mounts, symlinks ou outra montagem.

## Reavaliação do código oficial da TCL

O índice oficial [TCLOpenSource/TCL_Kernel_OpenSource](https://github.com/TCLOpenSource/TCL_Kernel_OpenSource) mapeia o **C6K** para [TCLOpenSource/mt9655](https://github.com/TCLOpenSource/mt9655) e lista Linux **5.15.148**.

Conferência direta via repositório oficial:
- O `Makefile` na branch `main` especifica `VERSION=5`, `PATCHLEVEL=15`, `SUBLEVEL=148`.
- O repositório contém predominantemente a base Android/GKI Linux comum, com `drivers/gpu/drm/mediatek` contendo drivers genéricos como `mtk_drm_drv.c`, e `drivers/pwm` com `pwm-mediatek.c`.
- A listagem consultada **não expõe o código específico** do módulo de TV `mediatek-drm-tv.ko` nem o do `mtk-tvpqu.ko` carregados na unidade examinada.

**Conclusão:** o repositório `mt9655` é uma boa referência de família, mas não pode ser usado como representação binária/fonte exata do kernel **5.15.180-android14-11** nem do driver proprietariamente estendido de vídeo. A diferença da subversão não prova que as ABIs mudaram; impede a suposição de equivalência.

## Rota priorizada

1. Ler os **valores**, não só os nomes, dos quatro atributos `support_render_ldm*` via `adb shell cat`. Nenhuma alteração.
2. Se as capacidades forem coerentes, obter apenas uma cópia do módulo DRM instalado por `adb pull /vendor/lib/modules/mediatek-drm-tv.ko`. Analisar **offline**, sem `insmod`, `rmmod`, root, dispositivos `/dev/dri` ou chamadas `ioctl`.
3. Conferir `modinfo`, `readelf`, `strings`, `nm` (se disponível) e hashes para localizar rotas `LDM`, `PWM`, `backlight`, `DRM ioctl`, `sysfs`, `debugfs` e leituras escalares/matriciais.
4. Somente seguir com interface comprovadamente de leitura, com limites e origem dos dados validados. A transação AIDL **158 continua BLOQUEADA** por suspeita de inconsistência de buffer.
5. Separar MicroDimming de processamento de vídeo da telemetria das **180 zonas físicas**; nomes parecidos não comprovam equivalência.

## Próximo comando Windows CMD (somente leitura)

```cmd
adb shell "for f in /sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm*; do echo $f; cat $f; done"
```

Não confiar que o retorno será booleano até observar os valores. Se houver `Permission denied`, não buscar bypass de SELinux.

## Fontes públicas

- TCL OpenSource index: https://github.com/TCLOpenSource/TCL_Kernel_OpenSource
- Família pública `mt9655`: https://github.com/TCLOpenSource/mt9655
- Base Linux sysfs: https://docs.kernel.org/5.15/filesystems/sysfs.html

**Conclusão de segurança:** nenhum novo executável ou comando de escrita na TV é necessário. A nova prioridade é o driver `mediatek_drm_tv` que efetivamente está rodando nela.
