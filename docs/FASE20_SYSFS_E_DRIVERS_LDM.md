# Fase 20 · LDM sysfs bloqueado e escolha dos módulos reais

**19/10/2026 · TCL 55C6K V643 · evidência de ADB fornecida pelo usuário, sem root.**

## Evidência na TV

`uname -r`:
```text
5.15.180-android14-11
```

Os quatro atributos presentes em `/sys/devices/platform/mediatek-drm-tv-kms/capability/` são:
- `support_render_ldm_support`
- `support_render_ldm_global_dimming_support`
- `support_render_ldm_support_dv_gd`
- `support_render_ldm_vrr_support`

O teste direto com `adb shell cat` resultou em **Permission denied para os quatro atributos**. **Não obtivemos seus valores; presença ≠ habilitação.** O log não contém modo Unix nem rótulos SELinux desses arquivos, por isso não sabemos qual camada negou o acesso.

`/proc/modules` confirma drivers carregados:
- `mediatek_drm_tv` (módulo carregado, 1.355.776 bytes na coluna de memória declarada);
- `mtk_tvpqu` (3.772.416 bytes);
- `mtk_pq` (749.568 bytes);
- `pwmseg_mtktv` (24.576 bytes);
- `pwmscan_mt5896` (20.480 bytes);
- `spi_mt5896` (28.672 bytes).

A listagem `/vendor_dlkm/lib/modules` mostra `mediatek-drm-tv.ko`, `mtk-tvpqu.ko`, `mtk-pq.ko`, `pwmseg-mtktv.ko`, `pwmscan-mt5896.ko`. **Não executamos nenhum módulo; só foram listados.**

## Pesquisa da TCL OpenSource

O índice oficial [TCL_Kernel_OpenSource](https://github.com/TCLOpenSource/TCL_Kernel_OpenSource) associa explicitamente C6K ao repositório [mt9655](https://github.com/TCLOpenSource/mt9655), marcado **Android U, kernel 5.15.148**. A TV em teste informa **5.15.180-android14-11**.

A inspeção do repositório público `mt9655` mostrou estrutura padrão do kernel Linux/Android. O diretório `drivers/gpu/drm/mediatek` contém código genérico upstream e **não lista** o módulo `mediatek-drm-tv.ko` / driver de TV LDM presente no aparelho. O inventário GitHub de arquivos foi truncado após mais de 75 mil caminhos; assim, esta ausência é observação sobre o diretório inspecionado, **não prova universal de que nenhum outro arquivo contém LDM**.

**Decisão:** priorizar cópias offline dos módulos realmente instalados na V643, sem assumir ABI nem comportamento idêntico aos sources 5.15.148.

## Próximas ações seguras

1. **Somente metadados sysfs**:
   ```sh
   adb shell ls -lZ /sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm*
   ```
   Inspecionar proprietário, bits de modo e contexto SELinux sem ler valores protegidos.
2. **Extrair binário para análise offline**, somente se necessário:
   ```sh
   adb pull /vendor_dlkm/lib/modules/mediatek-drm-tv.ko
   ```
   O pull copia do dispositivo ao PC; não executa o módulo nem altera configuração. Se o acesso for negado, **não tentar bypass**.
3. Na cópia local, `sha256sum`, `readelf -p .modinfo`, `readelf -Ws`, `strings`, `llvm-objdump`: procurar `support_render_ldm_*`, `ldm`, `pwm`, `drm`, `sysfs`, `ioctl` e distinguir leitura de escrita. Verificar module vermagic.
4. Caso o módulo do DRM não revele toda a cadeia, analisar `mtk-tvpqu.ko` e `mtk-pq.ko` como dependências. Não executar `ioctl` arbitrário e não ler registradores físicos.

A meta continua identificar telemetria dinâmica dos **180 blocos (18×10)**; a existência de *capability flags* é indício de uma interface, **não** dados individuais de brilho nem prova de que sejam lidos via ADB shell.
