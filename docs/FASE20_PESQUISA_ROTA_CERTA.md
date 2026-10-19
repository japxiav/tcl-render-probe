# Fase 20 — Pesquisa de rota: Local Dimming físico vs MicroDimming

**2026-10-19 | TCL 55C6K | firmware V643 | sem executar qualquer teste novo na TV.**

## Veredito

**Rota prioritária:** identificar os módulos e a interface de observabilidade do **driver MediaTek TV DRM/LDM** que efetivamente alimenta o backlight. Paralelamente criar método de **validação óptica externa** usando vídeo de teste e câmera com exposição travada. Não priorizar `getMicroLocalDimmingData` como se fosse a matriz física de 180 zonas.

## Fontes externas pesquisadas

1. Índice oficial TCL liga explicitamente C6K ao kernel `mt9655`, Android U, kernel **5.15.148**: https://github.com/TCLOpenSource/TCL_Kernel_OpenSource
2. Código publicado de base: https://github.com/TCLOpenSource/mt9655
3. A pasta publicada `drivers/gpu/drm/mediatek` contém 28 arquivos de driver DRM genérico e não expõe `mtk_tv_drm_ldm` nem implementação LDM para esta TV: https://github.com/TCLOpenSource/mt9655/tree/main/drivers/gpu/drm/mediatek
4. Android documenta separação GKI vs módulos específicos de fabricante e localização em vendor/vendor_boot: https://source.android.com/docs/core/architecture/kernel/modules
5. Discussão técnica ilustrando diferença de zonas MicroDimming (imagem/software) vs Local Dimming (LEDs físicos): https://www.avforums.com/threads/tcl-c935-discussion-help-experiences.2426274/page-36
6. Confirmação externa de 180 zonas (18 x 10) na C6K 55: https://www.choose.tv/us/tv/reviews/tcl/tcl-c6k_AFD
7. Metodologia de avaliação independente com pontos brancos, movimento, blooming e exposição controlada: https://www.rtings.com/tv/tests/picture-quality/lighting-zones

**Limitação:** associação do modelo a um repositório da TCL não significa que o código da revisão exata V643 ou os módulos proprietários estejam integralmente publicados. A versão do kernel do aparelho precisa ser confirmada em leitura passiva.

## Evidência da unidade do usuário — V643

- `IRender/GetLdmBlockNum` (147) com seletor `0xF1FFFFFF`: retorno `0`, **width=18, height=10, product=180**. Layout provável 18 colunas × 10 linhas, ainda sem verificação de orientação por iluminação individual.
- `GetDimmingDutyInfo` (143): duas amostras iguais de `0,0,255`; sem evidência de duty físico por zona.
- `GetDvPwmInfo` (162): resposta `0,0`; sem evidência de PWM variável.
- `TvPanelManager::getLocalDimmingData` via Binder 134 é stub; 180 zeros não indicam backlight desligado.
- `TvPqManagerService::getLocalDimmingData` -> `thal_panel_get_ldm_block_data` -> AIDL Render: caminho nominal aparentemente retorna à operação problemática de leitura 158. **Trocar a camada Java/TCL por esta função não corrige o suspeito problema de memória mais abaixo.**
- A transação 158 mantém um potencial risco por copiar para o ponteiro `end` do vetor de resposta sem preparação demonstrada; **não executar**.
- Em `libtpq.so`, `getMicroLocalDimmingData` usa `videoGetMicroDimmingData` e `thal_video_get_effect`; isso aponta a processamento de vídeo e **não comprova** leitura de LEDs reais. A concatenação para `char*` tem capacidade de destino não comprovada; **não executar**.

## Evidências do binário real: pontos de observabilidade passiva

`libmi3_hwc_hal.so`, SHA-256 `608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500`:

- `/sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm_support`
- `/sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm_global_dimming_support`
- `/sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm_vrr_support`
- `/sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm_support_dv_gd`
- `/dev/dma_heap/mtk_ldm_data_uncached`
- `drmIoctl` interno com código `0xC0246461` encontrado nas funções GetLdmBlockNum e GetLdmBlockData; **não emitir ioctl manual**.

Esses caminhos **não garantem** acesso ADB e alguns já deram `Permission denied`. Os `support_*` são indicadores de capacidade, não valores das zonas. O heap DMA **não é arquivo de telemetria textual**.

## Plano por prioridade

**P1. Identificar driver ativo sem alterar estado.**

Comparar `uname -r`, lista passiva de módulos (`/proc/modules`), nomes de `/vendor/lib/modules` e `/vendor_dlkm/lib/modules` e listagem dos arquivos `capability` do `mediatek-drm-tv-kms`. **Listar nomes/metadados, sem cat indiscriminado de sysfs, sem root/SELinux/modprobe/insmod**. Se houver `Permission denied`, não contornar.

**P2. Rastrear símbolos/ABI em cópias offline dos arquivos já disponíveis.**

Procurar no módulo/ELF referente a `mediatek-drm-tv-kms` as rotas somente leitura: parâmetros `GET_LDM_*`, tamanho e tipo dos buffers, origem da telemetria, segurança dos locks/IOCTLs. Não instalar nem chamar novas funções sem documentação clara. Se o driver estiver embutido no kernel e não houver fontes correspondentes, registrar a limitação.

**P3. Validar o observável físico de maneira independente.**

Usar padrões estáticos preto e quadrado branco deslocado, mais padrão em movimento em modo SDR estável, e câmera fixa com exposição/foco/ISO travados, no escuro. Medir blooming, atraso de transição e regiões iluminadas. Isso **não equivale a telemetria PWM exata** nem revela o mapa de registradores, mas permite verificar mudanças reais de backlight com segurança. Método alinhado à RTINGS.

**P4. Considerar MicroDimming como pesquisa auxiliar**, apenas se suas dimensões diferirem claramente de 18×10 ou se for possível correlacionar mapa digital com padrão exibido; jamais equiparar valores ao PWM real sem fonte comprovada.

## Critérios de evidência para considerar acesso a zonas "concluído"

1. Uma leitura gera **180 valores não triviais**, com formato/ordem/escala documentados.
2. Na mesma configuração, amostras de preto vs ponto branco mudam na região espacial esperada, repetidamente.
3. Fonte identificável (driver físico/telemetria do controlador), não mapa de imagem nem dados simulados.
4. Memória, permissões e estabilidade comprovadas sem alterações de firmware ou chamadas proprietárias indefinidas.

**STOP:** com ausência de interface de leitura suportada ou com buffers suspeitos, não executar 158 nem outros comandos exploratórios; continuar só análise offline e medições ópticas.

## Próxima ação concreta

Antes de desenvolver TCL Render Probe v0.6, executar **somente inventário passivo** no aparelho (quando conveniente), usando comandos individuais:

```cmd
adb shell uname -r
adb shell cat /proc/modules
adb shell ls /vendor/lib/modules
adb shell ls /vendor_dlkm/lib/modules
adb shell ls /sys/devices/platform/mediatek-drm-tv-kms/capability
```

Nenhum dos comandos grava estado, mas alguns podem ser negados. O inventário ajudará a separar drivers vendor reais do kernel genérico disponibilizado em GitHub.

**Decisão final:** seguir **driver físico → evidência passiva → validação óptica**. MicroDimming e PWM global são secundários. Sem novo executável no aparelho nesta etapa.
