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
- **GPL-3.0**, a licença do Longshot e do Hookshot. Cada versão leva em `patches/` a diferença inteira do renderizador
  (`deckport-longshot-5e072fc8.patch`, contra o commit 5e072fc8 do Longshot), o script de compilação e os patch_*.py.
- **Publicar** (tornar o repositório público, criar uma versão) pede o OK do Kewin na hora.
- Textos em português seguem `C:\Dev\_docs\escrita-geral.md`: sem travessão e sem emoji.
- O instalador não pode exigir ajuste de sistema, senha ou teclado.

## Como o repositório é montado

- `ferramentas/sincronizar.sh` copia do `steam-deck` o lançador, os ajudantes, as ferramentas dos mods e os patches.
  Não editar essas cópias aqui: editar lá e sincronizar.
- `ferramentas/gerar_assets.py` monta as artes (fundos, artes da Steam, logo da abertura) a partir de `arte/logo.png`
  e de fundos desenhados por ele. O logo tem geometria fixa: a faixa "STEAMDECK VERSION" fica em x >= 210 e y de 407 a
  441, que é o que o renderizador revela com o flare.
- O renderizador é o mesmo do Deck do Kewin (`~/zelda-oot/longshot_vk-ls-1.so` na VPS, sha 0a70e306), compilado por
  `build-vk-ls.sh` da árvore `~/zelda-oot/ls-220`. A tela de abertura dele fica desligada pelo lançador
  (`RX_VK_STARTUP_SCREEN=0`), porque travava no Modo de Jogo.
- `ferramentas/montar-pacote.sh vX.Y.Z` monta `dist/zelda-oot-deck-vX.Y.Z.tar.gz`.

## Instalador

Tk, tela cheia 1280x800, controle e toque, no molde do `deckport-infamous-ss`. `instalador/nucleo.py` faz o trabalho:
baixa o builder do Longshot (`BASE_VERSAO`, hoje a v3.0.0-rc.5; tenta o git.magicbean.dev e depois o anexo do nosso
release, porque as nightlies somem; soma SHA-256 conferida), extrai, aplica o `patch_800p.py` e o
`patches/deckport-longshot-<base>.patch` nas fontes dele, e monta o jogo a partir do `.nup` (ou de uma pasta de outra
versão, por `--romfs` e `--exefs`). Desde a nightly 18x o builder compila o renderizador na montagem (commit 25726217),
então o renderizador do port sai da própria montagem, com os shaders preparados por ele. A pasta montada guarda
`deckport_base.txt` com a identidade da base (versão do Longshot + soma do patch); igual à do pacote, ela é usada como
está. Depois gera os mods com o Python do Longshot, copia os saves do Hookshot e cria o atalho. As ferramentas de
compilação que o Longshot baixa ficam em `~/.local/share/zelda-oot-deck/longshot/builder`.
Prévia no PC: `DEMO=1 PRINTS=<pasta> python instalador/instalador.py`.

O patch do renderizador é feito no `steam-deck` (árvore do Longshot na VPS, `build-vk-ls.sh` com `ARVORE=` para
conferir que compila) e entra aqui pelo `ferramentas/sincronizar.sh`. Trocar a base: o patch novo sobre a versão
nova, `BASE_*` em `nucleo.py`, e o AppImage da base como anexo do release (o espelho).

## Atualização automática (desde a v0.1.1)

`instalador/atualizar.py`, chamado pelo lançador. `aplicar` na abertura: põe no lugar a versão já baixada e abre o
lançador de novo. `verificar` em segundo plano (unidade `zelda-oot-deck-atualizar`, fora da sessão do jogo): baixa a
versão nova do GitHub e, se a identidade da base muda, monta o jogo de novo em `<raiz>/jogo-novo` quando o jogo está
fechado e o Deck na tomada; a próxima abertura troca as pastas. Abrir o jogo interrompe a montagem (o `--work` do builder é
reaproveitado). `ZELDA_ATUALIZAR=0` ou `"atualizar": false` no `config.json` desliga; `ZELDA_RELEASE_URL` aponta para um
JSON de release falso nos testes. Log: `<raiz>/logs/atualizacao.log`. Quem tem a v0.1.0 precisa rodar o instalador uma
vez para ganhar o atualizador.

## Publicação aprovada (2026-11-12)

O Kewin aprovou deixar o repositório público e lançar a v0.1.0 em 2026-11-13, com o aviso no README de que a montagem pelo `.nup` dentro do instalador ainda não foi testada até o fim. O Hookshot saiu do GitHub no mesmo dia e a v0.1.0 esperou. Em 2026-11-15 o Kewin pediu o lançamento com o que roda no Deck dele: renderizador do Longshot, base Longshot v3.0.0-rc.3. Versões seguintes continuam precisando do OK dele na hora.

A v0.1.3 saiu em 2026-11-22, com o OK do Kewin ("faz o que falta no Zelda"), depois do instalador testado no Deck LCD com um HOME isolado: montagem completa em 67 min sem erro, 800 funções do perfil achadas, Kokiri a 38,2 fps de mediana (p10 30,2) e nenhum crash em duas corridas de 620 s.
