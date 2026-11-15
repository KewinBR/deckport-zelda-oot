# Mudanças

## v0.1.1 (versão de teste)

- Base nova: Longshot nightly-189 (aa95d35f). O builder dele compila o renderizador na montagem, então o instalador
  aplica o patch do port nas fontes do builder e o renderizador do port sai da própria montagem, com os shaders
  preparados por ele. O AppImage da nightly vai também como anexo deste release, porque as nightlies somem do servidor
  do Longshot.
- Cinco correções do Longshot que saíram depois da nightly-189, levadas no patch: a memória devolvida quando o Linux
  fica sem (testada pelo Longshot num Deck OLED: o swap zerava, com ela sobravam mais de 2 GB), a conta de espaço dos
  arquivos de páginas que ela usa, shaders com mais de 1 MiB que ficavam de fora, a correção das páginas atrasadas e o
  caminho alternativo dos mesh shaders com cargas maiores.
- Atualização automática: o lançador vê em segundo plano se há versão nova, baixa e confere, e ela entra na abertura
  seguinte. Quando a base muda, o jogo é montado de novo sozinho, com o jogo fechado e o Deck na tomada, numa pasta ao
  lado; abrir o jogo pausa a montagem. `"atualizar": false` no `config.json` desliga. Quem tem a v0.1.0 precisa rodar
  o instalador uma vez.
- O desinstalador para a atualização em segundo plano antes de apagar.

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
