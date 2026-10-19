# Fase 20 — localizar o caminho real dos 180 blocos (TCL C6K V643)

**19/10/2026. Estado: investigação offline e planejamento de análise ELF, nenhuma chamada ao controlador de LEDs.**

## Resultado da pesquisa de código-fonte da TCL

Repos públicos oficiais inspecionados:

1. **TCLOpenSource/mt9655** `main` em `941c8ab356a90a1170388a21f6617a177731832a`, Makefile `VERSION=5 PATCHLEVEL=15 SUBLEVEL=148`. Está associado ao modelo C6K no índice oficial. O repositório expõe código do kernel base e caminhos genéricos `drivers/gpu/drm/mediatek/`. A árvore retornada pela API foi **truncada**, mas buscas no repositório e inspeção de caminhos relevantes não localizaram `mediatek-drm-tv.ko`, `mtk-tvpqu.ko` ou nomes dos atributos sysfs `support_render_ldm_*`. **Não é justificável presumir que contenha o driver LDM da V643.**
2. **TCLOpenSource/mt9618**, Makefile `5.15.180`, mesma subversão base do kernel observado na TV (`5.15.180-android14-11`), porém **família de TVs distinta** e também sem módulos de TV/LDM nos caminhos pesquisados. Compatibilidade de versão **não implica** compatibilidade de módulo nem código de controle de LEDs.

Fontes públicas:
- https://github.com/TCLOpenSource/TCL_Kernel_OpenSource
- https://github.com/TCLOpenSource/mt9655
- https://github.com/TCLOpenSource/mt9618

## Evidência do aparelho (ADB somente leitura)

O usuário compartilhou `uname -r`, `/proc/modules`, listagem `/vendor/lib/modules` e nomes de capacidades DRM. Confirmado:

- Kernel: `5.15.180-android14-11`.
- Carregados: `mediatek_drm_tv`, `mtk_tvpqu`, `mtk_pq`, `mtk_tvcpuif`, `pwmseg_mtktv`, `spi_mt5896` e `mtk_bdma` (além de outros).
- Arquivos existentes: `/vendor/lib/modules/mediatek-drm-tv.ko`, `mtk-tvpqu.ko`, `mtk-pq.ko`, `mtk-tvcpuif.ko`, `pwmseg-mtktv.ko` e `pwmadc-mt5896.ko`.
- Em `/sys/devices/platform/mediatek-drm-tv-kms/capability/` existem quatro nomes `support_render_ldm_*`; a leitura com o usuário shell retorna `Permission denied`.

**A presença de drivers SPI/PWM e de outros consumidores SPI não prova que os dados LDM físicos usem SPI.** É necessária análise de imports, strings e fluxos de chamada do módulo real.

## Evidência nativa V643 já disponível e verificada

Arquivo: `libmi3_hwc_hal.so`, SHA-256:
`608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500`

- `MI_RENDER_GetLdmBlockNum` e `MI_RENDER_GetLdmBlockData` usam um ioctl privado **`0xC0246461`** na rota DRM.
- Decodificação **da palavra ioctl**, não do esquema interno do pedido: `_IOC_TYPE = 0x64 ('d')`, `_IOC_NR=0x61`, `_IOC_SIZE=36`, direção codificada `_IOC_READ|_IOC_WRITE`. A estrutura de 36 bytes é **desconhecida** e não deve ser construída por tentativa e erro.
- O binário contém a mensagem `DRM_IOCTL_MTK_TV_CTL_LOCAL_DIMMING`.
- O nome do heap `/dev/dma_heap/mtk_ldm_data_uncached` também é referenciado no binário; sugere uso de buffer compartilhado dedicado a LDM. **Não prova conteúdo PWM por zona, acesso do shell nem leitura direta do DMA.**
- A resposta real de `GetLdmBlockNum` foi `result_code=0`, `18×10=180` (AIDL 147 com seletor `0xF1FFFFFF`).
- A operação AIDL 158 foi bloqueada após auditoria dos ponteiros do vetor de retorno, e **não deve ser testada no dispositivo**.

## Nossa nova estratégia: mapear do driver para o barramento

1. **Obter cópias somente leitura dos módulos de kernel V643**, prioritariamente `mediatek-drm-tv.ko` e `mtk-tvpqu.ko`, mais módulos `mtk-pq`, `mtk-tvcpuif`, `pwmseg-mtktv`, `pwmadc-mt5896` para comparação. Usar exclusivamente `adb pull`, sem `insmod`, `rmmod`, `su`, `service call`, `drmIoctl` manual ou escrita em sysfs.
2. **Verificar integridade e arquitetura** (`SHA-256`, cabeçalho ELF, `modinfo`, símbolos exportados/importados e strings relacionadas a `local_dimming`, LDM, SPI, PWM, DMA, panel).
3. **Localizar os handlers ioctl DRM**, incluindo `_IOC_NR 0x61`; mapear as chamadas internas para matrizes LDM, sincronização de buffers e possíveis funções de telemetria. Só serão chamadas 'interface de leitura' se não tiverem efeitos colaterais plausíveis e se permissões forem legítimas.
4. **Rastrear a etapa física** se as evidências indicarem realmente `spi_sync`, `pwm_apply`, `i2c_transfer`, mailbox, `rpmsg` ou outra interface. A lista de módulos instalada **não substitui esse rastreamento**.
5. **Comparar grid e tipos:** exigir prova de `18 × 10`, comprimento/buffer apropriado e mudança consistente com padrões de imagem em qualquer eventual leitura de intensidade. Correlacionar sem modificar o firmware.

## Ferramenta de coleta / análise offline

Pacote separado `TCL_C6K_Driver_Trace_Kit.zip` contém:
- `COLLECT_C6K_KERNEL.cmd`: coleta **somente leitura** em Windows com ADB, de módulos de kernel já presentes na TV; gera ZIP e checksums, sem root nem alterações.
- `inspect_modules_offline.py`: relatório de cabeçalho ELF, SHA-256 e strings, não executa código extraído.
- `README.md`: instruções e critérios de risco.

**Ponto de parada seguro:** caso `adb pull` retorne `Permission denied`, não contornar permissões. Verificar fontes públicas do mesmo módulo ou revisar apenas artefatos já obtidos.

## Limites atuais

O código-fonte oficial examinado **não permitiu ainda identificar a função que envia cada uma das 180 intensidades ao hardware**. Necessitamos dos módulos binários desta V643 ou fontes equivalentes verificadas. Não assumir que toda matriz MicroDimming digital seja a matriz física dos controladores Mini LED.

O próximo passo não é instalar um novo probe nem escrever na TV: **analisar os módulos kernel offline**.
