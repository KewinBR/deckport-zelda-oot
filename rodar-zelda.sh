#!/usr/bin/env bash
# Roda NO DECK. Abre o Zelda: Ocarina of Time (Switch 2) pelo port nativo Hookshot, compilado na VPS.
#   bash rodar-zelda.sh
# Jogo compilado: ~/zelda-oot/game (pasta de saída do Hookshot: bin/hookshot ou hookshot, image.bin, .game/).
# Log desta abertura: ~/zelda-oot/logs/; log do jogo: ~/zelda-oot/game/hookshot_log.txt.
# Teste sem ninguém no controle: linhas "<botão>" escritas em /tmp/zelda-pad.txt viram toques (HOS_INPUT_LIVE).
set -uo pipefail
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}
# Instalação pelo instalador público (deckport-zelda-oot): os caminhos vêm de ~/.config/zelda-oot-deck/caminhos.env
# (ZELDA_BASE, ZELDA_JOGO, ZELDA_SCRIPTS). Sem o arquivo, vale o arranjo do Deck do Kewin.
[[ -f ${ZELDA_CONF:-$HOME/.config/zelda-oot-deck/caminhos.env} ]] && . "${ZELDA_CONF:-$HOME/.config/zelda-oot-deck/caminhos.env}"
base=${ZELDA_BASE:-$HOME/zelda-oot}
scripts=${ZELDA_SCRIPTS:-$HOME/steam-deck/scripts}
# v2.0.12 + Deckport + 800p em game-2012 (patches/deckport-2012.patch, patch_800p.py). A falta de memória perto do castelo
# vale pras duas versões (2026-11-10); o 800p deixa 1,9 GB livres no mesmo save, contra 0,6. Reservas: game-dp (v2.0.11),
# game-2011 e game (v2.0.7): ZELDA_JOGO=$base/<pasta> volta pra elas.
# v2.1.0 (game-210, 2026-11-11): Hookshot novo com os patches Deckport (patches/deckport-210.patch) e o menu em ImGui.
# game-2012 fica de reserva: ZELDA_JOGO=$base/game-2012.
jogo=${ZELDA_JOGO:-$base/game-210}

# Uma abertura por vez (lição do inFAMOUS: duas aberturas juntas e o earlyoom matou por memória).
if pgrep -f "^\./(bin/)?hookshot$" >/dev/null || [[ -n $(find /tmp/zelda-abrindo -newermt '-60 seconds' 2>/dev/null) ]]; then
    echo "rodar-zelda: o jogo já está abrindo ou aberto, saindo" >&2
    exit 0
fi
touch /tmp/zelda-abrindo
mkdir -p "$base/logs"
log=$base/logs/zelda-$(date +%Y%m%d-%H%M%S).log
exec > "$log" 2>&1
ln -sf "$log" "$base/ultima.log"
echo "início $(date '+%F %T')"
unset LD_PRELOAD LD_LIBRARY_PATH
[[ -f $jogo/image.bin ]] || { echo "falta o jogo compilado em $jogo"; exit 1; }

# Experimento: VAR=valor por linha em ~/zelda-oot/exp-env, lido uma vez e apagado.
if [[ -f $base/exp-env ]]; then
    while IFS= read -r linha; do [[ $linha == *=* ]] && export "$linha" && echo "exp-env: $linha"; done < "$base/exp-env"
    rm -f "$base/exp-env"
fi

# Tela do Deck: tela cheia na resolução nativa. Perfil portátil do Switch 2 (mais leve).
export HOS_FULLSCREEN=${HOS_FULLSCREEN:-1}
export HOS_HANDHELD=${HOS_HANDHELD:-1}
export HOS_FPS_LOG=${HOS_FPS_LOG:-1}
export HOOKSHOT_NO_UPDATE_CHECK=1
# 16:10 sem barras (patch_1610.py no executável): a imagem 2304x1440, câmera 1,6, interface no meio na vertical.
# Só na pasta game-dp; nas outras o executável ignora telas mais altas que 16:9.
export HOS_ASPECT=${HOS_ASPECT:-1.6}
# Saída 1424x800 (patch_800p.py, só no executável de game-2012): imagem 1280x800, a tela do Deck, e cena 960x600. No
# mesmo save, 31 fps e 1,9 GB livres, contra 15 fps e 0,6 GB na saída do jogo (2304x1440). Nas outras pastas o valor 5 é
# ignorado (volta pra saída do jogo).
# v2.1.0 (game-210): a saída é um tamanho, e o "5" antigo virou 5120x2880 lá; patch_800p.py faz o tamanho valer no
# perfil portátil.
if grep -qE "^version=v2\.([1-9]|[1-9][0-9])\." "$jogo/hookshot_version.txt" 2>/dev/null || [[ $jogo == *game-210* ]]; then export HOS_OUTPUT_RES=${HOS_OUTPUT_RES:-1424x800}; else export HOS_OUTPUT_RES=${HOS_OUTPUT_RES:-5}; fi
# Mod de texturas reduzidas (ferramentas/reduzir_texturas.py, gerado na VPS a partir do romfs, fica só no Deck e na VPS,
# nunca no git): texturas com lado acima de 1024 perdem os níveis de cima (2018 texturas, 2,9 GB a menos de 16,2 GB) e
# a tabela de tamanhos acompanha. Sem a pasta, o jogo segue sem mod.
# 2026-11-10: com o de 1024 o castelo carregou e deu pra andar numa sala antes da memória acabar; o de 512 (10268
# texturas, 6,2 GB a menos) é o padrão agora. O de 1024 segue em mods-tex1024.
# Junto, o mod de vegetação (ferramentas/reduzir_vegetacao.py, no Pack/Foliage.pack.zs: grama com metade da densidade
# e distâncias da vegetação a 60%): na Cidadela 18,5 -> 19,8 fps. mods-tex512-veg tem os dois (links).
# Desde 2026-11-10 o menu do port (aba Gráficos > Mundo) escolhe os mods e a sombra; os valores ficam no
# hookshot_options.ini (deckport_*) e valem na próxima abertura. opcoes_deckport monta $base/mods-atual com links:
# texturas (deckport_textures: 0 mods-tex1024, 1 mods-tex512) e vegetação (veg-niveis/d<distância>g<grama>, gerados na
# VPS por reduzir_vegetacao.py; d4g2 = original, sem mod), e põe RX_VK_SHADOW_DIV (deckport_shadows: 0 1, 1 2, 2 4).
# HOS_MODS ou RX_VK_SHADOW_DIV já definidos de fora (exp-env, teste) vencem.
mods_fora=${HOS_MODS:-}; sombra_fora=${RX_VK_SHADOW_DIV:-}
opcoes_deckport() {
    local ini=$jogo/hookshot_options.ini tex=1 dist=2 grama=0 sombra=1
    if [[ -f $ini ]]; then
        tex=$(awk -F= '$1=="deckport_textures"{print $2+0}' "$ini"); tex=${tex:-1}
        dist=$(awk -F= '$1=="deckport_distance"{print $2+0}' "$ini"); dist=${dist:-2}
        grama=$(awk -F= '$1=="deckport_grass"{print $2+0}' "$ini"); grama=${grama:-0}
        sombra=$(awk -F= '$1=="deckport_shadows"{print $2+0}' "$ini"); sombra=${sombra:-1}
    fi
    local m=$base/mods-atual
    rm -rf "$m"; mkdir -p "$m"
    if (( tex == 0 )); then ln -s "$base/mods-tex1024/deckport-texturas" "$m/deckport-texturas"
    else ln -s "$base/mods-tex512/deckport-texturas" "$m/deckport-texturas"; fi
    # Ícones de botão do Steam Deck (Hookshot v2.1.0, pasta prompts/ do jogo): um mod com a tabela de tamanhos faz o
    # Hookshot desistir da fonte dos ícones. A tabela do mod de texturas fica fora do mod, já com a entrada da fonte
    # aumentada (ferramentas/tabela_prompts.py), e vai para prompts/rsizetable.zs, que o Hookshot serve.
    local tab=$base/mods-tex512/prompts-rsizetable.zs
    (( tex == 0 )) && tab=$base/mods-tex1024/prompts-rsizetable.zs
    if [[ -f $tab && -d $jogo/prompts && -z $mods_fora ]]; then
        [[ -f $jogo/prompts/rsizetable-hookshot.zs ]] || cp "$jogo/prompts/rsizetable.zs" "$jogo/prompts/rsizetable-hookshot.zs"
        cmp -s "$tab" "$jogo/prompts/rsizetable.zs" || { cp "$tab" "$jogo/prompts/rsizetable.zs.novo" && mv "$jogo/prompts/rsizetable.zs.novo" "$jogo/prompts/rsizetable.zs"; }
    fi
    [[ -d $base/veg-niveis/d${dist}g${grama} ]] && ln -s "$base/veg-niveis/d${dist}g${grama}/deckport-vegetacao" "$m/deckport-vegetacao"
    export HOS_MODS=${mods_fora:-$m}
    local div=(1 2 4)
    export RX_VK_SHADOW_DIV=${sombra_fora:-${div[$sombra]:-2}}
    echo "opções do port: texturas $tex, distância $dist, grama $grama, sombra $sombra -> HOS_MODS=$HOS_MODS RX_VK_SHADOW_DIV=$RX_VK_SHADOW_DIV"
}
opcoes_deckport
# Base v2.0.7 (2026-11-09): o crash write 0x40 do RADV foi corrigido na v2.0.6, então a compilação de shaders na abertura
# volta (sem RX_VK_NO_WARM / RX_VK_PRECOMPILE=0) e o pino de 32 lanes fica (os shaders do Switch esperam warp de 32).
# Travamento da GPU do Deck: o task shader de culling 2c56dc1006942f74 (teste de oclusão por grade que roda por segundos
# no RDNA2, issue #817 do Hookshot). O renderizador Deckport desliga só o culling dele (RX_VK_MESH_NOCULL, padrão no
# código): todo meshlet é desenhado e nada some. Não usar mais RX_VK_SKIP_CODE nem a lista longa de RX_VK_SKIP_PROG:
# tiravam ~30 programas (casas, plataformas, rupees). Não exportar RX_VK_MESH_NOCULL aqui: variável RX_VK_MESH* muda o
# carimbo do cache de programas e o jogo recompila tudo.
# Configurações que funcionaram no Deck (issue #817): otimizador do driver nos mesh, limites de memória (o Deck diz ter
# ~6 GB de VRAM e os limites do preset mínimo não pegam), e menos espera entre envios no RADV (issue #1000).
export RX_VK_MESH_OPT=${RX_VK_MESH_OPT:-1}
# Travamento da GPU em área aberta (Rancho Lon Lon, 2026-11-10): com o caminho nativo de task/mesh shaders, mesmo com o
# NOCULL, a GPU trava no task shader de culling 2c56dc1006942f74 numa vista da paisagem (5 reproduções sem tela, também no
# SteamOS 3.9.5). O caminho alternativo do Hookshot (task e mesh como compute) rodou 15 min girando a câmera no mesmo save,
# sem travar e sem faltar nada na cena: 18 fps contra 21. Mas ele pisca muito (RX_VK_AFLASH,
# câmera girando no rancho: 208-236 por 1000 quadros, contra 8,5 no nativo; WAIT_GPU=-1 não muda). Voltou ao nativo (0)
# em 2026-11-10 23h50. Próximo passo: alternativo só nos programas com o task 2c56dc1006942f74.
# (O cache de programas é separado: trocar entre os dois recompila tudo, ~10 min.)
export RX_VK_FORCE_MESH_FALLBACK=${RX_VK_FORCE_MESH_FALLBACK:-0}
# v2.1.0: só os desenhos com task shader vão pelo caminho alternativo (o travamento está no task 2c56dc1006942f74; os
# mesh sem task ficam nativos). No rancho girando a câmera: 13 min sem travar, 22-24 fps. RX_VK_TASK_MESH_FALLBACK=0 volta.
export RX_VK_TASK_MESH_FALLBACK=${RX_VK_TASK_MESH_FALLBACK:-1}
# Texturas (2026-11-10): dentro do castelo elas chegavam a 1,95 GB do orçamento de 2048 e a memória do Deck acabava;
# com 1024 o renderizador passa um pouco do limite (~1,3 GB), mas é ~0,6 GB a menos.
export RX_VK_VRAM_MB=${RX_VK_VRAM_MB:-1024}
export RX_VK_TEX_MAX_MB=${RX_VK_TEX_MAX_MB:-128}
export RX_VK_TEX_MAX_DIM=${RX_VK_TEX_MAX_DIM:-1024}
mirror_fora=${RX_VK_MIRROR_MB:-}
export RX_VK_MIRROR_MB=${RX_VK_MIRROR_MB:-256}
# Memória perto do castelo (2026-11-10): a sombra de escrita (write-back diff) cabia em 512 MB nas GPUs integradas; com
# 64 MB o renderizador ocupa ~450 MB a menos (2013 -> ~1550 MB privados) e o fps não muda (15,2 x 15,0 no mesmo save).
export RX_VK_WB_SHADOW_MB=${RX_VK_WB_SHADOW_MB:-64}
# Piscada da v2.0.12 até na interface (2026-11-10): a v2.0.12 adia texturas ASTC quando o envio de um quadro passa de
# 40 ms (RX_VK_UPLOAD_BUDGET_MS); no Deck isso acontece em jogo normal (433 adiadas numa sessão de 4 min) e a textura
# falta por alguns quadros. 0 volta ao da v2.0.11 (sem adiar).
export RX_VK_UPLOAD_BUDGET_MS=${RX_VK_UPLOAD_BUDGET_MS:-0}
export RX_VK_BATCH_POLL_US=${RX_VK_BATCH_POLL_US:-2000}
# Iluminação piscando (tela inteira preta/branca por um quadro): no Deck (memória unificada, sem o espelho de VRAM) a GPU
# lê a memória do jogo ao vivo e o jogo escreve o medidor de exposição do quadro seguinte antes de a GPU ler o atual
# (issues #1186/#1126 do Hookshot). Não deixar o jogo correr à frente da GPU resolve. O 1 (espera o quadro anterior,
# 30 -> 27 fps) diminuiu mas ainda piscava ao girar a câmera; o -1 do Deckport (patch_waitself.py) espera o próprio
# quadro no present (~25 fps). O patch "não testado" da #1126 travou o jogo no carregamento: não usar.
# Desde 2026-11-10 (v2.0.12 + PR #1133 do Hookshot no renderizador, que anota as escritas da GPU nas ligações diretas
# de buffer e faz a cópia da CPU esperar por elas): 1 basta. Girando a câmera sem tela, flashes por 1000 quadros:
# atual sem espera 41,5; atual com -1 14,3; PR #1133 com 1 8,5; PR #1133 com 0 7,1. O -1 corta o fps pela metade
# parado em 800p (31 -> 16).
export RX_VK_WAIT_GPU=${RX_VK_WAIT_GPU:-1}
# Marcadores na GPU: se travar, o log (e o vigia do patch #817) diz qual programa.
export RX_VK_CHECKPOINTS=${RX_VK_CHECKPOINTS:-1}
# Folhas e grama brancas por um quadro e HUD embaralhado: a GPU lê os dados do quadro na memória do jogo enquanto o jogo
# já os reescreve (valentas, issue 1000 do Hookshot). O espelho de VRAM dá à GPU uma cópia. No rancho, girando a câmera,
# o contador AFLASH foi de 2.339 para 618 e o fps não caiu. O teste foi com 1024 MB de espelho (com os 256 de antes não
# foi medido), e a memória livre mais o swap livre ficaram iguais aos do teste sem espelho. RX_VK_MIRROR=0 volta.
export RX_VK_MIRROR=${RX_VK_MIRROR:-1}
[ "$RX_VK_MIRROR" = 1 ] && export RX_VK_MIRROR_MB=${mirror_fora:-512}   # (512: 22 piscadas por 1000 jogando, não pior que 1024)
# A v2.1.0 faz a CPU esperar pelos resultados que a GPU escreve (#1375 do Hookshot). Sem a espera o jogo os lê com um
# quadro de atraso, como a v2.0.14 fazia: no rancho, parado, 23,7 fps viraram 25,1 e 28,9. RX_VK_NO_READBACK_WAIT=0 volta.
export RX_VK_NO_READBACK_WAIT=${RX_VK_NO_READBACK_WAIT:-1}
[ "$RX_VK_NO_READBACK_WAIT" = 0 ] && unset RX_VK_NO_READBACK_WAIT
# Dados de cada sessão para análise: o contador de piscadas no log do jogo (uma linha a cada 600 quadros).
export RX_VK_AFLASH=${RX_VK_AFLASH:-1}
# Controle remoto pra teste (não atrapalha o controle de verdade).
export HOS_INPUT_LIVE=${HOS_INPUT_LIVE:-/tmp/zelda-pad.txt}
: > "$HOS_INPUT_LIVE"

# Controle: no Game Mode a Steam esconde o controle do Deck (28DE:1205) e entrega o virtual (28DE:11FF), sem
# giroscópio e sem botões de trás. O jogo ignora o virtual e lê o do Deck direto (mesmo truque do inFAMOUS).
env | grep -iE '^SDL_|SteamVirtualGamepad|STEAM_INPUT' | sed 's/^/env: /' || true
controle=(env -u SDL_GAMECONTROLLER_ALLOW_STEAM_VIRTUAL_GAMEPAD SDL_GAMECONTROLLER_IGNORE_DEVICES=0x28DE/0x11FF)

# Giroscópio: a Steam deixa desligado; liga depois que o jogo abriu o controle, e repete enquanto ele roda.
rm -f "$jogo/hookshot_log.txt"
ajudantes=()
setsid python3 "$scripts/ligar-imu.py" --manter "$jogo/hookshot_log.txt" \
    --marca "hid: controller 0 connected" --processo "^\./(bin/)?hooksho[t]$" --atual "$jogo/hookshot_log.txt" \
    --espera 1800 </dev/null >/dev/null 2>&1 &
ajudantes+=($!)

# Botão Steam e menu rápido pausam o jogo (o gamescope não manda perda de foco).
if [[ -n ${SteamAppId:-} ]]; then
    setsid python3 "$scripts/congelar-no-menu-steam.py" "$SteamAppId" "^\./(bin/)?hookshot$" \
        </dev/null >>"$base/logs/congelar.log" 2>&1 &
    ajudantes+=($!)
fi
# Ao sair, os ajudantes saem junto: com um deles vivo a Steam acha que o jogo segue aberto (o reaper espera todos).
trap 'kill "${ajudantes[@]}" 2>/dev/null' EXIT

cd "$jogo"
bin=./hookshot; [[ -x ./bin/hookshot ]] && bin=./bin/hookshot
# Huge pages transparentes desligadas só para o jogo (2026-11-12, pista do issue #1000 do Hookshot): o SteamOS vem com
# THP "always", e pedidos de blocos grandes com a memória fragmentada fazem o kernel despejar o jogo para o swap. O
# prctl vale para o processo e passa pelo exec; o sistema não muda. No rancho, em 10 min, o fps não mudou; o efeito
# esperado é em sessão longa. ZELDA_THP=1 deixa como o sistema manda.
prefixo=()
[[ ${ZELDA_THP:-0} != 1 && -f $scripts/sem-thp.py ]] && prefixo=(python3 "$scripts/sem-thp.py")
# "Aplicar e reiniciar" do menu do port: o jogo deixa deckport_reiniciar ao lado do ini e fecha; aqui ele abre de novo
# com as opções novas (os mods e a sombra só valem na abertura).
rm -f "$jogo/deckport_reiniciar"
while :; do
echo "abrindo $bin"
"${controle[@]}" "${prefixo[@]}" "$bin" &
pid_jogo=$!
# Depois de um CRASH o Hookshot fica parado em vez de fechar: fecha ele, pra a pessoa voltar pro Game Mode.
( while kill -0 $pid_jogo 2>/dev/null; do
      if grep -q "^\[hos host\] CRASH:" "$log"; then sleep 3; echo "vigia: crash no log, fechando o jogo"; kill -KILL $pid_jogo; fi
      sleep 2
  done ) &
# Memória (2026-11-10): a sessão de 2026-11-09 23:16 acabou a RAM (15 GB) e o swap (8,6 GB) em Hyrule Field e o Deck
# travou inteiro (o earlyoom não chegou a matar). A cada 5 s o log ganha uma linha "mem:" (livre, swap livre, GTT, RSS e
# swap do jogo); com menos de 2500 MB entre RAM livre e swap livre (1200 era tarde: a Steam ia pro swap e travava; 3500 fechava cedo, com o zram ainda aguentando), o jogo era fechado antes de o Deck congelar.
# 2026-11-12: os 2500 fechavam o jogo em pico passageiro. Na troca de área o jogo carrega a área nova antes de soltar a
# velha (GTT +1,1 GB em 25 s) e a soma caiu a 2357 MB com 2,1 GB de swap ainda livres, numa tela de carregamento. Agora
# fecha com a pressão de memória do kernel (PSI full avg10) em 35% ou mais, ou com menos de 1300 MB na soma.
( n=0
  while kill -0 $pid_jogo 2>/dev/null; do
      livre=$(awk '/^MemAvailable/{a=$2} /^SwapFree/{s=$2} END{print int((a+s)/1024)}' /proc/meminfo)
      if (( n++ % 5 == 0 )); then
          gtt=$(( $(cat /sys/class/drm/card*/device/mem_info_gtt_used 2>/dev/null | head -1) / 1048576 ))
          echo "mem: $(date +%T) $(awk '/^MemAvailable|^SwapFree|^Shmem:/{printf "%s %d MB ",$1,$2/1024}' /proc/meminfo)GTT: $gtt MB jogo $(awk '/^VmRSS|^VmSwap|^RssShmem/{printf "%s %d MB ",$1,$2/1024}' /proc/$pid_jogo/status 2>/dev/null)"
      fi
      # Pressão de memória (PSI): a parte do tempo, nos últimos 10 s, em que tudo ficou parado esperando memória.
      # É o sinal de que o Deck está engasgando de verdade; a soma livre sozinha fechava o jogo em pico de carregamento.
      psi=$(awk '/^full/{sub("avg10=","",$2); print int($2)}' /proc/pressure/memory 2>/dev/null); psi=${psi:-0}
      (( n % 5 == 1 )) && echo "psi: $(date +%T) full avg10 $psi% livre+swap $livre MB"
      if (( livre < 1300 || psi >= 35 )); then
          echo "vigia: memória acabando ($livre MB livres com o swap, pressão $psi%), fechando o jogo; maiores mapeamentos (RSS+swap, MB):"
          # (2026-11-10: o que cresce perto do castelo não aparecia no VmRSS; isto diz em qual mapeamento está)
          awk '/^[0-9a-f]+-[0-9a-f]+ /{n=($6==""?"[anon]":$6)} /^Rss:/{r[n]+=$2} /^Swap:/{w[n]+=$2}
               END{for(k in r) printf "%7d %7d %s\n",(r[k]+w[k])/1024,w[k]/1024,k}' /proc/$pid_jogo/smaps 2>/dev/null |
              sort -rn | head -12 | sed 's/^/vigia:   /'
          kill -KILL $pid_jogo
      fi
      sleep 1
  done ) &
wait $pid_jogo
codigo=$?
echo "fim $(date '+%F %T') código $codigo"
if [[ -f $jogo/deckport_reiniciar ]]; then
    rm -f "$jogo/deckport_reiniciar"
    echo "reiniciando pelo menu do port"
    opcoes_deckport
    continue
fi
break
done
tail -40 "$jogo/hookshot_log.txt" 2>/dev/null | sed 's/^/jogo: /'
# O log inteiro do jogo fica guardado por sessão (fps, tempos de CPU e GPU por quadro, piscadas, memória), comprimido;
# o hookshot_log.txt é apagado na abertura seguinte. Ficam as 30 sessões mais novas.
if [ -s "$jogo/hookshot_log.txt" ]; then
    gzip -c "$jogo/hookshot_log.txt" > "${log%.log}-jogo.txt.gz" 2>/dev/null
    ls -t "$base"/logs/zelda-*-jogo.txt.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
fi
exit $codigo
