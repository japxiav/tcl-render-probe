# Fase 16 · Auditoria offline de GetLdmBlockData (158)

**19/10/2026 · TCL 55C6K · firmware V643**

## Resultado reproduzível

No ambiente offline de análise, usando cópias inalteradas de:
- `vendor.mediatek.hardware.render-impl.so`: SHA-256 `7daa84de2d0b306fa0704498d0b8f10ddff51d812de34225c9598b9c1655ec7c`;
- `libmi3_hwc_hal.so`: SHA-256 `608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500`.

O auditor validou **13 instruções ARM/Thumb em endereços específicos** e não encontrou gravação direta em `sp+0x18` entre a inicialização da estrutura temporária e a chamada HAL. Isso constitui evidência de disassembly **apenas para esses ELFs e versão**. Chamadas indiretas, aliases, possíveis pré-condições do driver e inicialização de estruturas externas ainda exigem investigação.

### Pontos confirmados

- `Render::GetLdmBlockData` em `0x2e83c–0x2e846`: zera 16 bytes da estrutura local (`sp+0x10`).
- `0x2e854`: usa campo de entrada `+0x10` (comprimento solicitado) na preparação do vetor temporário.
- `0x2e86a`: armazena ponteiro do vetor em `sp+0x14`; `0x2e8b0`: armazena o tipo em `sp+0x10`.
- `0x2e8c8`: chamada indireta à HAL.
- `MI_RENDER_GetLdmBlockData` em `0x784ea` lê os dois words do comprimento nativo em `[r4+8]`.
- No caminho de cópia HAL (`0x785e6–0x785ec`), `__aeabi_memcpy8` usa esse comprimento nativo.
- Na cópia posterior do serviço (`0x2e926–0x2e92c`), o destino vem de `[r8+0xc]` e a extensão vem da entrada `[r5+0x10]`. **Propriedade/capacidade desse destino não foi comprovada**.

### Principal risco

O comprimento do vetor temporário, o comprimento nativo que a HAL usa e o comprimento da cópia posterior parecem seguir origens diferentes. É **possível** que parte do caminho seja no-op, que os dados retornem vazios ou que haja incompatibilidade de buffers; ainda não se demonstrou qual comportamento ocorreria com um request real. Uma chamada de leitura proprietária pode provocar falha no serviço gráfico.

Isso **não equivale a afirmar** que há vulnerabilidade explorável, que a TV travaria, ou que a função sempre retorna zeros. O limite de inferência é intencional.

## Comando offline (somente computador)

Com LLVM disponível e **os dois ELFs originais já extraídos**, executar:

```sh
python3 tools/ldm158_offline_audit.py \
  --render /caminho/vendor.mediatek.hardware.render-impl.so \
  --hal /caminho/libmi3_hwc_hal.so
```

O programa verifica hashes, endereços e instruções e imprime JSON. **Não conecta ao Android, não usa ADB, Binder nem DRM.**

O GitHub Actions roda testes sintéticos de falha segura via `python3 -m unittest discover -s tests -v`, sem distribuir os binários proprietários no repositório. Esses testes de modelo não substituem auditoria real no hardware.

## Decisão técnica

**BLOQUEADA a operação 158** no executável para TV. A whitelist do probe permanece limitada às operações de leitura já existentes (31, 143, 147).

Para reavaliar, precisamos antes esclarecer:

1. Se algum caminho indireto inicializa o comprimento nativo `+8`;
2. Se `[r8+0xc]` identifica um buffer de destino válido e alocado, com capacidade suficiente;
3. Unidade exata de contagem (bytes/elementos de 16 bits), origem do vetor e valor do tipo;
4. Retorno AIDL e comportamento em dados ausentes, sem provocar alocações/uso inseguro.

**Resultado já comprovado de fases anteriores:** dimensões nativas 18×10 (180 blocos), sem root. **Não houve leitura dos 180 valores dinâmicos.**
