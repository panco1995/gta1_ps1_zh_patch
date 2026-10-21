# 侠盗猎车手1 美版 PS1 简体中文补丁

这是美版 PlayStation 光盘的私人汉化工作副本。任务对白和传呼机走英语槽，显示为简体中文。菜单、制作人员名单和 CD 音轨仍是英文。法语、德语、意大利语、西班牙语、日语槽没有改。

## 怎么安装

仓库里的 `build/Grand Theft Auto (USA) (Track 01).bin` 就是打好的数据轨。音乐不在仓库里，继续用你自己的美版音轨。

1. 找到你的美版目录，里面要有 `Grand Theft Auto (USA).cue`，以及 `Grand Theft Auto (USA) (Track 01).bin` 到 `(Track 11).bin`。
2. 把原来的 `Grand Theft Auto (USA) (Track 01).bin` 改名备份，例如加上 `.bak`。
3. 把仓库里的 `build/Grand Theft Auto (USA) (Track 01).bin` 复制到这个目录，文件名保持 `Grand Theft Auto (USA) (Track 01).bin`。
4. 用模拟器打开原来的 `Grand Theft Auto (USA).cue`。语言保持英语。

`build/` 里的 cue、`SLUS_001.06`、`MISSION.VSR` 不用拷。汉化在这条数据轨里。音轨 02–11 不要换。想还原游戏时，把备份的 Track 01 拷回去。

## 怎么打包

`extract/` 随仓库走，里面是从美版数据轨抽出、尚未打补丁的文件。把原盘放进 `Grand Theft Auto (USA)/`，文件名不要改，然后直接跑下面的四条命令。

Python 3.9 和 Pillow 也要有。字库用仓库里的 `font/NotoSansCJKsc-Regular-subset.otf`。

要放进来的文件：

| 放在这里 | 是什么 |
| --- | --- |
| `Grand Theft Auto (USA)/Grand Theft Auto (USA) (Track 01).bin` | 美版数据轨，约 59MB。`repack_track.py` 以它为底稿 |
| `Grand Theft Auto (USA)/Grand Theft Auto (USA) (Track 02).bin` … `(Track 11).bin` | 原版 CD 音轨。打包脚本不读它们，生成的 cue 用相对路径指回这个目录 |

仓库里已经有、不用再准备的：

| 路径 | 是什么 |
| --- | --- |
| `extract/SLUS_001.06` | 原版可执行文件，1181696 字节。补丁的输入，不要改这个文件 |
| `extract/MISSION.VSR` | 原版文本包，1058556 字节。补丁的输入，不要改这个文件 |

这两个文件若丢了，可以从 Track 01 再抽。每个扇区 2352 字节，用户数据从偏移 24 开始，长度 2048。`SLUS_001.06` 在扇区 24，`MISSION.VSR` 在扇区 2291。

```bash
python3 tools/build_font.py
python3 tools/repack_mission.py
python3 tools/patch_exe.py
python3 tools/repack_track.py
```

只改已有汉字的译文时，字库不用重做，从 `repack_mission.py` 开始即可。新增了 `zh_cn.tsv` 里没有的字，才要先跑 `build_font.py`。只改显存坐标时，跑 `patch_exe.py` 和 `repack_track.py`。

`repack_mission.py` 会先用英语原文做一次往返，再套中文。任一字符串解不回来，脚本会直接退出，不会写出半成品。

打完后按上面的「怎么安装」，用新的 Track 01 换掉美版目录里的同名文件。`build/Grand Theft Auto (zh).cue` 只在原盘放在仓库旁的 `Grand Theft Auto (USA)/` 时才能直接开，音轨路径写的是 `../Grand Theft Auto (USA)/`。

## 这次做了什么

1. 解开 `MISSION.VSR` 里的英语赫夫曼文本。游戏按位读，一条字符串从自己的正文开始，读进下一条记录开头的 8 字节，直到解出 NUL。所以只切到下一条偏移时，句子会在词中间断开；游戏里看到的是读完那 8 字节之后的整句。
2. 1310 条任务字符串译成简体中文，写在 `text/zh_cn.tsv`。英语槽重编码后仍能解出界面字符串，所以菜单英文还在，只是换了一棵同时容纳中文 UTF-8 字节的赫夫曼树。
3. 用仓库里的思源黑体简体子集画出 16×16 点阵，挂到美版可执行文件里原本关闭的宽字通道上。美版没有汉字图，原来的宽字来自 BIOS 的 Shift-JIS 字库，简体字出不来。
4. 重排数据轨。`SLUS_001.06` 和 `MISSION.VSR` 都变大了，原位置后面紧挨着下一个文件，不能原地加长。数据轨从 26404 个扇区变成 26438 个，改过的扇区重算了 Mode 2 Form 1 的 EDC/ECC。音轨仍按音轨号播放。

宽字只在字符串里出现 U+0101 及以上的字符时启用。纯英文界面继续用 8×8 字体。一条中文句子里的数字和标点也走 16 像素宽。

## 文件清单

### 提交

| 路径 | 作用 |
| --- | --- |
| `README.md` | 本说明 |
| `.gitignore` | 排除美版镜像，保留 `Grand Theft Auto (USA)/put rom here`。`extract/` 和 `build/` 要入库 |
| `text/zh_cn.tsv` | 译文唯一来源。列是 `id`、`zh`、`en`，1310 行 |
| `text/ps1_decoded.tsv` | 英语槽解出来的句子，含和 PC 文本的差异标记 |
| `text/zh_todo.tsv` | 早期对照表，`zh` 列是空的，不要往这里写译文 |
| `text/zh_hand.tsv` `text/zh_sa.tsv` `text/zh_burro.tsv` `text/zh_vc1.tsv` `text/zh_vc2.tsv` | 合并前的分批底稿。和 `zh_cn.tsv` 冲突时以 `zh_cn.tsv` 为准 |
| `ref/ENGLISH.FXT.txt` | PC 版英语文本，用来对照被截断的句子。这是游戏原文，公开仓库要不要带上自己决定 |
| `tools/huffman.py` | 英语前缀码，71 个符号，用来核对早期解码 |
| `tools/export_strings.py` | 从 `MISSION.VSR` 导出 id / PC 英语对照，会覆盖 `zh_todo.tsv` |
| `tools/build_font.py` | 从 `zh_cn.tsv` 生成点阵 |
| `tools/repack_mission.py` | 把中文写回英语槽，输出 `build/MISSION.VSR` |
| `tools/patch_exe.py` | 打开宽字并接上点阵，输出 `build/SLUS_001.06` |
| `tools/repack_track.py` | 把上面两个文件放进数据轨，并写 cue |
| `font/NotoSansCJKsc-Regular-subset.otf` | 思源黑体简体（Noto Sans CJK SC）的子集，SIL OFL 1.1。只收译文和 ASCII 用到的 1636 个字符 |
| `font/OFL.txt` | 这套字体的许可证全文 |
| `font/glyphs.bin` | 游戏实际使用的点阵。按 Unicode 排序：`u32` 个数，然后每条 `u16` 码位、`u16` 零、32 字节点阵 |
| `font/charset.tsv` | 码位预览索引 |
| `font/page_00.png` … `page_06.png` | 字库预览 |
| `font/page_00.4bpp` … `page_06.4bpp` | 256×256、4bpp 预览图。游戏不读这些页，钩子读的是 `glyphs.bin` |
| `extract/SLUS_001.06` | 未打补丁的原版可执行文件，补丁输入 |
| `extract/MISSION.VSR` | 未打补丁的原版文本包，补丁输入 |
| `extract/GAMEFONT.VSR` `extract/FNT_8X8.VSR` `extract/FRONTEND.VSR` `extract/GTAMOG.VSR` | 一并抽出的原版资源，当前脚本不读，留在目录里备查 |
| `build/Grand Theft Auto (USA) (Track 01).bin` | 打好的数据轨，约 59MB。不会打包的人用它替换原版 Track 01 |
| `build/Grand Theft Auto (zh).cue` | 原盘位于仓库旁的 `Grand Theft Auto (USA)/` 时的播放入口 |
| `build/SLUS_001.06` `build/MISSION.VSR` | 打包中间产物。安装时不用单独拷 |

## 文本和字体在游戏里的位置

英语文本槽是 `MISSION.VSR` 的 bin 0、6、19、26、33、40、47、54。赫夫曼表是 bin 12。一组六个语言的顺序是英、法、德、意、西、日。任务城市是自由城简单、自由城普通、圣安地列斯普通、圣安地列斯困难、罪恶城 1、罪恶城 2。bin 0 和 bin 6 是界面（395 + 133 条），没有英文底稿，这次保持原文，只为了跟上新的赫夫曼树而重新编码。

每条字符串前面有 8 字节，解码器不读它。它是上一条句子的尾部。第一条的这 8 字节要原样保留，游戏会把其中第一个字当成文本对象上的字段。

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

## 后期更新文档

### 改一句译文

1. 只编辑 `text/zh_cn.tsv` 里对应 id 的 `zh` 列。不要改分批底稿，也不要重跑 `export_strings.py`，它会把 `zh_todo.tsv` 的译文列清掉。
2. 句子里如果出现字库里没有的字，先跑 `build_font.py`，再跑 `patch_exe.py`。
3. 跑 `repack_mission.py`，再跑 `repack_track.py`。
4. 进游戏翻到这句的任务或传呼机。同一 id 在几个城市槽里会一起换掉。

译文约定，后面改句子时继续沿用：

- 口语，保留粗口的力度。对玩家用「你」。酒店礼貌台词可以用「您」。
- `ps1_decoded.tsv` 里标成和 PC 相同、只是存盘时被截断的句子，按 PC 的完整句来译，不要翻译那个半截单词。
- 标成用词不同的，按 PS1 的词，不按 PC。例如 guys 不是 dealers，pickup 不是 van，Vice Squad 不是 Drug Squad。
- 货币用「块」。破坏提示是「限时 N 秒，砸出 X 块的破坏！」，金额到整万时用「万」。
- 领奖是「去……领奖！还剩 N 秒！」。
- id 2502 必须是 18 个半角句点。id 3502 必须是 9 个半角句点。不要写成省略号。
- 一条中文的 UTF-8 加结尾 NUL，不要超过游戏里已经出现过的最长英语句子（198 字节）。现在最长的中文是 180 字节。明显超长的新句子可能冲掉解码缓冲区。

### 2197 和 2600 仍是「待校」

这两条的压缩数据解出来是乱码，不是 PC 上对应的 “BYE BYE!” / “HELLO T!”。现在游戏里会真的显示出「待校」两个字。

有把握的译法之后：改 `zh_cn.tsv` 这两行，按「改一句译文」重打包。不要为了填空去采用那两句 PC 文本，除非重新解码证明它们就是这个意思。

### 界面的 528 句还是英文

bin 0（局内）和 bin 6（前端）的 id 是槽位序号，不是 PC 的 FXT 键，不能按编号猜英文。`repack_mission.py` 里的解码器已经能把它们解成原文。以后要译的话：先把解出的英文存成表，逐条翻译，再并进打包脚本里现在「界面保持原文」的分支。不要凭 id 编句子。

### 汉字缺一角、整句空白、或者花屏

按这个顺序查，改一处就重打 `patch_exe.py` 和 `repack_track.py`：

1. 缺的是某个新字：`build_font.py` 会直接退出并打印这个字。字库子集里没有它。用同一套 OFL 字体补进 `font/NotoSansCJKsc-Regular-subset.otf`，或换一份覆盖这个字的思源黑体再子集。阈值现在是 80，字号 14。太细的笔画被吃掉时，降低阈值或把字号调到 15，然后看 `font/page_00.png`。
2. 整句都是空格子：宽字开关没生效，或查找函数没有跳到 `0x8012F93C`。`patch_exe.py` 会在美版字节对不上时退出，不要对着已经打过补丁的 `build/SLUS_001.06` 再打一次，输入永远是 `extract/SLUS_001.06`。
3. 汉字正常、数字或标点是空白：这句里的 ASCII 不在 `glyphs.bin` 里。`patch_exe.py` 会给宽字句子里的 ASCII 补点阵；空格用一张空的 16×16，因为宽字模式下空格也占 16 像素。
4. 画面上有一条横条噪点，或字叠在别的贴图上：显存条和游戏贴图撞了。改 `tools/patch_exe.py` 里的 `VRAM_X` / `VRAM_Y`。现在是 384, 256，向右延伸到 x=1024。不要放进 x=0–320，那是帧缓冲。
5. 一出现中文就崩溃：宽字缓存的格子数是 0，绘制时空指针。加载器必须从 `0x800E4F3C` 跳过缺失的 Kanji 资源，再落到原来的 `0x800E4F8C` 去分配那 160 个格子。不要只把 `0xA5F8` 改成 0 而不打这段加载器。

### 中文串成一长行，或不换行

换行符在这套文本里是 `@`（0x40），普通换行是 0x0A。现在的译文没有插入 `@`，长句靠游戏按像素宽度折行。折行明显错误时，在 `zh_cn.tsv` 的合适位置加上 `@`，再走「改一句译文」。不要把 `@` 写成全角。

### 换了字体或点阵格式

`build_font.py` 的 `pack_bitmap` 必须继续按「低字节在左、bit 7 在左」输出。改成普通的从 bit 0 往左排，字会左右切成两半。改完用「你」看一眼：左半是亻，右半是尔。

### 数据轨或 cue 报错

`repack_track.py` 会把抽出的 `SLUS_001.06` 和 `MISSION.VSR` 与写进镜像的字节再比一次，并对一个扇区复核 EDC/ECC。校验失败就不要拿那个 bin 去玩。

模拟器拒绝 cue 里的 `../` 时，把 `build/Grand Theft Auto (zh).cue` 里的音轨路径改成绝对路径，或者把 cue 放到和原版音轨同一层。不要去改音轨 bin。

数据轨变长之后，总扇区数写进了主卷描述符。音轨是独立文件，音轨号没变。如果音乐播到错误的曲子，先确认模拟器加载的是这份 cue，而不是原版 cue。

## 不要再走的弯路

- 不要把中文塞进 8×8 的 `FNT_8X8` 或 `GAMEFONT` 的拉丁页。那两套都是英文界面字。
- 不要改 `0x800E64C0`。它只把存档文件名转成 Shift-JIS。
- 不要用 PC 的 `KANJI.BIT` 直接替换。PS1 美版不读那个文件，宽字按 32 字节、16 行的格式向 BIOS 查找要图。
- 英语界面和中文任务共用 bin 12 这一棵树。只换树、不重编码 bin 0 和 bin 6，菜单会变成乱码。
- 原盘上的 `SLUS_001.06` 不要直接改。补丁的输入是 `extract/`，输出是 `build/`。
