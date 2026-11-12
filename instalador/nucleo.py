"""Parte sem tela do instalador do Deckport Zelda: Ocarina of Time.

Acha a cópia do jogo do próprio jogador (um arquivo .nup, ou uma pasta já montada pelo Hookshot v2.1.0), baixa o
Hookshot oficial, monta o jogo com ele, troca o renderizador pelo do port, gera os mods de textura e de vegetação a
partir dos arquivos do jogo, instala o lançador e cria o atalho na Steam. Nada do jogo sai do Deck nem é baixado.

Layout instalado (DESTINO = a pasta pessoal no SSD ou a raiz do cartão SD):
    DESTINO/zelda-oot-deck/jogo/          a pasta do jogo montada pelo Hookshot
    DESTINO/zelda-oot-deck/mods-tex512/   texturas reduzidas (e mods-tex1024/)
    DESTINO/zelda-oot-deck/veg-niveis/    os níveis de vegetação do menu do port
    DESTINO/zelda-oot-deck/logs/          um log por sessão de jogo
    ~/.local/share/zelda-oot-deck/        o port: lançador, renderizador, ferramentas, Hookshot, instalador
    ~/.config/zelda-oot-deck/             config.json e caminhos.env (lido pelo lançador)
"""
from __future__ import annotations

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

# O Hookshot em que o renderizador do port foi feito. Outra versão não serve: o renderizador é trocado inteiro.
HOOKSHOT_VERSAO = "v2.1.0"
HOOKSHOT_ARQUIVO = f"Hookshot-{HOOKSHOT_VERSAO}-x86_64.AppImage"
HOOKSHOT_URL = f"https://github.com/NotRexed/Hookshot/releases/download/{HOOKSHOT_VERSAO}/{HOOKSHOT_ARQUIVO}"
HOOKSHOT_SHA256 = "c0b2e958ae00dc560072154f890b9be422724abd9bb522d6afd9922788b86e02"
HOOKSHOT_BYTES = 242149880

NUP_MINIMO = 20 * 1024 ** 3      # o .nup do jogo tem 25,6 GB
ESPACO_MONTAR = 45 * 1024 ** 3   # jogo montado (~35 GB com os caches de shader) e a folga da montagem
ESPACO_SO_PORT = 6 * 1024 ** 3   # só os mods, sobre uma pasta já montada

# Os níveis do menu do port (Gráficos > Mundo): distância da vegetação e densidade da grama.
DISTANCIAS = [0.4, 0.5, 0.6, 0.8, 1.0]
GRAMAS = [(0.5, 0.67), (0.75, 0.84), (1.0, 1.0)]   # (densidade, folhas por tufo)


@dataclass
class Jogo:
    caminho: Path
    tamanho: int
    tipo: str            # "nup" ou "pasta"
    versao: str = ""     # (pasta) a versão do Hookshot que a montou
    marcado: bool = True

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
    """A versão do Hookshot que montou a pasta (hookshot_version.txt: version=v2.1.0), ou vazio se não é uma."""
    try:
        if not (pasta / "image.bin").is_file() or not (pasta / "romfs").is_dir():
            return ""
        for linha in (pasta / "hookshot_version.txt").read_text().splitlines():
            if linha.startswith("version="):
                return linha.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def procurar_jogos(lugares: list[Path] | None = None, profundidade: int = 4) -> list[Jogo]:
    """Os .nup grandes e as pastas já montadas pelo Hookshot, nas pastas de costume (sem entrar em pastas ocultas)."""
    achados: dict[Path, Jogo] = {}
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
        if item.name in ("hookshot", "logs", ".git"):
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

    def _para(self):
        if self.cancelado:
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
            raise RuntimeError("cancelado")

    def cancelar(self):
        self.cancelado = True
        if self.proc and self.proc.poll() is None:
            self.proc.kill()

    # ---- o Hookshot oficial
    def _hookshot(self) -> Path:
        pasta = APPDIR / "hookshot"
        pasta.mkdir(parents=True, exist_ok=True)
        app = pasta / HOOKSHOT_ARQUIVO

        def confere() -> bool:
            if not app.is_file() or app.stat().st_size != HOOKSHOT_BYTES:
                return False
            h = hashlib.sha256()
            with open(app, "rb") as f:
                for bloco in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloco)
            return h.hexdigest() == HOOKSHOT_SHA256

        if not confere():
            parte = app.with_suffix(".parte")
            with urllib.request.urlopen(HOOKSHOT_URL, timeout=60) as r, open(parte, "wb") as f:
                lido = 0
                while True:
                    self._para()
                    bloco = r.read(1 << 20)
                    if not bloco:
                        break
                    f.write(bloco)
                    lido += len(bloco)
                    self._avanca(1, 0.9 * lido / HOOKSHOT_BYTES)
            parte.replace(app)
            if not confere():
                app.unlink(missing_ok=True)
                raise RuntimeError("o Hookshot baixado não confere com o original (soma SHA-256 diferente)")
        app.chmod(0o755)
        # extraído: o Python dele (com o zstandard) roda as ferramentas do port, e a montagem roda sem FUSE
        raiz = pasta / "squashfs-root"
        if not (raiz / "AppRun").exists():
            shutil.rmtree(raiz, ignore_errors=True)
            subprocess.run([str(app), "--appimage-extract"], cwd=pasta, check=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        self._avanca(1, 1.0)
        return raiz

    def _python(self, hookshot: Path) -> str:
        for p in (hookshot / "usr" / "python" / "bin" / "python3", hookshot / "usr" / "python" / "bin" / "python"):
            if p.exists():
                return str(p)
        raise RuntimeError("o Python do Hookshot não foi achado em " + str(hookshot))

    # ---- montar o jogo (o builder do Hookshot, sem janela: as linhas @@ dizem a etapa, a fração e o tempo que falta)
    def _montar(self, hookshot: Path, jogo: Path):
        trabalho = self.raiz / "montagem"
        log = self.raiz / "logs" / "montagem.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        cmd = [str(hookshot / "AppRun"), "--cli", "--nup", str(self.jogo.caminho), "--out", str(jogo), "--work",
               str(trabalho), "--language", self.idioma, "--log", str(log)]
        amb = dict(os.environ, HOOKSHOT_NO_UPDATE_CHECK="1")
        amb.pop("LD_PRELOAD", None)
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=amb,
                                     errors="replace")
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
            elif etapa == "read" and "MiB written" in linha:   # extração: uns 26 GB
                m = re.search(r"([\d.]+) MiB written", linha)
                if m:
                    self._avanca(2, 0.10 * min(1.0, float(m.group(1)) / 26800))
        if self.proc.wait() != 0:
            raise RuntimeError("a montagem do jogo pelo Hookshot falhou (%d): %s" % (self.proc.returncode,
                                                                                   " | ".join(ultimas[-4:])))
        shutil.rmtree(trabalho, ignore_errors=True)
        print("montagem: %.0f min" % ((time.time() - ini) / 60))

    # ---- o renderizador do port no lugar do do Hookshot
    def _renderizador(self, jogo: Path):
        nosso = APPDIR / "renderizador" / "hookshot_vk.so"
        if not nosso.is_file():
            raise RuntimeError("falta o renderizador do port no pacote (renderizador/hookshot_vk.so)")
        alvo = jogo / "bin" / "hookshot_vk.so"
        guardado = jogo / "bin" / "hookshot_vk.so.hookshot"
        if alvo.exists() and not guardado.exists():
            shutil.copy2(alvo, guardado)   # o original fica ao lado, para desinstalar
        novo = alvo.with_suffix(".so.novo")
        shutil.copy2(nosso, novo)
        novo.replace(alvo)

    # ---- os mods, gerados dos arquivos do jogo
    def _ferramenta(self, py: str, nome: str, args: list[str], etapa: int, a: float, b: float, padrao: str = ""):
        self.proc = subprocess.Popen([py, "-I", str(APPDIR / "deck" / "ferramentas" / nome), *args],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        ultimas = []
        for linha in self.proc.stdout:
            self._para()
            ultimas = (ultimas + [linha.rstrip()])[-6:]
            if padrao:
                m = re.search(padrao, linha)
                if m and float(m.group(2)) > 0:
                    self._avanca(etapa, a + (b - a) * float(m.group(1)) / float(m.group(2)))
        if self.proc.wait() != 0:
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
            if self.jogo.tipo == "pasta":
                jogo = self.jogo.caminho
                if not self.jogo.versao.startswith(HOOKSHOT_VERSAO):
                    raise RuntimeError(f"a pasta foi montada pelo Hookshot {self.jogo.versao}; este port precisa da "
                                       f"{HOOKSHOT_VERSAO}")
            else:
                jogo = self.raiz / "jogo"
                if versao_da_pasta(jogo).startswith(HOOKSHOT_VERSAO):   # já montado numa instalação anterior
                    self._avanca(2, 1.0)
                else:
                    self._montar(hookshot, jogo)
            self._avanca(2, 1.0)
            self._renderizador(jogo)
            self._avanca(3, 1.0)
            self._texturas(py, jogo)
            self._vegetacao_e_icones(py, jogo)
            # o idioma do jogo e os caminhos que o lançador lê
            CAMINHOS.parent.mkdir(parents=True, exist_ok=True)
            CAMINHOS.write_text(f'ZELDA_BASE="{self.raiz}"\nZELDA_JOGO="{jogo}"\nZELDA_SCRIPTS="{APPDIR / "deck"}"\n')
            c = ler_config()
            c.update({"versao": (PACOTE / "VERSAO").read_text().strip() if (PACOTE / "VERSAO").exists() else "",
                      "raiz": str(self.raiz), "jogo": str(jogo), "jogo_de_fora": self.jogo.tipo == "pasta",
                      "hookshot": HOOKSHOT_VERSAO})
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
