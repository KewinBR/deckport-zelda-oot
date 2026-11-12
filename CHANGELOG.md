# Mudanças

## v0.1.0 (versão de teste)

Primeira versão aberta para testes.

- Instalador pelo Modo Desktop, com controle e toque: monta o jogo com o Hookshot v2.1.0 a partir do `.nup` do
  jogador, ou usa uma pasta já montada.
- Renderizador do Hookshot v2.1.0 com as alterações do Deck: modo híbrido contra a travada da GPU, saída em 16:10 na
  resolução do Deck, sombra reduzida, menu do port e tela de abertura.
- Mods gerados no Deck a partir do jogo: texturas reduzidas (512 e 1024) e 14 níveis de vegetação.
- Lançador com vigia de memória por pressão do kernel e log de cada sessão.
- Huge pages transparentes desligadas só para o processo do jogo (sem mudar o sistema). Para voltar ao padrão do
  sistema: `ZELDA_THP=1`.
- Desinstalador (`instalador/desinstalar.py`): tira o atalho, o port e os mods, e mantém os saves e o jogo montado.
- Defeitos conhecidos no README. A montagem pelo `.nup` dentro do instalador ainda não foi testada até o fim; o caminho da pasta já montada foi.
