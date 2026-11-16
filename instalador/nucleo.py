"""Parte sem tela do instalador do Deckport Zelda: Ocarina of Time.

Acha a cópia do jogo do próprio jogador (um arquivo .nup, ou uma pasta já montada pelo Hookshot ou pelo Longshot),
baixa o Longshot oficial (a continuação do Hookshot), monta o jogo com ele, troca o renderizador pelo do port, gera os
mods de textura e de vegetação a partir dos arquivos do jogo, instala o lançador e cria o atalho na Steam. Nada do jogo
sai do Deck nem é baixado. Uma pasta montada por outra versão é montada de novo a partir dos arquivos que ela guarda
(romfs e o código do jogo), sem o .nup.

Layout instalado (DESTINO = a pasta pessoal no SSD ou a raiz do cartão SD):
    DESTINO/zelda-oot-deck/jogo/          a pasta do jogo montada pelo Hookshot
    DESTINO/zelda-oot-deck/mods-tex512/   texturas reduzidas (e mods-tex1024/)
    DESTINO/zelda-oot-deck/veg-niveis/    os níveis de vegetação do menu do port
    DESTINO/zelda-oot-deck/logs/          um log por sessão de jogo
    ~/.local/share/zelda-oot-deck/        o port: lançador, renderizador, ferramentas, Longshot, instalador
    ~/.config/zelda-oot-deck/             config.json e caminhos.env (lido pelo lançador)
"""
from __future__ import annotations

import filecmp
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

APP = "zelda-oot-deck"
CONFIG = Path.home() / ".config" / APP / "config.json"
CAMINHOS = Path.home() / ".config" / APP / "caminhos.env"
AQUI = Path(__file__).resolve().parent
PACOTE = AQUI.parent  # a raiz do pacote da release (VERSAO, rodar-zelda.sh, deck/, renderizador/, instalador/)
APPDIR = Path.home() / ".local" / "share" / APP

# A base: o Longshot, a continuação do Hookshot (git.magicbean.dev/MagicBeanDev/Longshot, GPL-3). Desde a nightly 18x o
# builder compila o renderizador na montagem, com as fontes que carrega (sem .so pronto, commit 25726217): o patch do
# port (patches/BASE_PATCH: as alterações do Deck) é aplicado nessas fontes, e a montagem já sai com o renderizador do
# port e os shaders preparados com ele. (O Hookshot saiu do GitHub em 2026-11-13.)
BASE_NOME = "Longshot"
BASE_VERSAO = "v3.0.0-rc.5"
BASE_ARQUIVO = f"Longshot-{BASE_VERSAO}-x86_64.AppImage"
BASE_URL = f"https://git.magicbean.dev/MagicBeanDev/Longshot/releases/download/{BASE_VERSAO}/{BASE_ARQUIVO}"
BASE_SHA256 = "0912757a0b8e368e82c4825088e3fead91ddb3b1eb139a40d2db9aa57ff84bf9"
BASE_BYTES = 99600888
BASE_PATCH = f"deckport-longshot-{BASE_VERSAO}.patch"
# (a pasta do jogo montada pelo port guarda a identidade da base com que foi montada: a versão do Longshot e a soma do
# patch. Mudou qualquer um dos dois, ela é montada de novo)
MARCA = "deckport_base.txt"
# As nightlies do Longshot somem do servidor depois de uns dias: o mesmo arquivo vai também como anexo do release do
# port, e o instalador tenta os dois (a soma é conferida em qualquer um).
REPO = "KewinBR/deckport-zelda-oot"


def versao_do_pacote(pacote: Path | None = None) -> str:
    try:
        return ((pacote or PACOTE) / "VERSAO").read_text().strip()
    except OSError:
        return ""


def urls_da_base(pacote: Path | None = None) -> list[str]:
    v = versao_do_pacote(pacote)
    espelho = [f"https://github.com/{REPO}/releases/download/{v}/{BASE_ARQUIVO}"] if v else []
    return [BASE_URL, *espelho]


def identidade_base(pacote: Path | None = None) -> str:
    """'Longshot v3.0.0-rc.5 + 1a2b3c4d5e6f': a base e a soma do patch do port sobre ela."""
    try:
        sha = hashlib.sha256(((pacote or PACOTE) / "patches" / BASE_PATCH).read_bytes()).hexdigest()[:12]
    except OSError:
        sha = "?"
    return f"{BASE_NOME} {BASE_VERSAO} + {sha}"


def aplicar_patch(patch: Path, pasta: Path) -> None:
    """O patch do port nas fontes do builder (git apply; sem o git, o patch do sistema)."""
    for cmd in (["git", "apply", "-p1", "--whitespace=nowarn", str(patch)], ["patch", "-p1", "-N", "-i", str(patch)]):
        try:
            r = subprocess.run(cmd, cwd=pasta, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except FileNotFoundError:
            continue
        if r.returncode == 0:
            return
        raise RuntimeError(f"o patch do port não entrou nas fontes do Longshot ({cmd[0]}): {r.stdout.strip()[-300:]}")
    raise RuntimeError("falta o git ou o patch para aplicar o patch do port")


def trocar_jogo(raiz: Path, novo: Path, atual: Path) -> Path:
    """Põe a pasta recém-montada (novo) no lugar de raiz/jogo, levando as opções do jogador (as do Longshot e as do menu
    do port, no longshot_options.ini) da pasta em uso (atual). Uma pasta montada antes do port (fora de raiz) fica como
    está; a raiz/jogo antiga sai (o romfs da nova é o mesmo, por hardlink: nada se perde)."""
    for nome in ("longshot_options.ini", "longshot_env.txt"):
        if (atual / nome).is_file() and not (atual / nome).is_symlink():
            shutil.copy2(atual / nome, novo / nome)
    final, velho = raiz / "jogo", raiz / "jogo-velho"
    shutil.rmtree(velho, ignore_errors=True)
    if final.exists():
        final.replace(velho)
    novo.replace(final)
    shutil.rmtree(velho, ignore_errors=True)
    return final


def marca_da_pasta(pasta: Path) -> str:
    try:
        return (pasta / MARCA).read_text().strip()
    except OSError:
        return ""
# (o Longshot baixa as ferramentas da montagem à parte, uns 520 MB: ficam dentro do port, para o desinstalador levar)
BASE_FERRAMENTAS = APPDIR / "longshot" / "builder"

NUP_MINIMO = 20 * 1024 ** 3      # o .nup do jogo tem 25,6 GB
ESPACO_MONTAR = 45 * 1024 ** 3   # jogo montado (~35 GB com os caches de shader) e a folga da montagem
ESPACO_SO_PORT = 6 * 1024 ** 3   # só os mods, sobre uma pasta já montada pela mesma versão
ESPACO_REFAZER = 20 * 1024 ** 3  # montar de novo uma pasta de outra versão no mesmo disco (o romfs vira link, não cópia)

# Os níveis do menu do port (Gráficos > Mundo): distância da vegetação e densidade da grama.
DISTANCIAS = [0.4, 0.5, 0.6, 0.8, 1.0]
GRAMAS = [(0.5, 0.67), (0.75, 0.84), (1.0, 1.0)]   # (densidade, folhas por tufo)


@dataclass
class Jogo:
    caminho: Path
    tamanho: int
    tipo: str            # "nup" ou "pasta"
    versao: str = ""     # (pasta) quem a montou: "Longshot v3.0.0-rc.3", "Hookshot v2.1.0"
    marcado: bool = True

    @property
    def serve(self) -> bool:
        """Uma pasta montada pelo port com a mesma base e o mesmo patch (uma instalação anterior): entra como está.
        Montada pelo Longshot sozinho, o renderizador e os shaders preparados nela não são os do port (a primeira
        abertura levaria horas); ela é montada de novo, como as de outra versão."""
        return self.tipo == "pasta" and marca_da_pasta(self.caminho) == identidade_base()

    @property
    def refazer(self) -> bool:
        """Uma pasta de outra versão que guarda os arquivos do jogo: dá para montar de novo sem o .nup."""
        return self.tipo == "pasta" and not self.serve and exefs_da_pasta(self.caminho) is not None

    @property
    def local(self) -> str:
        p = (self.caminho.parent if self.tipo == "nup" else self.caminho).as_posix()
        return p.replace(Path.home().as_posix(), "~")


@dataclass
class Local:
    nome: str
    raiz: Path
    livre: int
    sd: bool


@dataclass
class Progresso:
    etapa: int = 0
    fracao: float = 0.0  # da etapa atual
    total: float = 0.0
    texto: str = ""
    erro: str = ""
    pronto: bool = False
    restante_s: float = -1
    _trava: threading.Lock = field(default_factory=threading.Lock)


def lugares_de_busca() -> list[Path]:
    home = Path.home()
    lugares = [home / "Downloads", home / "Desktop", home / "Documents", home / "Games", home]
    media = Path("/run/media")
    if media.is_dir():
        for usuario in media.iterdir():
            if usuario.is_dir():
                lugares += [p for p in usuario.iterdir() if p.is_dir()]
    return [p for p in lugares if p.is_dir()]


def versao_da_pasta(pasta: Path) -> str:
    """Quem montou a pasta ("Longshot v3.0.0-rc.3", pelo longshot_version.txt; "Hookshot v2.1.0", pelo
    hookshot_version.txt), ou vazio se não é uma pasta montada."""
    try:
        if not (pasta / "image.bin").is_file() or not (pasta / "romfs").is_dir():
            return ""
    except OSError:
        return ""
    for nome in ("Longshot", "Hookshot"):
        try:
            for linha in (pasta / f"{nome.lower()}_version.txt").read_text().splitlines():
                if linha.startswith("version="):
                    return f"{nome} {linha.split('=', 1)[1].strip()}"
        except OSError:
            continue
    return ""


def exefs_da_pasta(pasta: Path) -> Path | None:
    """O código do jogo que a pasta guarda para as atualizações (.longshot_exefs ou .hookshot_exefs)."""
    for nome in (".longshot_exefs", ".hookshot_exefs"):
        p = pasta / nome
        try:
            if p.is_dir() and any(p.iterdir()) and (pasta / "romfs").is_dir():
                return p
        except OSError:
            continue
    return None


def procurar_jogos(lugares: list[Path] | None = None, profundidade: int = 4) -> list[Jogo]:
    """Os .nup grandes e as pastas já montadas pelo Hookshot, nas pastas de costume (sem entrar em pastas ocultas)."""
    achados: dict[Path, Jogo] = {}
    # a pasta do jogo de uma instalação anterior do port (a busca não entra nas pastas zelda-oot-deck)
    if lugares is None and ler_config().get("jogo"):
        anterior = Path(ler_config()["jogo"])
        v = versao_da_pasta(anterior)
        if v:
            achados[anterior.resolve()] = Jogo(anterior, 0, "pasta", v)
    for raiz in lugares or lugares_de_busca():
        base = len(raiz.parts)
        for pasta, subpastas, arquivos in os.walk(raiz, onerror=lambda e: None):
            aqui = Path(pasta)
            if len(aqui.parts) - base >= profundidade:
                subpastas[:] = []
            if "image.bin" in arquivos and "romfs" in subpastas:   # uma pasta montada: não desce nela
                v = versao_da_pasta(aqui)
                if v and aqui.parent.name != APP:
                    achados[aqui.resolve()] = Jogo(aqui, 0, "pasta", v)
                subpastas[:] = []
                continue
            subpastas[:] = [s for s in subpastas if not s.startswith(".") and s not in (APP, "romfs", "steamapps")]
            for a in arquivos:
                if a.lower().endswith(".nup"):
                    p = aqui / a
                    try:
                        t = p.stat().st_size
                    except OSError:
                        continue
                    if t >= NUP_MINIMO:
                        achados[p.resolve()] = Jogo(p, t, "nup")
    return sorted(achados.values(), key=lambda j: (j.tipo != "pasta", str(j.caminho)))


def locais() -> list[Local]:
    """O SSD (a pasta pessoal) e cada cartão ou disco montado em /run/media (só pontos de montagem de verdade)."""
    res = [Local("ssd", Path.home(), shutil.disk_usage(Path.home()).free, False)]
    vistos = set()
    try:
        with open("/proc/mounts") as f:
            pontos = [linha.split()[1].replace(r"\040", " ") for linha in f]
    except OSError:
        pontos = []
    for ponto in pontos:
        m = Path(ponto)
        if not ponto.startswith("/run/media/") or m in vistos:
            continue
        vistos.add(m)
        try:
            if os.access(m, os.W_OK):
                res.append(Local(m.name, m, shutil.disk_usage(m).free, True))
        except OSError:
            pass
    return res


def ler_config() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {}


def gravar_config(c: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(c, indent=2, ensure_ascii=False))


def instalar_app() -> None:
    """Copia o lançador, os scripts, o renderizador, as artes e o instalador pro APPDIR. O Hookshot baixado e os logs
    ficam como estão."""
    APPDIR.mkdir(parents=True, exist_ok=True)
    for item in PACOTE.iterdir():
        if item.name in ("hookshot", "longshot", "logs", ".git"):
            continue
        alvo = APPDIR / item.name
        if alvo.resolve() == item.resolve():
            continue
        if alvo.is_dir():
            shutil.rmtree(alvo)
        elif alvo.exists():
            alvo.unlink()
        if item.is_dir():
            shutil.copytree(item, alvo)
        else:
            shutil.copy2(item, alvo)
    for sh in ("rodar-zelda.sh",):
        if (APPDIR / sh).exists():
            (APPDIR / sh).chmod(0o755)


class Instalacao(threading.Thread):
    """Etapas: 0 port, 1 baixar o Hookshot, 2 montar o jogo, 3 renderizador do port, 4 texturas, 5 vegetação e
    ícones, 6 atalho na Steam."""

    PESOS = [0.01, 0.03, 0.70, 0.01, 0.20, 0.02, 0.03]

    def __init__(self, jogo: Jogo, destino: Local, progresso: Progresso, criar_atalho, idioma: str = "pt-BR"):
        super().__init__(daemon=True)
        self.jogo = jogo
        self.raiz = destino.raiz / APP
        self.p = progresso
        self.criar_atalho = criar_atalho
        self.idioma = idioma
        self.cancelado = False
        self.proc: subprocess.Popen | None = None
        if jogo.tipo == "pasta":   # nada a montar: o peso da montagem vai para as texturas
            self.PESOS = [0.02, 0.08, 0.0, 0.02, 0.78, 0.05, 0.05]

    # ---- progresso
    def _avanca(self, etapa: int, fracao: float, texto: str = "", restante: float = -1):
        with self.p._trava:
            self.p.etapa, self.p.fracao = etapa, max(0.0, min(1.0, fracao))
            self.p.total = sum(self.PESOS[:etapa]) + self.PESOS[etapa] * self.p.fracao
            self.p.restante_s = restante
            if texto:
                self.p.texto = texto

    def _matar(self):
        """O AppRun do Hookshot é um script que abre o Python da montagem por baixo: matar só ele deixa a extração
        rodando. Cada processo nasce em sessão própria e sai o grupo inteiro."""
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, 9)
            except OSError:
                self.proc.kill()

    def _para(self):
        if self.cancelado:
            self._matar()
            raise RuntimeError("cancelado")

    def cancelar(self):
        self.cancelado = True
        self._matar()

    # ---- o Hookshot oficial
    def _hookshot(self) -> Path:
        """Baixa o Longshot oficial (soma conferida), extrai e põe nele o patch da saída de 800 linhas."""
        # cada versão da base na sua pasta: um builder de outra versão já extraído não é reaproveitado por engano
        pasta = APPDIR / "longshot" / BASE_VERSAO
        pasta.mkdir(parents=True, exist_ok=True)
        for velho in (APPDIR / "longshot").iterdir():   # (as de antes: o AppImage e o builder soltos, outras versões)
            if velho.name not in (BASE_VERSAO, "builder"):
                shutil.rmtree(velho, ignore_errors=True) if velho.is_dir() else velho.unlink(missing_ok=True)
        app = pasta / BASE_ARQUIVO

        def confere() -> bool:
            if not app.is_file() or app.stat().st_size != BASE_BYTES:
                return False
            h = hashlib.sha256()
            with open(app, "rb") as f:
                for bloco in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloco)
            return h.hexdigest() == BASE_SHA256

        falhas = []
        for url in urls_da_base():
            if confere():
                break
            parte = app.with_suffix(".parte")
            try:
                pedido = urllib.request.Request(url, headers={"User-Agent": "deckport-zelda-oot"})
                with urllib.request.urlopen(pedido, timeout=60) as r, open(parte, "wb") as f:
                    lido = 0
                    while True:
                        self._para()
                        bloco = r.read(1 << 20)
                        if not bloco:
                            break
                        f.write(bloco)
                        lido += len(bloco)
                        self._avanca(1, 0.9 * lido / BASE_BYTES)
                parte.replace(app)
            except OSError as e:
                falhas.append(f"{url}: {e}")
                parte.unlink(missing_ok=True)
                continue
            if not confere():
                app.unlink(missing_ok=True)
                falhas.append(f"{url}: soma SHA-256 diferente")
        if not confere():
            raise RuntimeError("não deu para baixar o Longshot " + BASE_VERSAO + " (" + "; ".join(falhas) + ")")
        app.chmod(0o755)
        # extraído: o Python dele (com o zstandard) roda as ferramentas do port, e a montagem roda sem FUSE
        raiz = pasta / "squashfs-root"
        fontes = raiz / "usr" / "share" / "longshot"
        marca = raiz / ".deckport"
        try:
            pronta = marca.read_text().strip() == identidade_base()
        except OSError:
            pronta = False
        if not pronta:   # extraído de novo: as fontes limpas antes do patch
            shutil.rmtree(raiz, ignore_errors=True)
            subprocess.run([str(app), "--appimage-extract"], cwd=pasta, check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            # a saída 1424x800 também no perfil portátil (o Longshot só a aceita no modo dock); sem ele a imagem sai
            # em 2048x1152 e o jogo gasta o dobro de memória de vídeo
            subprocess.run([self._python(raiz), "-I", str(PACOTE / "patches" / "patch_800p.py"), str(fontes)],
                           check=True)
            # o renderizador do port: o builder o compila destas fontes e prepara os shaders com ele. (O carimbo do cache
            # de programas muda com o renderizador e com o modo dos task shaders: com o do Longshot a primeira abertura
            # preparava tudo de novo, 820 de 38809 programas em 6,5 min)
            aplicar_patch(PACOTE / "patches" / BASE_PATCH, fontes)
            marca.write_text(identidade_base())
        self._avanca(1, 1.0)
        return raiz

    def _python(self, hookshot: Path) -> str:
        for p in (hookshot / "usr" / "python" / "bin" / "python3", hookshot / "usr" / "python" / "bin" / "python"):
            if p.exists():
                return str(p)
        raise RuntimeError("o Python do Longshot não foi achado em " + str(hookshot))

    # ---- montar o jogo (o builder do Longshot, sem janela: as linhas @@ dizem a etapa, a fração e o tempo que falta)
    def _montar(self, hookshot: Path, jogo: Path):
        trabalho = self.raiz / "montagem"
        log = self.raiz / "logs" / "montagem.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        if self.jogo.tipo == "nup":
            origem = ["--nup", str(self.jogo.caminho)]
        else:   # uma pasta de outra versão: o romfs dela (por link, no mesmo disco) e o código do jogo que ela guarda
            origem = ["--romfs", str(self.jogo.caminho / "romfs"), "--exefs", str(exefs_da_pasta(self.jogo.caminho))]
        cmd = [str(hookshot / "AppRun"), "--cli", *origem, "--out", str(jogo), "--work",
               str(trabalho), "--language", self.idioma, "--log", str(log)]
        amb = dict(os.environ, HOOKSHOT_NO_UPDATE_CHECK="1", LONGSHOT_NO_UPDATE_CHECK="1",
                   LONGSHOT_BUILDER_HOME=str(BASE_FERRAMENTAS))
        # os mesmos interruptores que o lançador usa e que entram no carimbo do cache de programas (rodar-zelda.sh)
        amb.update(RX_VK_TASK_MESH_FALLBACK="1", RX_VK_FORCE_MESH_FALLBACK="0", RX_VK_MESH_OPT="1",
                   HOS_HANDHELD="1", HOS_OUTPUT_RES="1424x800", HOS_ASPECT="1.6")
        amb.pop("LD_PRELOAD", None)
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=amb,
                                     errors="replace", start_new_session=True)
        # ler os arquivos e traduzir vão até 25% da barra; compilar, de 25% a 100%
        faixa = {"read": (0.0, 0.10), "lift": (0.10, 0.25), "compile": (0.25, 1.0)}
        etapa, ini = "read", time.time()
        resto, ultimas = -1.0, []
        for linha in self.proc.stdout:
            self._para()
            linha = linha.rstrip()
            ultimas = (ultimas + [linha])[-12:]
            if linha.startswith("@@stage "):
                etapa = linha.split()[1]
                a, _ = faixa.get(etapa, (0.0, 0.25))
                self._avanca(2, a, linha.split(" ", 2)[2] if linha.count(" ") >= 2 else "", resto)
            elif linha.startswith("@@eta "):
                try:
                    resto = float(linha.split()[1])
                except ValueError:
                    pass
            elif linha.startswith("@@progress "):
                try:
                    f = float(linha.split()[1])
                except ValueError:
                    continue
                a, b = faixa.get(etapa, (0.25, 1.0))
                self._avanca(2, a + (b - a) * f, restante=resto)
            elif linha.startswith("Downloading the build tools"):   # as ferramentas da montagem, antes de ler o jogo
                m = re.search(r"\((\d+) of (\d+),", linha)
                if m:
                    self._avanca(2, 0.0, f"{m.group(1)}/{m.group(2)}")
            elif etapa == "read" and "MiB written" in linha:   # extração: uns 26 GB
                m = re.search(r"([\d.]+) MiB written", linha)
                if m:
                    self._avanca(2, 0.10 * min(1.0, float(m.group(1)) / 26800))
        if self.proc.wait() != 0:
            self._para()
            raise RuntimeError("a montagem do jogo pelo Longshot falhou (%d): %s" % (self.proc.returncode,
                                                                                   " | ".join(ultimas[-4:])))
        shutil.rmtree(trabalho, ignore_errors=True)
        print("montagem: %.0f min" % ((time.time() - ini) / 60))

    # ---- o renderizador do port: compilado pela montagem, das fontes com o patch; aqui só se confere e marca a pasta
    def _renderizador(self, jogo: Path):
        alvo = jogo / "bin" / "longshot_vk.so"
        try:
            dados = alvo.read_bytes()
        except OSError:
            raise RuntimeError(f"a montagem não deixou o renderizador em {alvo}")
        if b"RX_VK_READBACK_SKIP" not in dados:   # (uma variável que só o renderizador do port lê)
            raise RuntimeError(f"o renderizador em {alvo} não é o do port: o patch não entrou na montagem")
        (jogo / MARCA).write_text(identidade_base() + "\n")

    # ---- os mods, gerados dos arquivos do jogo
    def _ferramenta(self, py: str, nome: str, args: list[str], etapa: int, a: float, b: float, padrao: str = ""):
        self.proc = subprocess.Popen([py, "-I", str(PACOTE / "deck" / "ferramentas" / nome), *args],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                                     start_new_session=True)
        ultimas = []
        for linha in self.proc.stdout:
            self._para()
            ultimas = (ultimas + [linha.rstrip()])[-6:]
            if padrao:
                m = re.search(padrao, linha)
                if m and float(m.group(2)) > 0:
                    self._avanca(etapa, a + (b - a) * float(m.group(1)) / float(m.group(2)))
        if self.proc.wait() != 0:
            self._para()
            raise RuntimeError(f"{nome} falhou ({self.proc.returncode}): " + " | ".join(ultimas[-3:]))
        self._avanca(etapa, b)

    def _texturas(self, py: str, jogo: Path):
        romfs = str(jogo / "romfs")
        nucleos = str(max(2, (os.cpu_count() or 4) - 2))
        for i, (lado, pasta) in enumerate(((512, "mods-tex512"), (1024, "mods-tex1024"))):
            saida = self.raiz / pasta
            marca = saida / ".pronto"
            if marca.exists():
                self._avanca(4, (i + 1) / 2)
                continue
            shutil.rmtree(saida, ignore_errors=True)
            mod = saida / "deckport-texturas" / "romfs"
            mod.mkdir(parents=True)
            self._ferramenta(py, "reduzir_texturas.py",
                             [romfs, "--max", str(lado), "--saida", str(mod), "--jobs", nucleos, "--tabela",
                              str(saida / "tabela-do-mod.zs"), "--progresso"],
                             4, i / 2, (i + 1) / 2, r"@@ (\d+) (\d+)")
            marca.write_text(str(lado))

    def _vegetacao_e_icones(self, py: str, jogo: Path):
        romfs = str(jogo / "romfs")
        total = len(DISTANCIAS) * len(GRAMAS)
        k = 0
        for d, dist in enumerate(DISTANCIAS):
            for g, (dens, folhas) in enumerate(GRAMAS):
                saida = self.raiz / "veg-niveis" / f"d{d}g{g}" / "deckport-vegetacao" / "romfs"
                k += 1
                if dist == 1.0 and dens == 1.0:   # o original: sem mod
                    continue
                shutil.rmtree(saida.parent, ignore_errors=True)
                saida.mkdir(parents=True)
                self._ferramenta(py, "reduzir_vegetacao.py",
                                 [romfs, "--saida", str(saida), "--densidade", str(dens), "--folhas", str(folhas),
                                  "--distancia", str(dist)], 5, 0.7 * (k - 1) / total, 0.7 * k / total)
        # a tabela de tamanhos dos ícones de botão (prompts/ do jogo) junto com a de cada mod de texturas
        da_hookshot = jogo / "prompts" / "rsizetable-hookshot.zs"
        if not da_hookshot.exists() and (jogo / "prompts" / "rsizetable.zs").exists():
            shutil.copy2(jogo / "prompts" / "rsizetable.zs", da_hookshot)
        if da_hookshot.exists():
            for pasta in ("mods-tex512", "mods-tex1024"):
                do_mod = self.raiz / pasta / "tabela-do-mod.zs"
                if do_mod.exists():
                    self._ferramenta(py, "tabela_prompts.py",
                                     [str(do_mod), str(da_hookshot), str(self.raiz / pasta / "prompts-rsizetable.zs")],
                                     5, 0.7, 1.0)
        self._avanca(5, 1.0)

    def run(self):
        try:
            self.raiz.mkdir(parents=True, exist_ok=True)
            (self.raiz / "logs").mkdir(exist_ok=True)
            self._avanca(0, 0.2)
            instalar_app()
            self._avanca(0, 1.0)
            hookshot = self._hookshot()
            py = self._python(hookshot)
            if self.jogo.serve:
                jogo = self.jogo.caminho
            else:
                if self.jogo.tipo == "pasta" and not self.jogo.refazer:
                    raise RuntimeError(f"a pasta foi montada pelo {self.jogo.versao} e não guarda os arquivos do jogo "
                                       f"para montar de novo; use o .nup")
                jogo = self.raiz / "jogo"
                if marca_da_pasta(jogo) == identidade_base():   # já montado numa instalação anterior
                    self._avanca(2, 1.0)
                elif self.jogo.tipo == "pasta" and self.jogo.caminho.resolve() == jogo.resolve():
                    # a pasta de uma instalação anterior (outra base): montada ao lado e trocada no fim
                    novo = self.raiz / "jogo-novo"
                    shutil.rmtree(novo, ignore_errors=True)
                    self._montar(hookshot, novo)
                    trocar_jogo(self.raiz, novo, jogo)
                else:
                    self._montar(hookshot, jogo)
            self._avanca(2, 1.0)
            self._renderizador(jogo)
            self._avanca(3, 1.0)
            self._texturas(py, jogo)
            self._vegetacao_e_icones(py, jogo)
            # saves de quem jogava no Hookshot: o Longshot os procura em ~/.local/share/longshot. Copiados, não movidos
            # (a pasta do Hookshot fica como estava), e só se o Longshot ainda não tem nenhum.
            dados = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
            antigos, novos = dados / "hookshot" / "save", dados / "longshot" / "save"
            if antigos.is_dir() and any(antigos.iterdir()) and not (novos.is_dir() and any(novos.iterdir())):
                shutil.copytree(antigos, novos, dirs_exist_ok=True)
                print(f"saves do Hookshot copiados para {novos}")
            # o idioma do jogo e os caminhos que o lançador lê
            CAMINHOS.parent.mkdir(parents=True, exist_ok=True)
            CAMINHOS.write_text(f'ZELDA_BASE="{self.raiz}"\nZELDA_JOGO="{jogo}"\nZELDA_SCRIPTS="{APPDIR / "deck"}"\n')
            c = ler_config()
            c.update({"versao": versao_do_pacote(),
                      "raiz": str(self.raiz), "jogo": str(jogo), "jogo_de_fora": self.jogo.serve,
                      "base": identidade_base()})
            gravar_config(c)
            self._avanca(6, 0.4)
            self.criar_atalho(self.raiz, APPDIR)
            self._avanca(6, 1.0)
            with self.p._trava:
                self.p.pronto = True
        except Exception as e:  # a tela mostra o erro e o log
            import traceback
            traceback.print_exc()
            with self.p._trava:
                self.p.erro = str(e)
