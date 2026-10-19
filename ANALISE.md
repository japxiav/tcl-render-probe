# Prova e limites do protocolo

## Evidencias estaticas dos binarios enviados

- `vendor.mediatek.hardware.render-V1-ndk.so`: `BpRender::GetLdmBlockNum` 
  em `0x394f0`; carrega `0x93` (147) em `0x395d0` e chama `AIBinder_transact`.
- A assinatura descompilada e `GetLdmBlockNum(int, ST_LDM_BLOCK_NUM_INFO const&, RetGetLdmBlockNum*)`.
- `ST_LDM_BLOCK_NUM_INFO::writeToParcel` em `0x4d840`: cabecalho length (int32), campo int32 offset 0, campo char16 offset 4, char16 offset 6.
- `RetGetLdmBlockNum::writeToParcel` em `0x45754`: cabecalho, int32 codigo, marker 1 e Parcelable aninhado.
- O driver inferior `MI_RENDER_GetLdmBlockNum` possui verificacoes de estado e despacha ioctl `0xC0246461`. O probe NAO executa ioctl diretamente.
- `GetLdmBlockData` (158) requer estrutura muito mais complexa e NAO esta habilitada neste prototipo.

## Limitacoes

A entrada selecionada `0` e `block_type=0` ainda NAO esta validada contra chamadas do proprio firmware em funcionamento. O modo seguro inicial e apenas `--ping`. Mesmo chamadas rotuladas leitura podem disparar erros em sistemas proprietarios. O probe contem apenas essas duas opcoes e nao implementa `Set*`.

## Auditoria de seguranca sugerida

Antes de executar `--read-block-num`, auditar a semantica dos dois inteiros e verificar controle de acesso SELinux. Codigo fonte aberto, compilado em GitHub Actions. Dispositivos /dev e arquivos de firmware nao sao acessados diretamente pelo probe.
