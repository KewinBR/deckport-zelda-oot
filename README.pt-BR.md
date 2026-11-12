<p align="center"><img src="arte/logo-vertical.png" width="420" alt="The Legend of Zelda: Ocarina of Time, Deckport (STEAMDECK VERSION)"></p>

<p align="center"><b>Português</b> • <a href="README.md">English</a></p>

# Deckport: The Legend of Zelda: Ocarina of Time

O **Deckport** é um port para Steam Deck do remake de Ocarina of Time (Switch 2), sem emulador. Ele roda sobre o
[Hookshot](https://github.com/NotRexed/Hookshot), de NotRexed, que recompila o jogo para PC. O Deckport acrescenta o
trabalho específico do Deck: um renderizador ajustado, cortes de conteúdo para a memória e a CPU do aparelho, menu
próprio e um instalador que dispensa teclado e mouse.

**Esta é uma versão de teste.** O jogo é jogável, mas tem defeitos conhecidos, listados abaixo. Ela foi aberta para
que mais gente teste em mais áreas do jogo.

**Você precisa da sua própria cópia do jogo**, num arquivo `.nup`. Este repositório não tem nenhum arquivo do jogo e
nada do jogo é baixado.

## O que funciona

- Jogo jogável no Steam Deck LCD, de 24 a 31 fps na maior parte das áreas testadas (Floresta Kokiri, campo, rancho
  Lon Lon, cidade do castelo, Kakariko).
- Tela cheia em 16:10, na resolução do Deck.
- Ícones de botão do Steam Deck nos textos e menus do jogo (recurso do Hookshot).
- Menu do port no estilo do jogo, com predefinições e opções de textura, distância da vegetação, grama e sombra.
- Tela de abertura própria enquanto os shaders são preparados.
- Giroscópio do Deck, e o botão Steam pausa o jogo.
- Cada sessão guarda um log com fps, memória e pressão de memória, para quem quiser relatar um problema.

## Defeitos conhecidos

- **Piscadas.** A grama pode ficar branca por um quadro, principalmente ao girar a câmera em área aberta. A causa é
  conhecida (a GPU lê dados que o jogo já reescreveu) e a correção está em andamento.
- **Névoa errada** em algumas áreas, como o mercado da cidade do castelo. Provavelmente a mesma causa.
- **Memória no limite.** O jogo ocupa quase toda a memória do Deck. Se ela acabar de verdade, o port fecha o jogo
  antes que o Deck congele.
- **Primeira abertura demorada.** A preparação dos shaders leva mais de 30 minutos, uma vez só.
- **Só o começo do jogo foi testado.** Outros donos de Deck relatam travadas da GPU em áreas mais adiante.
- A montagem do jogo no próprio Deck leva de uma a duas horas.

## Do que você precisa

- Steam Deck (LCD ou OLED) com SteamOS.
- O arquivo `.nup` da sua cópia do jogo, com a atualização v131072 (a mesma que o Hookshot v2.1.0 pede).
- 45 GB livres para a montagem. Depois de instalado, o jogo ocupa uns 35 GB.
- Quem já montou o jogo com o **Hookshot v2.1.0** pode apontar essa pasta e pular a montagem.

## Como instalar

1. No Deck, entre no Modo Desktop.
2. Baixe o arquivo [Instalar-Zelda-OoT.desktop](https://github.com/KewinBR/deckport-zelda-oot/releases/latest) e
   abra. Ou, pelo Konsole:
   ```bash
   curl -L https://github.com/KewinBR/deckport-zelda-oot/releases/latest/download/instalar.sh | bash
   ```
3. O instalador acha o `.nup` no Deck e no cartão SD, pergunta onde instalar e faz o resto: baixa o Hookshot oficial,
   monta o jogo, coloca o renderizador do port, gera as texturas e a vegetação do Deck e cria o atalho na Steam.
4. Volte ao Modo de Jogo e abra pela biblioteca.

O instalador não muda nada no sistema. Tudo fica na sua pasta pessoal e, se você escolher, no cartão SD.

## Atualizar e desinstalar

Para atualizar, rode o instalador de novo (passo 2 acima). Ele baixa a versão mais nova e aproveita o que já foi
feito: o jogo montado e as texturas não são refeitos.

Para desinstalar, no Konsole:
```bash
python3 ~/.local/share/zelda-oot-deck/instalador/desinstalar.py
```
Isso tira o atalho da Steam, o port, a configuração, os mods gerados e os logs. Os saves continuam em
`~/.local/share/hookshot`, e a pasta do jogo montado também fica, de volta ao renderizador original do Hookshot. Com
`--com-jogo`, a pasta do jogo que o instalador montou também é apagada. Uma pasta que você montou antes do port nunca
é apagada.

## Como relatar um problema

Abra uma issue e anexe o log da sessão em que o problema aconteceu. Os logs ficam em `zelda-oot-deck/logs/`, dentro
do local que você escolheu na instalação. Diga a área do jogo e o que você estava fazendo.

## O que é do Hookshot e o que é do Deckport

O Hookshot faz o trabalho pesado: recompilar o jogo, traduzir os shaders e desenhar com Vulkan. Os ícones de botão do
Deck também são dele. O Deckport troca o renderizador por uma versão com alterações para o Deck, e acrescenta o
lançador, os mods gerados a partir da sua cópia do jogo, o menu e o instalador.

As alterações no renderizador estão em [patches/](patches/), como scripts aplicados sobre o Hookshot v2.1.0, e o
arquivo `deckport-210.patch` tem a diferença inteira.

## Créditos e licença

- [Hookshot](https://github.com/NotRexed/Hookshot), de NotRexed e colaboradores, sob GPL-3.0.
- Deckport por Kewin Lima.
- Fontes: Cinzel Decorative e Barlow, sob a SIL Open Font License.

Este repositório é distribuído sob a GPL-3.0, a mesma licença do Hookshot. The Legend of Zelda é marca da Nintendo.
Este projeto não tem vínculo com a Nintendo.
