# Fase 17 · Revisão do buffer de resposta da operação 158

**19/10/2026 | TCL C6K V643 | Apenas análise offline.**

## Resultado

A inspeção de **três bibliotecas ELF originais**, previamente verificadas por SHA-256, confirmou **19 pontos de instruções ARM Thumb**. O auditor offline executou **9 testes sintéticos** de segurança, todos aprovados. Os scripts completos, os resultados JSON e a documentação foram preparados em um pacote de auditoria separado; os ELFs proprietários não são redistribuídos.

## Nova descoberta: início do vetor ≠ destino da cópia

Em `vendor.mediatek.hardware.render-V1-ndk.so`:
- `RetGetLdmBlockData::writeToParcel`, `0x45682`: adiciona `+8` ao objeto de retorno antes de serializar o vetor de 16 bits (`0x45688`).
- `RetGetLdmBlockData::readFromParcel`, `0x4562a`: usa novamente `+8` para o vetor (`0x45630`).

Em `vendor.mediatek.hardware.render-impl.so`:
- `Render::GetLdmBlockData`, `0x2e926`: carrega o **destino** de `[r8+0xc]`, onde `r8` é o ponteiro do objeto de retorno.
- `0x2e92a`: carrega o **tamanho** de `[r5+0x10]`, de origem da entrada.
- `0x2e92c`: invoca a cópia de memória (`__aeabi_memcpy`).

Sob o layout habitual de `std::vector<char16_t>` da **libc++ ARM32**, se o vetor começa em `+8`, seus ponteiros são: **begin em +8, end em +12, end_cap em +16**.

**Hipótese técnica importante:** o código copia para `end`, não para `begin`, sem uma operação visível de `resize` dentro da implementação. O construtor/dispatcher AIDL pode ter pré-alocado ou inicializado o vetor antes da chamada, e esse estado ainda não foi rastreado completamente. Isso é evidência de *risco plausível*, não prova de travamento, falha explorável ou código executável inseguro em todos os caminhos.

A Fase 16 também observou comprimento nativo aparentemente zero em `native+8` enquanto a cópia final usa o comprimento da entrada. A hipótese de incompatibilidade entre buffers se fortalece.

## Hashes dos binários exatos analisados

- render-impl.so: `7daa84de2d0b306fa0704498d0b8f10ddff51d812de34225c9598b9c1655ec7c`
- libmi3_hwc_hal.so: `608115c1b37896e48e950b1c3b95dd5a0aad70732754e41c2196e69b6ab05500`
- render-V1-ndk.so: `de7d548884f7fadd141e9bce9a075039367ccb6a3065cfc23bdba09350254ed0`

## Limites e decisão

- **Confirmado na TV:** consulta `GetLdmBlockNum` (147) com retorno `result_code=0, width=18, height=10`, total de **180 blocos**.
- **Não confirmado:** intensidade dinâmica de cada bloco, unidade de comprimento, capacidade do vetor e ciclo de vida da memória de resposta.
- **Decisão de segurança:** manter **transação 158 BLOQUEADA** no TCL Render Probe. Não chamar `service call 158`, não enviar buffers arbitrários, não alterar firmware e não fazer `drmIoctl` manual.

**Próxima investigação:** localizar, no binário AIDL gerado, a rotina de despacho `BnRender` correspondente a 158 e verificar se o objeto de retorno tem seu vetor inicializado com capacidade apropriada antes de chamar `Render::GetLdmBlockData`.

A auditoria offline ajuda a detectar indícios estruturais, mas **não** certifica a segurança de uma consulta ao serviço real.
