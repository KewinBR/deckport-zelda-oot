# Deckport: Zelda Ocarina of Time (repositório público do port)

Este repositório é o que o público vê e instala. O trabalho do dia a dia (testes, medições, anotações, plano) fica no
repositório privado `steam-deck`, em `projetos/zelda-oot/`. Ler lá o `PLANO-PORT.md` e o `docs/aprendizados.md` antes
de mexer aqui.

## Regras

- **Nada do jogo neste repositório**, nem nas versões: texturas, tabelas, logo do jogo, capturas com arte do jogo.
  Tudo o que depende do jogo é gerado no Deck do jogador, a partir da cópia dele. O `ferramentas/montar-pacote.sh`
  recusa o pacote se achar arquivo do jogo.
- **GPL-3.0**, a licença do Hookshot. Cada versão leva em `patches/` os scripts e a diferença inteira
  (`deckport-210.patch`) do renderizador contra o Hookshot v2.1.0.
- **Publicar** (tornar o repositório público, criar uma versão) pede o OK do Kewin na hora.
- Textos em português seguem `C:\Dev\_docs\escrita-geral.md`: sem travessão e sem emoji.
- O instalador não pode exigir ajuste de sistema, senha ou teclado.

## Como o repositório é montado

- `ferramentas/sincronizar.sh` copia do `steam-deck` o lançador, os ajudantes, as ferramentas dos mods e os patches.
  Não editar essas cópias aqui: editar lá e sincronizar.
- `ferramentas/gerar_assets.py` desenha as artes (fundos, logos em texto, artes da Steam, logo da abertura) com fontes
  de licença aberta. O logo da abertura tem geometria fixa: a faixa "STEAMDECK VERSION" fica em x >= 210 e y de 407 a
  441, que é o que o renderizador revela com o flare.
- O renderizador público é compilado na VPS com `arte/logo-abertura.png` no lugar do `assets/hookshot.png` da árvore
  do Hookshot, e guardado como `~/zelda-oot/hookshot_vk-210-publico.so`. O do Deck do Kewin usa o logo do jogo e não
  pode ir para o pacote.
- `ferramentas/montar-pacote.sh vX.Y.Z` monta `dist/zelda-oot-deck-vX.Y.Z.tar.gz`.

## Instalador

Tk, tela cheia 1280x800, controle e toque, no molde do `deckport-infamous-ss`. `instalador/nucleo.py` faz o trabalho:
baixa o Hookshot v2.1.0 oficial (soma SHA-256 conferida), monta o jogo com ele a partir do `.nup` (ou usa uma pasta já
montada pela v2.1.0), troca o renderizador, gera os mods com o Python que vem dentro do Hookshot, e cria o atalho.
Prévia no PC: `DEMO=1 PRINTS=<pasta> python instalador/instalador.py`.

O renderizador do port só serve para o Hookshot v2.1.0. Trocar a base do Hookshot é trabalho do `steam-deck`
(patches, testes), e só depois o número da versão muda em `nucleo.py`.
