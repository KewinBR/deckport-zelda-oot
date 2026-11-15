"""Textos do instalador em português (Brasil) e inglês. T("chave") devolve no idioma atual."""
import locale
import os

TEXTOS = {
    "passo1": ("JOGO", "GAME"),
    "passo2": ("LOCAL", "LOCATION"),
    "passo3": ("INSTALAR", "INSTALL"),
    "passo4": ("PRONTO", "DONE"),
    "selecionar": ("Selecionar", "Select"),
    "sair": ("Sair", "Quit"),
    "marcar": ("Marcar", "Check"),
    "voltar": ("Voltar", "Back"),
    "cancelar": ("Cancelar", "Cancel"),
    "continuar": ("Continuar", "Continue"),
    "instalar": ("Instalar", "Install"),
    "outro_idioma": ("English", "Português"),
    "inicio_texto": ("Instalador do Deckport para o Steam Deck. Versão de teste.\nVocê precisa da sua própria cópia "
                     "do jogo de Switch 2, num arquivo .nup. Nada do jogo é baixado.",
                     "Deckport installer for the Steam Deck. Test version.\nYou need your own copy of the Switch 2 "
                     "game, as a .nup file. Nothing from the game is downloaded."),
    "creditos_por": ("DECKPORT POR", "DECKPORT BY"),
    "creditos_base": ("feito sobre o Longshot (MagicBeanDev) e o Hookshot (NotRexed), GPL-3",
                      "built on Longshot (MagicBeanDev) and Hookshot (NotRexed), GPL-3"),
    "jogo_titulo": ("Onde está o jogo?", "Where is the game?"),
    "jogo_achei": ("Achei isto no Deck e no cartão SD. Marque o que usar.",
                   "I found these on the Deck and the SD card. Check the one to use."),
    "jogo_nada": ("Não achei o arquivo .nup do jogo. Procure em outra pasta, ou aponte uma pasta já montada pelo "
                  "Hookshot ou pelo Longshot.",
                  "I could not find the game's .nup file. Look in another folder, or point to a folder already built "
                  "by Hookshot or Longshot."),
    "tipo_nup": ("Arquivo do jogo", "Game file"),
    "tipo_pasta": ("Pasta montada pelo", "Folder built by"),
    "pasta_versao_errada": ("sem os arquivos do jogo: use o .nup", "no game files kept: use the .nup"),
    "pasta_refazer": ("refeita com o Longshot", "rebuilt with Longshot"),
    "procurar": ("Procurar em outra pasta", "Look in another folder"),
    "procurar_sub": ("Pen drive, Downloads...", "USB drive, Downloads..."),
    "ja_montado": ("Já tenho a pasta montada", "I have a built folder"),
    "ja_montado_sub": ("Feita pelo Hookshot ou pelo Longshot", "Made by Hookshot or Longshot"),
    "local_titulo": ("Onde instalar?", "Where to install?"),
    "local_texto": ("O jogo montado ocupa uns 35 GB, e a montagem pede 45 GB livres.",
                    "The built game takes about 35 GB, and building it needs 45 GB free."),
    "local_texto_refazer": ("A pasta é montada de novo com o Longshot. No mesmo disco dela o romfs não é copiado, "
                            "e bastam uns 20 GB livres.",
                            "The folder is built again with Longshot. On its own drive the romfs is not copied, and "
                            "about 20 GB free is enough."),
    "local_texto_pasta": ("A pasta do jogo fica onde está. Aqui vão só os arquivos do port, uns 6 GB.",
                          "The game folder stays where it is. Only the port's files go here, about 6 GB."),
    "ssd": ("Armazenamento interno (SSD)", "Internal storage (SSD)"),
    "ssd_sub": ("Mais rápido para carregar", "Faster loading"),
    "sd": ("Cartão microSD", "microSD card"),
    "sd_sub": ("Libera o SSD", "Keeps the SSD free"),
    "livres": ("livres", "free"),
    "sem_espaco": ("Sem espaço: precisa de {} livres", "Not enough space: needs {} free"),
    "recomendado": ("RECOMENDADO", "RECOMMENDED"),
    "instalando_titulo": ("Instalando", "Installing"),
    "etapa_port": ("Preparando o Deckport", "Preparing Deckport"),
    "etapa_hookshot": ("Baixando o Longshot", "Downloading Longshot"),
    "etapa_montar": ("Montando o jogo (a parte demorada)", "Building the game (the long part)"),
    "etapa_renderizador": ("Colocando o renderizador do port", "Installing the port's renderer"),
    "etapa_texturas": ("Gerando as texturas do Deck", "Generating the Deck textures"),
    "etapa_vegetacao": ("Gerando a vegetação e os ícones", "Generating vegetation and icons"),
    "etapa_atalho": ("Criando o atalho na Steam", "Creating the Steam shortcut"),
    "total": ("Total", "Total"),
    "restam": ("cerca de {} min restantes", "about {} min left"),
    "restam_etapa": ("cerca de {} min nesta etapa", "about {} min in this step"),
    "tomada": ("deixe o Deck na tomada", "keep the Deck plugged in"),
    "pronto_titulo": ("Pronto!", "All set!"),
    "pronto_texto": ("Zelda: Ocarina of Time está na sua biblioteca da Steam, com capa e ícone.\nVolte ao Modo de Jogo "
                     "e abra por lá. A primeira abertura prepara os shaders e demora mais de 30 minutos, uma vez só.",
                     "Zelda: Ocarina of Time is in your Steam library, with cover art and icon.\nGo back to Game Mode "
                     "and launch it there. The first launch prepares the shaders and takes over 30 minutes, only once."),
    "pronto_menu": ("Menu do port durante o jogo: View + Menu (os dois botões pequenos ao lado da tela).",
                    "Port menu while playing: View + Menu (the two small buttons beside the screen)."),
    "modo_jogo": ("Voltar ao Modo de Jogo", "Back to Game Mode"),
    "erro_titulo": ("Algo deu errado", "Something went wrong"),
    "erro_texto": ("A instalação parou. Nada do seu jogo foi apagado, e dá para tentar de novo: o que já foi feito é "
                   "aproveitado. Se repetir, abra uma issue no GitHub com o arquivo "
                   "~/.config/zelda-oot-deck/instalador.log.",
                   "The installation stopped. Nothing from your game was deleted, and you can try again: what is done "
                   "is kept. If it happens again, open an issue on GitHub with the file "
                   "~/.config/zelda-oot-deck/instalador.log."),
    "tentar_de_novo": ("Tentar de novo", "Try again"),
}


class _T:
    lang = "pt"

    def __call__(self, chave: str) -> str:
        pt, en = TEXTOS.get(chave, (chave, chave))
        return pt if self.lang == "pt" else en


T = _T()


def idioma_inicial() -> str:
    """Português se o sistema estiver em português, senão inglês."""
    for v in (os.environ.get("LANG", ""), os.environ.get("LC_ALL", ""), (locale.getlocale()[0] or "")):
        if v.lower().startswith("pt"):
            return "pt"
    return "en"
