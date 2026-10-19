# Fase 18 — Despachante BnRender da operação AIDL 158

Data: 19/10/2026. TCL 55C6K, firmware V643, Android 14. **Análise offline, sem chamadas na TV**.

## Evidência nova, verificada diretamente no firmware

Os dois ELF foram conferidos por hash SHA-256:
- `vendor.mediatek.hardware.render-V1-ndk.so`: `de7d548884f7fadd141e9bce9a075039367ccb6a3065cfc23bdba09350254ed0`
- `vendor.mediatek.hardware.render-impl.so`: `7daa84de2d0b306fa0704498d0b8f10ddff51d812de34225c9598b9c1655ec7c`

### 1. Localização matemática do despachante

O código AIDL da função de despacho contém em `0x27960` um `tbh [pc, r0, lsl #1]`; em `0x27958`, calcula `transaction_code - 1`.

Para a transação 158, entrada da tabela em `0x27964 + (158-1) * 2 = 0x27A9E`. A entrada tem o halfword `0x17D3`; o alvo calculado é `0x27964 + 2 * 0x17D3 = 0x2A90A`.

Comparação positiva: transação 147 aponta a `0x2A592`, onde ocorre o caminho de `GetLdmBlockNum`.

### 2. Objeto de retorno inicializado com zeros

Em `0x2A90A`, o código executa `vmov.i32 q8, #0x0`. Em `0x2A912`, `r9 = sp+0x48`. Duas instruções `vst1.64 {d16, d17}` em `0x2A924` e `0x2A928` zeram os 32 bytes a partir de `sp+0x48`, incluindo os 3 ponteiros do vetor de retorno.

Na sequência:
- `0x2A956`: carrega função virtual do slot `vtable+0x28C`;
- `0x2A95C`: coloca `r9` como ponteiro do resultado no stack;
- `0x2A960`: chama a implementação via `blx r7`;
- `0x2A97E–0x2A982`: usa o mesmo objeto de retorno na serialização AIDL.

**Não há redimensionamento do vetor de retorno no despachante entre a inicialização com zeros e a chamada virtual.** Nenhum argumento recebido do cliente permite fornecer a memória do vetor de resposta antecipadamente por esse caminho.

### 3. A divergência do ponteiro agora tem origem confirmada

A AIDL serializa o vetor que começa em `RetGetLdmBlockData+8` (`0x45682–0x45688`). No layout padrão ARM32 libc++:
- `+8` = ponteiro `begin`;
- `+12` = ponteiro `end`;
- `+16` = ponteiro `end_cap`.

A implementação do fabricante, em `Render::GetLdmBlockData`:
- `0x2E91E`: entra no ramo de retorno zero da HAL;
- `0x2E922`: armazena código de retorno `0`;
- `0x2E926`: obtém ponteiro de destino de `[r8+0xC]` (**end**, não **begin**);
- `0x2E92A`: obtém comprimento solicitado da entrada `[r5+0x10]`;
- `0x2E92C`: chama `memcpy`.

Logo, **se** esse ramo for alcançado com comprimento maior que zero, a implementação aparenta usar destino de cópia sem armazenamento válido preparado no vetor de retorno. Tal situação é potencialmente perigosa para o processo de vídeo, e a existência de uma chamada *nominalmente* de leitura não garante sua segurança.

Não inferimos que um crash seja demonstrado na TV nem que todas as chamadas cheguem a esse ramo. O significado dos tipos 0/1/2 e o comportamento da HAL/DRM permanecem incompletos.

### 4. Decisão atual

- **GetLdmBlockNum (147):** comprovado na TCL: dimensões 18×10 (180 blocos).
- **GetDimmingDutyInfo (143):** duas leituras idênticas, `0,0,255`, sem identificação de intensidade por zona.
- **GetLdmBlockData (158):** **não executar no aparelho**. Sem garantia de capacidade do vetor de resposta e com destino de cópia suspeito.
- **CI:** scripts e testes verificam a tabela de despacho, o bloqueio da transação 158 no cliente e a presença de instruções específicas. Os testes sintéticos não constituem execução da chamada nem validam o kernel.

## Reproduzir auditoria offline

```sh
python3 tools/ldm158_dispatch_audit.py \
 --aidl /caminho/vendor.mediatek.hardware.render-V1-ndk.so \
 --render /caminho/vendor.mediatek.hardware.render-impl.so
```

A execução exige hashes exatos, `llvm-objdump` e produz JSON com evidências. O programa **não usa ADB e não conversa com a televisão**.

## Próximo caminho responsável

Encontrar uma **outra interface de telemetria que não use `GetLdmBlockData` (158)**. Possíveis alternativas somente se comprovadas: dump já implementado em driver/serviço, métricas agregadas acessíveis via APIs de leitura ou instrumentação de hardware externa, sem root nem alteração de firmware.

A documentação aqui é investigação de engenharia reversa em um firmware específico, não afirmação de vulnerabilidade generalizada.
