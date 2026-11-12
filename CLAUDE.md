# Deckport: Zelda Ocarina of Time (repositório público do port)

Este repositório é o que o público vê e instala. O trabalho do dia a dia (testes, medições, anotações, plano) fica no
repositório privado `steam-deck`, em `projetos/zelda-oot/`. Ler lá o `PLANO-PORT.md` e o `docs/aprendizados.md` antes
de mexer aqui.

## Regras

- **Nada do jogo neste repositório**, nem nas versões: texturas, tabelas, capturas com arte do jogo. O logo do port
  (`arte/logo.png`) e pelo Kewin com IA e as artes da Steam (`arte/steam/`: capa, fundo, horizontal, ícone) foram feitos pelo Kewin com IA, e ele liberou o
  uso público em 2026-11-12.
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
- `ferramentas/gerar_assets.py` monta as artes (fundos, artes da Steam, logo da abertura) a partir de `arte/logo.png`
  e de fundos desenhados por ele. O logo tem geometria fixa: a faixa "STEAMDECK VERSION" fica em x >= 210 e y de 407 a
  441, que é o que o renderizador revela com o flare.
- O renderizador é o mesmo do Deck do Kewin (`~/zelda-oot/hookshot_vk-210.so` na VPS), com `arte/logo.png` embutido
  como logo da abertura.
- `ferramentas/montar-pacote.sh vX.Y.Z` monta `dist/zelda-oot-deck-vX.Y.Z.tar.gz`.

## Instalador

Tk, tela cheia 1280x800, controle e toque, no molde do `deckport-infamous-ss`. `instalador/nucleo.py` faz o trabalho:
baixa o Hookshot v2.1.0 oficial (soma SHA-256 conferida), monta o jogo com ele a partir do `.nup` (ou usa uma pasta já
montada pela v2.1.0), troca o renderizador, gera os mods com o Python que vem dentro do Hookshot, e cria o atalho.
Prévia no PC: `DEMO=1 PRINTS=<pasta> python instalador/instalador.py`.

O renderizador do port só serve para o Hookshot v2.1.0. Trocar a base do Hookshot é trabalho do `steam-deck`
(patches, testes), e só depois o número da versão muda em `nucleo.py`.

## Publicação aprovada (2026-11-12)

O Kewin aprovou deixar o repositório público e lançar a v0.1.0 em 2026-11-13, com o aviso no README de que a montagem pelo `.nup` dentro do instalador ainda não foi testada até o fim. Versões seguintes continuam precisando do OK dele na hora.
