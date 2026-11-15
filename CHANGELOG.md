# Mudanças

## v0.1.0 (versão de teste)

Primeira versão aberta para testes.

- Base: Longshot v3.0.0-rc.3 (a continuação do Hookshot), baixado do release oficial com a soma SHA-256 conferida. O
  Hookshot saiu do GitHub em 2026-11-13, e o Longshot tem a mesma interface com o renderizador (versão 21).
- Instalador pelo Modo Desktop, com controle e toque: monta o jogo com o Longshot a partir do `.nup` do jogador, ou de
  uma pasta já montada pelo Hookshot ou pelo Longshot (montada de novo a partir dos arquivos que ela guarda, sem o
  `.nup`). Os saves do Hookshot são copiados para o Longshot.
- Renderizador do Longshot (commit 5e072fc8) com as alterações do Deck: menu do port, espera seletiva dos resultados
  da GPU (menos piscadas sem perder fps), sombra reduzida, saída em 16:10 na resolução do Deck. O mesmo que roda no
  Deck do autor.
- Ajustes do lançador para o Deck: sem os espelhos esparsos de VRAM e sem a correção das páginas atrasadas (em Kokiri,
  8% mais quadros e metade dos engasgos acima de 50 ms), e sem a tela de abertura, que travava no Modo de Jogo.
- Mods gerados no Deck a partir do jogo: texturas reduzidas (512 e 1024) e 14 níveis de vegetação.
- Lançador com vigia de memória por pressão do kernel, cópia do save a cada abertura e log de cada sessão.
- Huge pages transparentes desligadas só para o processo do jogo (sem mudar o sistema). Para voltar ao padrão do
  sistema: `ZELDA_THP=1`.
- Desinstalador (`instalador/desinstalar.py`): tira o atalho, o port, o Longshot baixado e os mods, e mantém os saves
  e o jogo montado.
- Defeitos conhecidos no README.
