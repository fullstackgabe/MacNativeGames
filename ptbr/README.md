# Zelda nativo no Mac — PT-BR

Versão do [MacNativeGames](https://github.com/ly05010419/MacNativeGames) (de ly05010419, licença MIT) para jogar
**Tears of the Kingdom** e **Breath of the Wild** com texto em português e vozes originais em inglês, com uma correção de
controle que vale para os dois jogos.

| Jogo | Versão | Português |
|---|---|---|
| Tears of the Kingdom | 1.4.3 | texto completo, legendas nas cutscenes (vozes em inglês) |
| Breath of the Wild | 1.6.0 + DLCs 1 e 2 | texto (vozes em inglês) |

O port em si — o código do jogo rodando direto no Apple Silicon, os serviços do Switch e os gráficos NVN sobre Metal — é
todo do projeto original. A tradução é dos autores dos mods (Triforce Heroes).

Este repositório **não contém nenhum arquivo do jogo, keys nem dos mods**. Você precisa ter os seus.

## O que muda em relação ao original

- **Analógicos e D-pad do Pro Controller via [pro-bridge](https://github.com/fullstackgabe/pro-bridge)**
  (`games/totk/runtime/gamepad.m`). No macOS, o GameController não entrega o analógico esquerdo do Switch Pro Controller
  pelo Bluetooth (ele chega como D-pad). Com o pro-bridge rodando (servidor DSU em `127.0.0.1:26760`), os analógicos e o
  D-pad vêm dele. Sem o pro-bridge, nada muda.
- **`ptbr/montar_texto_totk.py`**, que monta o texto em português do TOTK 1.4.3 (abaixo).

A correção fica no runtime compartilhado (`games/totk/runtime`), que os dois apps usam. O desvio do giroscópio em Pro
Controllers com calibração de fábrica ruim, que era corrigido aqui, agora é corrigido no projeto original
(`games/totk/runtime/motion_fusion.c`, desde 2026-10-28); `TOTK_GYRO_BIAS=0` continua desligando.

O português entra como **mod do jogador** (o projeto original já carrega mods de RomFS), sem mudar o build.

## Tears of the Kingdom (1.4.3)

Você precisa do jogo base 1.0.0 (XCI ou NSP), do update **1.4.3** e do seu `prod.keys`. Faça o build normal:

```sh
python3.14 build_app.py ~/Games/totk.xci -k ~/keys/prod.keys --update ~/Games/totk-1.4.3.nsp
```

Para o texto, você precisa da **Tradução Triforce Heroes 3.1** (Switch), no pacote completo ("Tradução + Dublagem") ou
numa cópia só com as legendas (sem as pastas `romfs/Voice` e `romfs/Sound`). Dela só se usa o texto,
`romfs/Mals/USen.Product.121.sarc.zs`; a dublagem nunca entra e as vozes ficam as originais em inglês.

A tradução foi feita para a 1.2.1, e a 1.4.3 lê outro arquivo de texto (`Product.142`), com algumas falas a mais. Copiar
o arquivo dela não serve. O `montar_texto_totk.py` refaz o texto da 1.4.3 fala por fala com as falas da tradução e
coloca o resultado na pasta de mods da 1.4.3:

```sh
python3.14 ptbr/montar_texto_totk.py --app "/caminho/Tears of the Kingdom.app" \
    --triforce "/caminho/<pasta da tradução>/atmosphere/Contents/0100F2C0115B6000/romfs"
python3.14 games/totk/scripts/make_mod_manifest.py \
    "$HOME/Library/Application Support/MacNativeGames/TOTK/mods/v143" --app "/caminho/Tears of the Kingdom.app"
```

O que o script faz:

- As falas que a tradução não tem ficam em inglês. Se você tiver um texto em português já feito para a 1.4.3 (por
  exemplo o `Mals/USpt.Product.142.sarc.zs` do pacote "Sem Legenda nas Falas Dubladas"), passe com `--base` e essas
  falas ficam com o português dele.
- Sete falas de cutscene que na 1.2.1 eram vazias e na 1.4.3 têm voz ("Sábia do Tempo", "Algum tempo depois...")
  estão traduzidas no próprio script, com os termos da tradução.
- O texto completo é maior que o espaço que o jogo reserva para ele. Por isso o mod leva também a tabela de tamanhos do
  jogo (`ResourceSizeTable.Product.143`), igual à original, só com as duas entradas do texto maiores.
- O mesmo texto vai como `USen` e `USpt`. O dicionário zstd, o texto em inglês e a tabela vêm do próprio app, sem
  precisar de keys nem do arquivo do jogo.

No fim, o script diz quantas falas vieram da tradução e quantas falas com voz ainda ficaram sem legenda (deve ser 0).

O jogo precisa rodar em `en-US` para mostrar esse texto. Para fixar (e manter depois de reiniciar, com um LaunchAgent
que rode o mesmo comando):

```sh
launchctl setenv TOTK_LANG en-US
```

## Breath of the Wild (1.6.0 + DLCs)

Você precisa do jogo base (NSP), do update **1.6.0** (`v786432`), das DLCs que tiver e do seu `prod.keys`:

```sh
python3.14 build_app.py ~/Games/botw.nsp -k ~/keys/prod.keys --update ~/Games/botw-1.6.0.nsp \
    --dlc ~/Games/botw-dlc1.nsp --dlc ~/Games/botw-dlc2.nsp
```

A legenda em português vem do mod **Tradução Triforce Heroes** (só textos). Copie o conteúdo da pasta `romfs/` dele para
a pasta de mods da 1.6.0 e gere o manifesto:

```sh
MODDIR="$HOME/Library/Application Support/MacNativeGames/BotW/mods/botw160"
mkdir -p "$MODDIR" && cp -R "/caminho/Tradução Triforce Heroes/romfs/." "$MODDIR/"
python3 games/totk/scripts/make_mod_manifest.py "$MODDIR" --app "/caminho/Breath of the Wild.app"
```

O mod traz a própria `ResourceSizeTable` (o texto em português é maior que o original). O jogo precisa rodar em
`en-US`: `defaults write org.macnativegames.botw AppleLanguages -array en-US`.

## Atualizar o port

Traga as mudanças do projeto original e troque só o runtime do app, sem o arquivo do jogo nem as keys:

```sh
git fetch upstream && git merge upstream/main
python3.14 update_runtime.py "/caminho/Tears of the Kingdom.app"
```

Os saves e a pasta de mods ficam fora do app e não mudam. Quando a atualização muda a tradução dos shaders, a primeira
abertura refaz o cache: o jogo fica na tela de carregamento por 15 a 25 minutos (o log mostra o progresso, "预热进度").
Não está travado, e isso só acontece uma vez.

## Saves

O TOTK guarda em `~/Library/Application Support/MacNativeGames/TOTK/profile` e o BOTW em `.../MacNativeGames/BotW/profile`,
fora do app. Cada usuário (painel de configurações, tecla 1) tem o seu save em `profile/save/<id>`; um perfil de antes
dos usuários vira o usuário "Local", com o mesmo save. Na primeira vez que uma versão nova abre, o app faz um backup
completo (`profile-before-1.4.3`). Um save de versão mais nova não abre numa versão mais antiga.

## Limitações

- TOTK: a tela de título e algumas texturas de menu ficam em inglês (a tradução traz essas texturas só para a 1.2.1).
