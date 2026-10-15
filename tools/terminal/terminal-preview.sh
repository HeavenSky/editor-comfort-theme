#!/bin/bash
#
#   Terminal theme preview.
#
#   1. 常用场景: 默认背景上的彩色字 / 粗体 / 弱化, 彩色底徽标(配黑字或白字),
#      反色, 注释色(90m). 这些都应该清晰可读.
#   2. 完整矩阵(加 --full 显示): 每种前景色叠在每种背景色上, 每格左为正常, 右为粗体.
#      矩阵里注定有大量看不清的格子, 属于正常现象, 不代表主题有问题:
#        - 同色系(如 32m 配 42m/102m) 本来就是同一个颜色;
#        - 深色主题的彩色是亮色, 当背景时配默认浅色字必然看不清;
#          浅色主题反之. 彩色底请配 30m(黑) 或 97m(白) 字.
#
#   终端宽度够时尽量并排输出以减少行数; 不够时自动退回上下排列.
#

# 矩阵测试文字, 须占 3 个显示列(汉字算 2 列). 默认 l繁:
#   l  细竖笔画, 对比度不足时最先变淡消失
#   繁 笔画密集的汉字, 对比度不足时最先糊成一团
# Il1 e中 鑫l gYw
# 可用环境变量覆盖, 例: T=gYw bash terminal-preview.sh --full
T="${T:-鑫l}"
names=(black red green yellow blue magenta cyan white)
cols=$(tput cols 2>/dev/null || echo 80)

# 常用场景右侧的补充样例, 按行号拼到彩色字那 8 行后面
extras=(
  "normal  \033[1mbold\033[0m  \033[2mdim\033[0m  \033[3mitalic\033[0m  \033[4munderline\033[0m  \033[7mreverse\033[0m  \033[9mstrike\033[0m"
  "\033[90mcomment/autosuggest(90m)\033[0m"
  "\033[32m+ added line\033[0m  \033[31m- removed line\033[0m  \033[36m@@ hunk @@\033[0m"
  "\033[1;34mdir/\033[0m  \033[1;32mexec*\033[0m  \033[35mlink@\033[0m  \033[33mwarning:\033[0m  \033[1;31merror:\033[0m"
)
inline_extras=0
[ "$cols" -ge 150 ] && inline_extras=1

# 左: 彩色字; 中: 同一颜色的徽标(4Xm / 10Xm 底配 30m 黑字或 97m 白字) 与反色; 右: 补充样例
echo " 彩色字 (正常 / 粗体 / 弱化 / 亮色9Xm)  徽标 (4Xm 底 黑/白字, 10Xm 底 黑/白字, 反色)"
for i in 0 1 2 3 4 5 6 7; do
  printf '  \033[3%dm%-8s\033[0m \033[1;3%dm%-8s\033[0m \033[2;3%dm%-8s\033[0m \033[9%dm%-8s\033[0m   ' \
    "$i" "${names[$i]}" "$i" bold "$i" dim "$i" bright
  printf '\033[30;4%dm PASS \033[0m \033[97;4%dm PASS \033[0m  \033[30;10%dm PASS \033[0m \033[97;10%dm PASS \033[0m  \033[7;3%dm %-7s \033[0m' \
    "$i" "$i" "$i" "$i" "$i" "${names[$i]}"
  [ "$inline_extras" = 1 ] && [ -n "${extras[$i]}" ] && echo -en "   ${extras[$i]}"
  echo
done
[ "$inline_extras" = 1 ] || for e in "${extras[@]}"; do echo -e " $e"; done

[ "$1" = "--full" ] || { echo " (加 --full 查看完整 16x16 矩阵)"; exit 0; }

# 每格 9 列: 正常 gYw + 粗体 gYw; 前景只列 m / 3Xm / 9Xm 共 17 行
print_grid() {
  local bgs=("$@")
  printf '\n      %6s   ' def
  for BG in "${bgs[@]}"; do
    [ -z "$BG" ] && { printf ' '; continue; }
    printf ' %6s   ' "$BG"
  done
  echo '  (每格: 正常 粗体)'
  for FG in m 30m 90m 31m 91m 32m 92m 33m 93m 34m 94m 35m 95m 36m 96m 37m 97m; do
    printf ' %4s ' "$FG"
    echo -en "\033[$FG $T \033[1m$T \033[0m"
    for BG in "${bgs[@]}"; do
      # 空字符串是左右两组之间的分隔
      [ -z "$BG" ] && { echo -n " "; continue; }
      echo -en " \033[$FG\033[$BG $T \033[1m$T \033[0m"
    done
    echo
  done
}

# 并排约需 180 列, 否则 40-47m 与 100-107m 上下排列
if [ "$cols" -ge 180 ]; then
  print_grid 40m 41m 42m 43m 44m 45m 46m 47m '' 100m 101m 102m 103m 104m 105m 106m 107m
else
  print_grid 40m 41m 42m 43m 44m 45m 46m 47m
  print_grid 100m 101m 102m 103m 104m 105m 106m 107m
fi
