# 侠盗猎车手1 美版 PS1 简体中文补丁

美版 PlayStation 光盘的简体中文补丁。中文写在英语槽里，游戏语言保持英语才会显示。

## 玩家指南

仓库里的 `build/Grand Theft Auto (USA) (Track 01).bin` 就是打好的数据轨。音乐不在仓库里，继续用你自己的美版音轨。

1. 找到你的美版目录，里面要有 `Grand Theft Auto (USA).cue`，以及 `Grand Theft Auto (USA) (Track 01).bin` 到 `(Track 11).bin`。
2. 把原来的 `Grand Theft Auto (USA) (Track 01).bin` 改名备份，例如加上 `.bak`。
3. 把仓库里的 `build/Grand Theft Auto (USA) (Track 01).bin` 复制到这个目录，文件名保持 `Grand Theft Auto (USA) (Track 01).bin`。
4. 用模拟器打开原来的 `Grand Theft Auto (USA).cue`。语言保持英语。

`build/` 里的 cue、`SLUS_001.06`、`MISSION.VSR` 不用拷。音轨 02–11 不要换。想还原游戏时，把备份的 Track 01 拷回去。

进游戏后，任务对白、传呼机、菜单和局内提示是简体中文。标题画面、制作人员名单和音乐仍是英文。有两句任务对白会显示「待校」。这次还没有在模拟器里实际开机。

## 汉化进度

### 已经汉化

| 内容 | 规模 | 放在 |
| --- | --- | --- |
| 任务对白和传呼机 | 1310 条 | `text/zh_cn.tsv` |
| 局内提示、车名、地名、结算 | 395 条 | `text/zh_ui.tsv` 的 bin 0 |
| 前端菜单、存档、暂停 | 133 条 | `text/zh_ui.tsv` 的 bin 6 |
| 16×16 汉字点阵 | 1677 字 | `font/glyphs.bin` |
| 可直接替换的数据轨 | 26437 扇区 | `build/Grand Theft Auto (USA) (Track 01).bin` |

字符串里出现 U+0101 及以上的字符时，整句改用 16 像素宽字，数字和标点也算在内。纯英文的句子仍用原来的 8×8 字体。

### 还没有汉化

| 内容 | 原因 |
| --- | --- |
| 菜单贴图 | `FRONTEND.VSR` 里的标题和画面是画上去的 |
| 制作人员名单 | 正文在光盘的 `CREDITS.STR`，职位名称在可执行文件里。菜单上的「查看制作人员」已经是中文 |
| CD 音轨 02–11 | 原版音乐，没有字幕 |
| 法语、德语、意大利语、日语槽 | 和英语槽并列放在同一份 `MISSION.VSR` 里。美版只读英语槽 |
| 西班牙语槽 | 这一档里仍是英文，只是用了自己的压缩表 |
| 任务 id 2197、2600 | 压缩数据解出来是乱码，游戏里显示「待校」 |

按钮提示里的 `~ | { } < >` 在原字体里是图标。一句里只要有汉字，这些符号会画成普通字符。

## 开发者指南

### 打包

`extract/` 随仓库走，里面是尚未打补丁的原版文件。把美版原盘放进 `Grand Theft Auto (USA)/`，文件名不要改。Python 3.9 和 Pillow 也要有。字库用仓库里的 `font/NotoSansCJKsc-Regular-subset.otf`。

| 放在这里 | 是什么 |
| --- | --- |
| `Grand Theft Auto (USA)/Grand Theft Auto (USA) (Track 01).bin` | 美版数据轨，约 59MB。`repack_track.py` 以它为底稿 |
| `Grand Theft Auto (USA)/Grand Theft Auto (USA) (Track 02).bin` … `(Track 11).bin` | 原版 CD 音轨。打包脚本不读它们，生成的 cue 用相对路径指回这个目录 |
| `extract/SLUS_001.06` | 原版可执行文件，1181696 字节。已经在仓库里，不要改 |
| `extract/MISSION.VSR` | 原版文本包，1058556 字节。已经在仓库里，不要改 |

`SLUS_001.06` 和 `MISSION.VSR` 若丢了，可以从 Track 01 再抽。每个扇区 2352 字节，用户数据从偏移 24 开始，长度 2048。`SLUS_001.06` 在扇区 24，`MISSION.VSR` 在扇区 2291。

```bash
python3 tools/build_font.py
python3 tools/repack_mission.py
python3 tools/patch_exe.py
python3 tools/repack_track.py
```

`repack_mission.py` 同时读 `text/zh_cn.tsv` 和 `text/zh_ui.tsv`，写进同一个英语槽。它会先用英语原文做一次往返，再套中文。任一字符串解不回来，脚本会直接退出，不会写出半成品。

只改已有汉字的译文时，从 `repack_mission.py` 开始。译文里出现字库没有的字，先跑 `build_font.py`，再跑 `patch_exe.py`。只改显存坐标时，跑 `patch_exe.py` 和 `repack_track.py`。

打完后按「玩家指南」换上新的 Track 01。`build/Grand Theft Auto (zh).cue` 只在原盘放在仓库旁的 `Grand Theft Auto (USA)/` 时才能直接开，音轨路径写的是 `../Grand Theft Auto (USA)/`。

### 改译文

1. 任务句子只改 `text/zh_cn.tsv` 里对应 id 的 `zh` 列。界面句子改 `text/zh_ui.tsv`，用 `bin` 和 `id` 一起找。两档界面编号都从 0 起。
2. 不要改分批底稿，也不要重跑 `export_strings.py`，它会把 `zh_todo.tsv` 的译文列清掉。
3. 按上一节重打包。同一条任务 id 在几个城市槽里会一起换掉。

沿用这些约定：

- 口语，保留粗口的力度。对玩家用「你」。酒店礼貌台词可以用「您」。
- `ps1_decoded.tsv` 里标成和 PC 相同、只是存盘时被截断的句子，按 PC 的完整句来译。
- 标成用词不同的，按 PS1 的词。例如 guys 不是 dealers，pickup 不是 van，Vice Squad 不是 Drug Squad。
- 货币用「块」。破坏提示是「限时 N 秒，砸出 X 块的破坏！」，金额到整万时用「万」。
- 领奖是「去……领奖！还剩 N 秒！」。
- id 2502 必须是 18 个半角句点。id 3502 必须是 9 个半角句点。
- 一条中文的 UTF-8 加结尾 NUL，不要超过游戏里已经出现过的最长英语句子（198 字节）。现在最长的中文是 180 字节。
- 界面字符串里的 `%s`、`%d`、`%01d` 个数和顺序要跟英文列一样。`#` 和 `@` 是换行，个数也不能变。bin 6 的 131 和 132 保持空白。
- 换行符是 `@`（0x40），普通换行是 0x0A。现在的译文没有插入 `@`，长句靠游戏按像素宽度折行。需要时在合适位置加上半角 `@`。

2197 和 2600 的压缩数据解出来是乱码，不是 PC 上的 “BYE BYE!” / “HELLO T!”。有把握的译法之后再改这两行。

### 文件清单

| 路径 | 作用 |
| --- | --- |
| `.gitignore` | 排除美版镜像，保留 `Grand Theft Auto (USA)/put rom here`。`extract/` 和 `build/` 入库 |
| `text/zh_cn.tsv` | 任务译文。列是 `id`、`zh`、`en`，1310 行 |
| `text/zh_ui.tsv` | 界面译文。列是 `bin`、`id`、`zh`、`en` |
| `text/ps1_decoded.tsv` | 英语槽解出来的句子，含和 PC 文本的差异标记 |
| `text/zh_todo.tsv` | 早期对照表，`zh` 列是空的 |
| `text/zh_hand.tsv` `text/zh_sa.tsv` `text/zh_burro.tsv` `text/zh_vc1.tsv` `text/zh_vc2.tsv` | 合并前的分批底稿。和 `zh_cn.tsv` 冲突时以 `zh_cn.tsv` 为准 |
| `ref/ENGLISH.FXT.txt` | PC 版英语文本，用来对照被截断的句子 |
| `tools/huffman.py` | 英语前缀码，71 个符号，用来核对早期解码 |
| `tools/export_strings.py` | 导出 id / PC 英语对照，会覆盖 `zh_todo.tsv` |
| `tools/build_font.py` | 从两张译文表生成点阵 |
| `tools/repack_mission.py` | 把任务和界面写回英语槽，输出 `build/MISSION.VSR` |
| `tools/patch_exe.py` | 打开宽字并接上点阵，输出 `build/SLUS_001.06` |
| `tools/repack_track.py` | 把上面两个文件放进数据轨，并写 cue |
| `font/NotoSansCJKsc-Regular-subset.otf` | 思源黑体简体子集，SIL OFL 1.1。收译文和 ASCII 用到的 1727 个字符 |
| `font/OFL.txt` | 字体许可证全文 |
| `font/glyphs.bin` | 游戏实际使用的点阵。`u32` 个数，然后每条 `u16` 码位、`u16` 零、32 字节点阵 |
| `font/charset.tsv` | 码位预览索引 |
| `font/page_00.png` … `page_06.png` | 字库预览 |
| `font/page_00.4bpp` … `page_06.4bpp` | 256×256、4bpp 预览图。游戏不读这些页 |
| `extract/SLUS_001.06` `extract/MISSION.VSR` | 补丁输入 |
| `extract/GAMEFONT.VSR` `extract/FNT_8X8.VSR` `extract/FRONTEND.VSR` `extract/GTAMOG.VSR` | 一并抽出的原版资源。当前脚本不读，留着备查 |
| `build/Grand Theft Auto (USA) (Track 01).bin` | 打好的数据轨 |
| `build/Grand Theft Auto (zh).cue` | 原盘位于仓库旁时的播放入口 |
| `build/SLUS_001.06` `build/MISSION.VSR` | 打包中间产物 |

美版原盘目录不要推进仓库。

### 文本和字体在游戏里的位置

`MISSION.VSR` 有 60 个块。前面是界面，后面每个城市一组：一块地图，然后六档文本。语言顺序是英、法、德、意、西、日。

| 块 | 内容 |
| --- | --- |
| 0–5 | 局内文字，六种语言。英语是 bin 0 |
| 6–11 | 前端菜单，六种语言。英语是 bin 6 |
| 12–17 | 六种语言各自的赫夫曼表。英语是 bin 12 |
| 18、25、32、39、46、53 | 地图，不是文本 |
| 19–24 | 自由城简单 |
| 26–31 | 自由城普通 |
| 33–38 | 圣安地列斯普通 |
| 40–45 | 圣安地列斯困难 |
| 47–52 | 罪恶城 1 |
| 54–59 | 罪恶城 2 |

每组六档里的第一档是英语。任务英语档是 bin 19、26、33、40、47、54。

游戏按位读字符串：从自己的正文开始，读进下一条记录开头的 8 字节，直到解出 NUL。只切到下一条偏移时，句子会在词中间断开；游戏里看到的是读完那 8 字节之后的整句。这 8 字节是上一条的尾部，第一条的要原样保留，游戏会把其中第一个字当成文本对象上的字段。

可执行文件基址 `0x80010000`，文件头 0x800 字节。和汉化有关的改动：

| 位置 | 改动 |
| --- | --- |
| 文件偏移 `0xA5F8`（`0x80019DF8`） | 宽字开关从 1 改成 0。美版出厂是关的 |
| `0x800E4F3C` | 宽字缓存不再去读光盘上不存在的 Kanji 资源，改成指向一块自造的显存条 |
| `0x800E545C` | 宽字字符串里的 ASCII 不再转成 Shift-JIS。那些码位和汉字 Unicode 重叠，例如 `S` 的 SJIS 是 U+8272，而 U+8272 是「色」 |
| `0x8012C708` | 原来的 BIOS 点阵查找改成跳到文件尾的二分查找 |
| `0x8012F8D4` 起的空闲区 | 显存描述、一张空白 16×16、查找代码 |
| `0x80130000` 起 | 追加的 `glyphs.bin`。文件头里的装载长度一并加长 |

显存条放在 x=384、y=256，高 16，宽 640 个显存像素（160 个格子，每格 4 像素，4bpp 下是 16 个纹素）。选这里是为了躲开左侧 320 像素宽的帧缓冲。这个坐标没有实机验证。

点阵一行 16 像素打包成一个小端 u16：低字节是左 8 像素，每个字节的 bit 7 是这半边最左边的像素。和 `0x800E51BC` 的读法一致。

`SLUS_001.06` 和 `MISSION.VSR` 都变大了，原位置后面紧挨着下一个文件，不能原地加长。数据轨从 26404 个扇区变成 26437 个，改过的扇区重算了 Mode 2 Form 1 的 EDC/ECC。音轨仍按音轨号播放。

### 排错

汉字缺一角、整句空白或花屏时，改一处就重打 `patch_exe.py` 和 `repack_track.py`：

1. 缺的是某个新字：`build_font.py` 会直接退出并打印这个字。用同一套 OFL 字体补进 `font/NotoSansCJKsc-Regular-subset.otf`。阈值现在是 80，字号 14。笔画被吃掉时，降低阈值或把字号调到 15，然后看 `font/page_00.png`。
2. 整句都是空格子：宽字开关没生效，或查找函数没有跳到 `0x8012F93C`。`patch_exe.py` 会在美版字节对不上时退出。输入永远是 `extract/SLUS_001.06`。
3. 汉字正常、数字或标点是空白：这句里的 ASCII 不在 `glyphs.bin` 里。`patch_exe.py` 会给宽字句子里的 ASCII 补点阵。空格用一张空的 16×16。
4. 画面上有一条横条噪点，或字叠在别的贴图上：改 `tools/patch_exe.py` 里的 `VRAM_X` / `VRAM_Y`。现在是 384, 256，向右延伸到 x=1024。不要放进 x=0–320，那是帧缓冲。
5. 一出现中文就崩溃：宽字缓存的格子数是 0。加载器必须从 `0x800E4F3C` 跳过缺失的 Kanji 资源，再落到原来的 `0x800E4F8C` 去分配那 160 个格子。

`repack_track.py` 会把抽出的 `SLUS_001.06` 和 `MISSION.VSR` 与写进镜像的字节再比一次，并对一个扇区复核 EDC/ECC。校验失败就不要拿那个 bin 去玩。

模拟器拒绝 cue 里的 `../` 时，把音轨路径改成绝对路径，或者把 cue 放到和原版音轨同一层。音轨 bin 不要改。数据轨变长之后，总扇区数写进了主卷描述符。音轨号没变。音乐播到错误的曲子时，先确认模拟器加载的是这份 cue。

换字体时，`build_font.py` 的 `pack_bitmap` 必须继续按「低字节在左、bit 7 在左」输出。改完用「你」看一眼：左半是亻，右半是尔。

### 不要再走的弯路

- 不要把中文塞进 8×8 的 `FNT_8X8` 或 `GAMEFONT` 的拉丁页。那两套都是英文界面字。
- 不要改 `0x800E64C0`。它只把存档文件名转成 Shift-JIS。
- 不要用 PC 的 `KANJI.BIT` 直接替换。PS1 美版不读那个文件。
- 英语界面和中文任务共用 bin 12 这一棵树。只换树、不重编码 bin 0 和 bin 6，菜单会变成乱码。
- 补丁的输入是 `extract/`，输出是 `build/`。
