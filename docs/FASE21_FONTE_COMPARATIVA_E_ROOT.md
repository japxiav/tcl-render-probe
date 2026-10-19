# Fase 21 — Fonte LDM comparativa e rota de root comprovada em hardware semelhante

**19/10/2026 | TCL 55C6K V643 | investigação documental. Nenhum comando novo enviado à TV.**

## 1. O que continua comprovado na unidade

- Android 14, kernel `5.15.180-android14-11`.
- Render Binder transação **147** retornou `width=18, height=10`, ou **180 blocos**. Não há leitura de intensidades dinâmicas.
- `GetLdmBlockData` (**158**) permanece **BLOQUEADA**. Análise offline do `BnRender` indica objeto de resposta inicialmente zerado e implementação com cópia a partir de ponteiro `end` do vetor sem alocação anterior comprovada. Não é prova de exploração, mas não é seguro tratá-la como API inofensiva.
- `/proc/modules` confirma `mediatek_drm_tv`, `mtk_tvpqu`, `mtk_pq`, `pwmseg_mtktv`, `spi_mt5896`. O primeiro alvo de análise é `/vendor_dlkm/lib/modules/mediatek-drm-tv.ko`.
- Os quatro arquivos `capability/support_render_ldm*` existem mas o usuário `shell` recebe `Permission denied`. Seus valores e causa exata da negação não são conhecidos.

## 2. Fonte histórica de driver LDM encontrada

Fonte pública da TCL:
- https://github.com/TCLOpenSource/mt9653/blob/main/drivers/gpu/drm/mediatek/MTK_TV/merak/ldm/drv/drvLDM_sti.c
- https://github.com/TCLOpenSource/mt9653/blob/main/drivers/gpu/drm/mediatek/MTK_TV/merak/ldm/api/apiLDM.c

O `Makefile` do repositório indica **Linux 5.4.190**, não 5.15.180. **Não corresponde à revisão da V643 e não autoriza copiar interfaces/offsets para ela.**

Observações diretas desse código:
- `MDrv_LDM_Init` carrega arquivos de configuração/perfis e inicializa regiões de memória via `ioremap_cache`.
- Há regiões nomeadas para `Edge2D`, `BacklightGamma`, dados de painel, dados `mspi` e dispositivo LED.
- A inicialização envia `PQU_MSG_SEND_LDM_INIT`, sugerindo separação entre configuração LDM no driver e processamento PQU. Não confirma que o caminho V643 seja idêntico.
- `MDrv_LDM_GetData` aparece **comentada**, com nota de obter endereços de dados LDF/LDB/SPI por quadro. Não existe evidência de API ativa/segura para leitura de zonas na V643.
- Também há funções de escrita em registradores na atualização de perfil, portanto é incorreto tratar todas as chamadas LDM como telemetria de leitura.

Conclusão: fonte histórica útil para **nomes e arquitetura de pesquisa** (`PQU`, `Edge2D`, `Gamma`, `LED`, `MSPI`, `DMA`). NÃO fornece endereço de 180 valores da nossa unidade.

## 3. Root: relato correspondente à 55C6K V643

Referência comunitária:
- https://github.com/lukasa1993/tcl-tv-toolkit
- https://github.com/lukasa1993/tcl-tv-toolkit/blob/main/docs/rooting.md
- https://github.com/lukasa1993/tcl-tv-toolkit/blob/main/docs/tested-devices.md

O autor relata **root validado com Magisk 30.7** na TCL **55C6K V8-T653T01-LF1V643, Android 14**, com comprovação posterior de `uid=0`. A rota incluiu acesso físico à interface UART na HDMI Service e comandos enviados por ESP32. O próprio guia declara que **não obteve retorno UART consistentemente legível** e descreve riscos/recuperação.

**Distinguir:**
1. Root relatado/validado em uma unidade 55C6K V643 via **interface física + ESP32**: sim.
2. Root reproduzível por qualquer unidade com firmware V643: não comprovado.
3. Root com **apenas ADB por Wi-Fi**, sem UART/cabo/dispositivo físico: ainda **não comprovado**.
4. Root implicar leitura direta de todos os 180 PWM físicos: também **não comprovado**.

O projeto atual NÃO vai executar desbloqueio ou flash. O objetivo principal é observabilidade das zonas físicas.

## 4. Próximo experimento com melhor relação sinal/risco

**Coleta read-only no computador que já tem ADB conectado à TV**:

```cmd
adb shell ls -lZ /sys/devices/platform/mediatek-drm-tv-kms/capability/support_render_ldm*
adb pull /vendor_dlkm/lib/modules/mediatek-drm-tv.ko mediatek-drm-tv.ko
adb pull /vendor_dlkm/lib/modules/mtk-tvpqu.ko mtk-tvpqu.ko
```

Se um pull for negado, registrar e interromper, sem tentar bypass. Sem `su`, alteração de permissões, `setenforce`, `insmod`, flash, escrita sysfs ou ioctl direto.

O scanner existente `tools/phase20_module_inventory.py` aceita esses arquivos para inventário básico offline. Depois de obter os hashes, avançar para `readelf`, `nm`, `strings` e disassembly somente no PC; comparar símbolos de `PQU`, `LDM`, `MSPI`, `DMA`, `GET*` e roteamento do ioctl `0xC0246461`, sem assumir que strings são chamadas ativas.

**Critério de sucesso final:** 180 valores mutáveis, formato e orientação validados com padrões de preto e ponto branco, e origem rastreável à cadeia física de backlight, não apenas MicroDimming digital.

## 5. Status

Fase 21 documental encerrada. Investigação real dos binários da **própria V643** depende da cópia passiva de `mediatek-drm-tv.ko` e `mtk-tvpqu.ko`. Root puro Wi-Fi continua como hipótese separada, não requisito automático da rota de observabilidade.
