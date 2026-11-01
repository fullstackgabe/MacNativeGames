#!/usr/bin/env python3.14
"""Monta o texto em português do Tears of the Kingdom 1.4.3 a partir da tradução Triforce Heroes (feita para a 1.2.1).

    python3.14 ptbr/montar_texto_totk.py --app "Tears of the Kingdom.app" \
        --triforce "/caminho/Traducao + Dublagem -Triforce Heroes(Switch)/.../romfs" [--base USpt.Product.142.sarc.zs]

O texto do jogo (Mals/USen.Product.<n>.sarc.zs) é um SARC de arquivos MSBT, um por conversa, e cada fala tem um rótulo.
A tradução foi feita para a 1.2.1 (Product.121), e a 1.4.3 lê o Product.142, que tem algumas falas a mais. Aqui o
texto da 1.4.3 é refeito fala por fala: cada rótulo que a tradução tem recebe a fala dela; o resto fica com a fala da
base (--base, um texto em português já feito para a 1.4.3, como o USpt.Product.142 do "Sem Legenda nas Falas
Dubladas"; sem ele, o inglês original), menos 6 falas de cutscene que só a 1.4.3 tem, traduzidas abaixo (MANUAL).
Falas que a base deixou em branco (um espaço sem quebra, como faz o "Sem Legenda") e que a tradução não tem são contadas
no fim.

O texto inteiro passa do tamanho que o jogo reserva para ele na tabela de tamanhos (ResourceSizeTable.Product.143):
a tabela vai junto no mod, igual à do jogo, só com as entradas de Mals/USen e Mals/USpt.Product.142 maiores
(docs/mods.md). O mesmo texto vai como USen e USpt: o jogo roda em en-US e mostra português com as vozes em inglês.

O dicionário zstd, o texto em inglês e a tabela vêm do RomFS do app (sem keys nem arquivo do jogo). Os arquivos são
escritos na pasta do mod (--mod, por padrão a pasta de mods da 1.4.3); depois rode make_mod_manifest.py.
"""
import argparse
from compression import zstd
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'games/totk/scripts'))
from make_mod_manifest import app_image_dir, read_index

TEXT = 'Mals/USen.Product.142.sarc.zs'
TEXTS = ('Mals/USen.Product.142.sarc', 'Mals/USpt.Product.142.sarc')   # names in the size table: without .zs
TABLE = 'System/Resource/ResourceSizeTable.Product.143.Nin_NX_NVN.rsizetable.zs'
BLANK = '\xa0'.encode('utf-16le') + b'\0\0'   # a line the "Sem Legenda" text leaves empty on screen
MANUAL = {   # cutscene lines that are empty in 1.2.1 and spoken in 1.4.3, with the translation's words (Sábia do Tempo, Gerudo)
    'Dm_GO_0021_Text_030_c': 'A Sábia do Tempo—uma dos seis sábios.',
    'Dm_ZN_0033_Text_017_c': 'Rauru!',
    'Dm_ZO_0032_Text_014_c': 'Era outra dos seis sábios—a Sábia do Tempo.',
    'Dm_RT_0022_Text_014_d': 'Algum tempo depois...',
    'Dm_GE_0025_Text_015_c': 'Outra dos seis sábios—a Sábia do Tempo.',
    'Dm_GE_0025_Text_015_d': 'Algum tempo depois...',
    'Dm_GE_0025_Text_015_e': 'Outra dos seis sábios—a Sábia do Tempo—veio\nme visitar e colocou as Gerudo em nosso caminho destinado.',
}


def romfs_files(app, names):
    """name -> bytes of the given RomFS files of the app (as make_mod_manifest.py finds its RomFS)."""
    romfs = app/'Contents/Resources/totk/extracted/v143/romfs'
    image = romfs/'romfs.bin' if (romfs/'romfs.bin').exists() else app_image_dir(app, 'v143')/'romfs.bin'
    index = read_index(romfs/'runtime-index.bin')
    with image.open('rb') as f:
        out = {}
        for name in names:
            offset, size = index[name]
            f.seek(offset); out[name] = f.read(size)
    return out


def sarc_read(data):
    """[(name, bytes)] of a SARC, in its order, and the header and node and name tables to write it again."""
    assert data[:4] == b'SARC' and data[6:8] == b'\xff\xfe'
    start = struct.unpack_from('<I', data, 0x0c)[0]
    count = struct.unpack_from('<H', data, 0x1a)[0]
    names = 0x20 + count*16 + 8
    members = []
    for i in range(count):
        _, attribute, lo, hi = struct.unpack_from('<4I', data, 0x20 + i*16)
        offset = names + (attribute & 0xffffff)*4
        members.append((data[offset:data.index(0, offset)].decode(), data[start + lo:start + hi]))
    return data[:start], members


def sarc_write(head, members):
    out, blob = bytearray(head), bytearray()
    for i, (_, data) in enumerate(members):
        blob += bytes(-len(blob) % 0x80)   # each member 0x80-aligned, as the game's own archives
        struct.pack_into('<II', out, 0x20 + i*16 + 8, len(blob), len(blob) + len(data))
        blob += data
    out += blob
    struct.pack_into('<I', out, 0x08, len(out))
    return bytes(out)


def msbt_read(data):
    """The sections of an MSBT, its label -> index and its strings (raw UTF-16, each with its terminator)."""
    assert data[:8] == b'MsgStdBn'
    sections, offset = [], 0x20
    for _ in range(struct.unpack_from('<H', data, 0x0e)[0]):
        size = struct.unpack_from('<I', data, offset + 4)[0]
        sections.append((data[offset:offset + 16], data[offset + 16:offset + 16 + size]))
        offset = (offset + 16 + size + 15) & ~15
    found = dict((h[:4], body) for h, body in sections)
    labels, table = {}, found[b'LBL1']
    for i in range(struct.unpack_from('<I', table, 0)[0]):
        count, at = struct.unpack_from('<II', table, 4 + i*8)
        for _ in range(count):
            length = table[at]
            labels[table[at + 1:at + 1 + length].decode()] = struct.unpack_from('<I', table, at + 1 + length)[0]
            at += 5 + length
    text = found[b'TXT2']
    count = struct.unpack_from('<I', text, 0)[0]
    starts = list(struct.unpack_from(f'<{count}I', text, 4)) + [len(text)]
    return sections, labels, [text[starts[i]:starts[i + 1]] for i in range(count)]


def msbt_write(data, sections, strings):
    head = 4 + 4*len(strings)
    starts = [head + sum(len(s) for s in strings[:i]) for i in range(len(strings))]
    text = struct.pack(f'<I{len(strings)}I', len(strings), *starts) + b''.join(strings)
    out = bytearray(data[:0x20])
    for h, body in sections:
        if h[:4] == b'TXT2':
            h, body = h[:4] + struct.pack('<I', len(text)) + h[8:], text
        out += h + body
        out += b'\xab'*(-len(out) % 16)
    struct.pack_into('<I', out, 0x12, len(out))
    return bytes(out)


def lines(members, name):
    """label -> raw string of one MSBT of an archive's members (empty when the archive lacks it)."""
    if name not in members:
        return {}
    _, labels, strings = msbt_read(members[name])
    return {label: strings[i] for label, i in labels.items()}


def merge(base, triforce, english):
    """The base text with the translation's line for every label the translation has a line for (a label it leaves
    empty may be spoken in 1.4.3: it keeps the base's line, or MANUAL's). Returns (text, counts)."""
    head, members = sarc_read(base)
    theirs, original = dict(sarc_read(triforce)[1]), dict(sarc_read(english)[1])
    counts = dict(triforce=0, manual=0, blank=0)
    out = []
    for name, data in members:
        if name.endswith('.msbt'):
            sections, labels, strings = msbt_read(data)
            other, spoken = lines(theirs, name), lines(original, name)
            for label, i in labels.items():
                line = other.get(label, BLANK)
                if label in MANUAL:
                    strings[i] = MANUAL[label].encode('utf-16le') + b'\0\0'; counts['manual'] += 1
                elif line not in (BLANK, b'\0\0'):
                    counts['triforce'] += strings[i] != line
                    strings[i] = line
                elif strings[i] in (BLANK, b'\0\0') and spoken.get(label, b'\0\0') != b'\0\0':
                    counts['blank'] += 1   # spoken in the game, empty here: no subtitle
            data = msbt_write(data, sections, strings)
        out.append((name, data))
    return sarc_write(head, out), counts


def table_at(table, name):
    """Where the size of a name is in the size table (its CRC32 records; the names of these files are not in the
    table's string records)."""
    assert table[:6] == b'RESTBL'
    crc, crcs = zlib.crc32(name.encode()), struct.unpack_from('<I', table, 14)[0]
    return next(22 + i*8 + 4 for i in range(crcs) if struct.unpack_from('<I', table, 22 + i*8)[0] == crc)


def table_entry(table, name):
    return struct.unpack_from('<I', table, table_at(table, name))[0]


def grow_table(table, sizes):
    """The size table with the entry of each name raised to at least the given size (values only: the order stays)."""
    out = bytearray(table)
    for name, size in sizes.items():
        struct.pack_into('<I', out, table_at(table, name), max(table_entry(table, name), size))
    return bytes(out)


def compress(data, dictionary=None):
    # In one call, so the frame declares its size (the game's decompressor needs it, docs/mods.md); no checksum, as the
    # game's own files.
    return zstd.compress(data, zstd_dict=dictionary, options={zstd.CompressionParameter.compression_level: 19,
                                                              zstd.CompressionParameter.checksum_flag: 0})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--app', type=Path, required=True, help='o Tears of the Kingdom.app (1.4.3)')
    parser.add_argument('--triforce', type=Path, required=True,
                        help='a pasta romfs da tradução Triforce Heroes, ou o arquivo Mals/USen.Product.121.sarc.zs dela')
    parser.add_argument('--base', type=Path, help='um texto em português da 1.4.3 (Mals/*.Product.142.sarc.zs) para as falas '
                        'que a tradução não tem; sem ele, essas falas ficam em inglês')
    parser.add_argument('--mod', type=Path, default=Path.home()/'Library/Application Support/MacNativeGames/TOTK/mods/v143',
                        help='a pasta do mod (padrão: %(default)s)')
    args = parser.parse_args()
    source = args.triforce/'Mals/USen.Product.121.sarc.zs' if args.triforce.is_dir() else args.triforce
    game = romfs_files(args.app, ['Pack/ZsDic.pack.zs', TEXT, TABLE])
    dictionary = zstd.ZstdDict(dict(sarc_read(zstd.decompress(game['Pack/ZsDic.pack.zs']))[1])['zs.zsdic'])
    english = zstd.decompress(game[TEXT], zstd_dict=dictionary)
    base = zstd.decompress(args.base.read_bytes(), zstd_dict=dictionary) if args.base else english
    text, counts = merge(base, zstd.decompress(source.read_bytes(), zstd_dict=dictionary), english)
    table = zstd.decompress(game[TABLE])
    # The game's entry is the text's size plus a margin of its own; the new entry keeps that margin, and 4 KB more.
    size = len(text) + (table_entry(table, TEXTS[0]) - len(english)) + 0x1000
    packed = compress(text, dictionary)
    for name in TEXTS:
        (args.mod/'Mals').mkdir(parents=True, exist_ok=True)
        (args.mod/(name + '.zs')).write_bytes(packed)
    (args.mod/TABLE).parent.mkdir(parents=True, exist_ok=True)
    (args.mod/TABLE).write_bytes(compress(grow_table(table, {name: size for name in TEXTS})))
    print(f'{counts["triforce"]} falas da Triforce Heroes, {counts["manual"]} traduzidas aqui, '
          f'{counts["blank"]} ainda em branco; texto {len(text):,} bytes (o do jogo: {len(english):,}), '
          f'tabela de tamanhos com {size:,} para o texto')
    print(f'escritos em {args.mod}: {", ".join(n + ".zs" for n in TEXTS)}, {TABLE}')
    print(f'agora: python3.14 games/totk/scripts/make_mod_manifest.py "{args.mod}" --app "{args.app}"')


if __name__ == '__main__':
    main()
