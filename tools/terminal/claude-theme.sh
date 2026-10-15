#!/bin/bash
#
#   按当前终端配色生成完整的 Claude Code 自定义主题(72 个颜色全部覆盖), 只用 bash, 不依赖其他工具; 写到 ~/.claude/themes/.
#
#   bash claude-theme.sh          打印终端深浅与底色, 如: dark #282C34
#   bash claude-theme.sh --new    读终端底色, 正文色与 16 色(OSC 11 / 10 / 4), 混色调优后写 term-light.json 或 term-dark.json;
#                                 终端只回应底色时退回直接引用终端 16 色(ansi:名字, 不调色), 文件名不变
#
#   启动: claude --settings '{"theme":"custom:term-dark"}'
#   按终端深浅自动选: claude --settings "{\"theme\":\"custom:term-$(bash claude-theme.sh | cut -d' ' -f1)\"}"
#   (自定义主题的 base 固定, 一个文件不能自适应深浅; 深浅终端里各生成一次, 启动时按终端底色选)
#
#   每个颜色按内置 light-ansi / dark-ansi 预设取对应的终端色(下表第 2, 3 列). --new 的混色(简化的 comfort 调色):
#     text 正文色; bg 终端底色; accent 终端色, 深色主题的亮色朝底色混 8%(压一点刺眼);
#     gray 底色与正文色按千分比混(次要文字, 边框); tint 底色朝某色混(diff, 消息底, 选区等背景块, 浅色 / 深色比例分列),
#     浅色主题里混入色先掺 30% 正文色去饱和(亮色块饱和度 <= 0.40).
#   比例按 tools/check/claude_theme.py 的门禁口径在 16 套 Comfort 主题上校准: 荧光度 <= 0.045, 背景块与底色对比度 <= 1.6,
#   正文压在背景块上 >= 4.5, 强调色 >= 4.5(浅色 >= 5.0), 亮色块饱和度 <= 0.40, 不出现纯黑 / 纯白.
#
#   VS Code 终端里 Claude Code 会强制降到 256 色(判断依据 TERM_PROGRAM=vscode), 淡色被取整成更艳的格点;
#   启动时清空它可保持 24 位色: TERM_PROGRAM= claude --settings '{"theme":"custom:term-light"}'
#   tmux 里同样降到 256 色(判断依据 TMUX), 设 CLAUDE_CODE_TMUX_TRUECOLOR=1 保持 24 位色(tmux 本身需开 RGB 支持)
#

case "$1" in
  "") action=print ;;
  --new) action=new ;;
  *) echo "未知参数: $1(可用 --new)" >&2; exit 2 ;;
esac

# 终端颜色查询: q <OSC 编号>, 输出 "r g b"(十进制); 回应形如 ESC ] 11 ; rgb:RRRR/GGGG/BBBB BEL, 每个分量取前两位十六进制
q() {
  local resp=
  printf '\033]%s;?\007' "$1" >&3
  IFS= read -r -t 1 -d $'\007' resp <&3
  [[ $resp =~ rgb:([0-9a-fA-F]{2})[0-9a-fA-F]*/([0-9a-fA-F]{2})[0-9a-fA-F]*/([0-9a-fA-F]{2}) ]] || return 1
  echo $((16#${BASH_REMATCH[1]})) $((16#${BASH_REMATCH[2]})) $((16#${BASH_REMATCH[3]}))
}
hex() { printf '#%02X%02X%02X' $1 $2 $3; }
# mix "<r g b>" "<r g b>" <千分比>: 前者 x (1 - a) + 后者 x a
mix() {
  local a=($1) b=($2) t=$3
  echo $(((a[0] * (1000 - t) + b[0] * t) / 1000)) $(((a[1] * (1000 - t) + b[1] * t) / 1000)) $(((a[2] * (1000 - t) + b[2] * t) / 1000))
}
names=(black red green yellow blue magenta cyan white)
# 终端色名 -> 下标(0~15), 如 redBright -> 9
slot() {
  local i n=${1%Bright}
  for i in 0 1 2 3 4 5 6 7; do [ "${names[$i]}" = "$n" ] && break; done
  [ "$n" != "$1" ] && i=$((i + 8))
  echo $i
}

bg= fg= pal=()
if { exec 3<>/dev/tty; } 2>/dev/null; then
  old=$(stty -g <&3)
  stty raw -echo <&3
  bg=$(q 11)
  if [ -n "$bg" ] && [ "$action" = new ]; then
    fg=$(q 10)
    for i in {0..15}; do pal[$i]=$(q "4;$i") || break; done
  fi
  stty "$old" <&3
  exec 3>&-
fi
if [ -z "$bg" ]; then
  echo "终端没有回应底色查询(不支持 OSC 11, 或在 tmux / ssh 里)" >&2
  exit 1
fi
set -- $bg
# 与 Claude Code 判断终端明暗的口径一致: sRGB 按亮度系数加权, > 0.5 为浅色
if [ $((2126 * $1 + 7152 * $2 + 722 * $3)) -gt $((5000 * 255)) ]; then mode=light; else mode=dark; fi
[ "$action" = print ] && { echo "$mode $(hex $bg)"; exit 0; }
# 正文色或 16 色查不全时无法混色, 退回直接引用终端 16 色
ansi=
if [ -z "$fg" ] || [ ${#pal[@]} -lt 16 ]; then
  ansi=1
  echo "终端没有回应正文色或 16 色查询(OSC 10 / OSC 4), 改为直接引用终端 16 色, 不调色" >&2
fi

# 颜色  浅色取的终端色  深色取的终端色  类型  混入的颜色  浅色比例  深色比例(千分比)
table=$(cat <<'EOF'
autoAccept                            magenta        magentaBright  accent  -  -  -
autoAcceptShimmer                     magentaBright  magentaBright  accent  -  -  -
skill                                 magenta        magentaBright  accent  -  -  -
bashBorder                            magenta        magentaBright  accent  -  -  -
claude                                redBright      redBright      accent  -  -  -
claudeShimmer                         yellowBright   yellowBright   accent  -  -  -
claudeBlue_FOR_SYSTEM_SPINNER         blue           blueBright     accent  -  -  -
claudeBlueShimmer_FOR_SYSTEM_SPINNER  blueBright     blueBright     accent  -  -  -
permission                            blue           blueBright     accent  -  -  -
permissionShimmer                     blueBright     blueBright     accent  -  -  -
planMode                              cyan           cyanBright     accent  -  -  -
ide                                   blueBright     blue           accent  -  -  -
promptBorder                          white          white          gray  fg  350  350
promptBorderShimmer                   whiteBright    whiteBright    gray  fg  600  600
text                                  black          whiteBright    text  -  -  -
inverseText                           white          black          bg  -  -  -
inactive                              blackBright    white          gray  fg  620  620
inactiveShimmer                       white          whiteBright    gray  fg  850  850
subtle                                blackBright    white          gray  fg  420  420
suggestion                            blue           blueBright     accent  -  -  -
remember                              blue           blueBright     accent  -  -  -
background                            cyan           cyanBright     accent  -  -  -
success                               green          greenBright    accent  -  -  -
error                                 red            redBright      accent  -  -  -
warning                               yellow         yellowBright   accent  -  -  -
merged                                magenta        magentaBright  accent  -  -  -
warningShimmer                        yellowBright   yellowBright   accent  -  -  -
diffAdded                             green          green          tint  green  160  120
diffRemoved                           red            red            tint  red  140  120
diffAddedDimmed                       green          green          tint  green  80  60
diffRemovedDimmed                     red            red            tint  red  70  60
diffAddedWord                         greenBright    greenBright    tint  green  260  180
diffRemovedWord                       redBright      redBright      tint  red  240  200
red_FOR_SUBAGENTS_ONLY                red            redBright      accent  -  -  -
blue_FOR_SUBAGENTS_ONLY               blue           blueBright     accent  -  -  -
green_FOR_SUBAGENTS_ONLY              green          greenBright    accent  -  -  -
yellow_FOR_SUBAGENTS_ONLY             yellow         yellowBright   accent  -  -  -
purple_FOR_SUBAGENTS_ONLY             magenta        magentaBright  accent  -  -  -
orange_FOR_SUBAGENTS_ONLY             redBright      redBright      accent  -  -  -
pink_FOR_SUBAGENTS_ONLY               magentaBright  magentaBright  accent  -  -  -
cyan_FOR_SUBAGENTS_ONLY               cyan           cyanBright     accent  -  -  -
professionalBlue                      blueBright     blueBright     accent  -  -  -
chromeYellow                          yellow         yellowBright   accent  -  -  -
clawd_body                            redBright      redBright      accent  -  -  -
clawd_background                      black          black          bg  -  -  -
userMessageBackground                 white          blackBright    tint  fg  100  100
userMessageBackgroundHover            whiteBright    black          tint  fg  150  150
composerSidebarBackground             white          blackBright    tint  fg  70  70
selectionBg                           cyan           blue           tint  blue  220  220
bashMessageBackgroundColor            whiteBright    black          tint  magenta  100  100
memoryBackgroundColor                 white          blackBright    tint  blue  100  100
rate_limit_fill                       yellow         yellow         accent  -  -  -
rate_limit_empty                      black          white          gray  fg  250  250
fastMode                              red            redBright      accent  -  -  -
fastModeShimmer                       redBright      redBright      accent  -  -  -
effortUltra                           magenta        magentaBright  accent  -  -  -
briefLabelYou                         blue           blueBright     accent  -  -  -
briefLabelClaude                      redBright      redBright      accent  -  -  -
rainbow_red                           red            red            accent  -  -  -
rainbow_orange                        redBright      redBright      accent  -  -  -
rainbow_yellow                        yellow         yellow         accent  -  -  -
rainbow_green                         green          green          accent  -  -  -
rainbow_blue                          cyan           cyan           accent  -  -  -
rainbow_indigo                        blue           blue           accent  -  -  -
rainbow_violet                        magenta        magenta        accent  -  -  -
rainbow_red_shimmer                   redBright      redBright      accent  -  -  -
rainbow_orange_shimmer                yellow         yellow         accent  -  -  -
rainbow_yellow_shimmer                yellowBright   yellowBright   accent  -  -  -
rainbow_green_shimmer                 greenBright    greenBright    accent  -  -  -
rainbow_blue_shimmer                  cyanBright     cyanBright     accent  -  -  -
rainbow_indigo_shimmer                blueBright     blueBright     accent  -  -  -
rainbow_violet_shimmer                magentaBright  magentaBright  accent  -  -  -
EOF
)

body=
while read -r token light dark kind src al ad; do
  [ "$mode" = light ] && s=$light a=$al || s=$dark a=$ad
  if [ -n "$ansi" ]; then
    v="ansi:$s"
  else
    case "$kind" in
      text) v=$(hex $fg) ;;
      bg) v=$(hex $bg) ;;
      gray) v=$(hex $(mix "$bg" "$fg" $a)) ;;
      tint)
        [ "$src" = fg ] && c=$fg || c=${pal[$(slot "$src")]}
        # 浅色: 混入色先掺 30% 正文色去饱和, 近白处的淡红淡绿才不会是糖果色
        [ "$mode" = light ] && [ "$src" != fg ] && c=$(mix "$c" "$fg" 300)
        v=$(hex $(mix "$bg" "$c" $a)) ;;
      accent)
        c=${pal[$(slot "$s")]}
        [ "$mode" = dark ] && [ "${s%Bright}" != "$s" ] && c=$(mix "$c" "$bg" 80)
        v=$(hex $c) ;;
    esac
  fi
  body="$body    \"$token\": \"$v\",
"
done <<< "$table"

dir="$HOME/.claude/themes"
name="term-$mode"
base=$mode
[ -n "$ansi" ] && base="$mode-ansi"
mkdir -p "$dir"
{
  printf '{\n  "name": "%s",\n  "base": "%s",\n  "overrides": {\n' "$name" "$base"
  printf '%s' "${body%,
}"
  printf '\n  }\n}\n'
} > "$dir/$name.json"
echo "已写 $dir/$name.json"
echo "启动: claude --settings '{\"theme\":\"custom:$name\"}'"
