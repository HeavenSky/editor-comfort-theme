# /// script
# requires-python = ">=3.11"
# ///
# 从本机 VS Code 安装包静态提取全部颜色键的官方说明与四种主题类型的默认值(不执行安装包内任何代码).
# 数据源: out/vs/workbench/workbench.desktop.main.js 里的 registerColor 包装函数调用 + out/nls.messages.json(说明按下标引用)
#        + extensions/*/package.json 的 contributes.colors(说明经 package.nls.json 引用).
# 产物 assets/vscode/vscode-color-docs.json 供 tools/lab/threshold-lab.mjs 的颜色键分层复核页(/keys)显示说明与默认值; VS Code 升级后与 extract_registry.py 一起重跑.
# 用法: uv run tools/gen/extract_key_docs.py [VS Code.app 路径] [输出 json 路径]
import json, os, re, sys

APP = sys.argv[1] if len(sys.argv) > 1 else '/Applications/Visual Studio Code.app'
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'vscode', 'vscode-color-docs.json'))
RES = os.path.join(APP, 'Contents', 'Resources', 'app')
BUNDLE = os.path.join(RES, 'out', 'vs', 'workbench', 'workbench.desktop.main.js')
MODES = ('dark', 'light', 'hcDark', 'hcLight')
NAMED = {'white': '#FFFFFF', 'black': '#000000', 'red': '#FF0000', 'blue': '#0000FF', 'green': '#00FF00',
         'cyan': '#00FFFF', 'lightgrey': '#D3D3D3', 'transparent': '#00000000'}
OPS = {0: 'darken', 1: 'lighten', 2: 'transparent', 3: 'opaque', 4: 'oneOf', 5: 'lessProminent', 6: 'ifDefinedThenElse', 7: 'mix'}
OP_FIELDS = {0: ('value', 'factor'), 1: ('value', 'factor'), 2: ('value', 'factor'), 3: ('value', 'background'),
             4: ('values',), 5: ('value', 'background', 'factor', 'transparency'), 6: ('if', 'then', 'else'), 7: ('color', 'with', 'ratio')}


class ParseError(Exception):
    pass


# ---------- 极简 JS 表达式解析(只覆盖 registerColor 参数里出现的子集) ----------
class P:
    def __init__(self, s, i):
        self.s, self.i = s, i

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t\r\n':
            self.i += 1

    def peek(self, t):
        self.ws()
        return self.s.startswith(t, self.i)

    def eat(self, t):
        if not self.peek(t):
            raise ParseError(f'期望 {t!r} 于 {self.s[self.i:self.i + 40]!r}')
        self.i += len(t)

    def string(self):
        q = self.s[self.i]
        j, out = self.i + 1, []
        while self.s[j] != q:
            if self.s[j] == '\\':
                out.append(json.loads('"' + self.s[j:j + 2] + '"') if self.s[j + 1] in 'nrt"\\/bfu' and self.s[j + 1] != 'u' else self.s[j + 1])
                j += 2
            else:
                out.append(self.s[j])
                j += 1
        self.i = j + 1
        return ('str', ''.join(out))

    def expr(self):
        e = self.unary()
        self.ws()
        # 二元与三元运算在本场景罕见, 碰到即放弃(由调用方记为解析失败)
        if self.i < len(self.s) and self.s[self.i] in '?|&+*/<>=' and not self.s.startswith('=>', self.i):
            raise ParseError(f'不支持的运算符 {self.s[self.i:self.i + 10]!r}')
        return e

    def unary(self):
        self.ws()
        c = self.s[self.i]
        if c == '!':
            self.i += 1
            v = self.unary()
            if v[0] == 'num':
                return ('bool', v[1] == 0)
            raise ParseError('! 后非数字')
        if c == '-':
            self.i += 1
            v = self.unary()
            if v[0] == 'num':
                return ('num', -v[1])
            raise ParseError('- 后非数字')
        if self.s.startswith('void ', self.i):
            self.i += 5
            self.unary()
            return ('null',)
        if self.s.startswith('new ', self.i):
            self.i += 4
            callee = self.primary()
            while self.peek('.'):
                self.eat('.')
                callee = ('member', callee, self.ident())
            args = self.args() if self.peek('(') else []
            return self.postfix(('new', callee, args))
        return self.postfix(self.primary())

    def ident(self):
        self.ws()
        m = re.compile(r'[A-Za-z_$][\w$]*').match(self.s, self.i)
        if not m:
            raise ParseError(f'期望标识符于 {self.s[self.i:self.i + 30]!r}')
        self.i = m.end()
        return m.group(0)

    def args(self):
        self.eat('(')
        out = []
        while not self.peek(')'):
            out.append(self.expr())
            if self.peek(','):
                self.eat(',')
        self.eat(')')
        return out

    def primary(self):
        self.ws()
        c = self.s[self.i]
        if c in '"\'':
            return self.string()
        if c == '`':
            j = self.s.index('`', self.i + 1)
            raw = self.s[self.i + 1:j]
            self.i = j + 1
            if '${' in raw:
                raise ParseError('模板字符串含插值')
            return ('str', raw)
        if m := re.compile(r'(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?').match(self.s, self.i):
            self.i = m.end()
            return ('num', float(m.group(0)))
        if c == '{':
            self.i += 1
            props = {}
            while not self.peek('}'):
                self.ws()
                k = self.string()[1] if self.s[self.i] in '"\'' else self.ident()
                if self.peek(':'):
                    self.eat(':')
                    props[k] = self.expr()
                else:
                    props[k] = ('id', k)
                if self.peek(','):
                    self.eat(',')
            self.eat('}')
            return ('obj', props)
        if c == '[':
            self.i += 1
            items = []
            while not self.peek(']'):
                items.append(self.expr())
                if self.peek(','):
                    self.eat(',')
            self.eat(']')
            return ('arr', items)
        if c == '(':
            self.i += 1
            e = self.expr()
            self.eat(')')
            return e
        name = self.ident()
        if name == 'null':
            return ('null',)
        if name in ('true', 'false'):
            return ('bool', name == 'true')
        return ('id', name)

    def postfix(self, e):
        while True:
            self.ws()
            if self.s.startswith('?.', self.i) or (self.peek('.') and not re.match(r'\.\d', self.s[self.i:self.i + 2])):
                self.i += 2 if self.s.startswith('?.', self.i) else 1
                e = ('member', e, self.ident())
            elif self.peek('('):
                e = ('call', e, self.args())
            else:
                return e


# ---------- 上下文: 变量 -> 颜色键, 工厂函数 -> op, 颜色类名, 本地化函数 ----------
class Ctx:
    def __init__(self, src, messages):
        self.src, self.messages = src, messages
        self.var2key = {}
        self.factories = {}
        for m in re.finditer(r'function ([\w$]+)\(([\w$,.]*)\)\{return\{op:(\d)', src):
            self.factories[m.group(1)] = int(m.group(3))
        self.color_cls = re.search(r'([\w$]+)\.fromHex\("#', src).group(1)
        self.const_cache = {}

    def lookup_const(self, name, depth):
        """未知标识符: 在 bundle 里找 `name=` 的首个定义并解析其右值."""
        if name in self.const_cache:
            return self.const_cache[name]
        self.const_cache[name] = None  # 防递归
        res = None
        for m in re.finditer(r'(?<![\w$.])' + re.escape(name) + r'=(?![=>])', self.src):
            try:
                p = P(self.src, m.end())
                ast = p.expr()
                if ast[0] == 'call' and ast[1] == ('id', REG) and ast[2] and ast[2][0][0] == 'str':
                    res = ast[2][0][1]
                else:
                    res = self.render(ast, depth + 1)
                break
            except (ParseError, IndexError, KeyError, ValueError):
                continue
        self.const_cache[name] = res
        return res

    def hexnorm(self, h):
        s = h[1:]
        if len(s) in (3, 4):
            s = ''.join(c * 2 for c in s)
        return '#' + s.upper()

    def render(self, e, depth=0):
        """把默认值 AST 渲染成可读字符串; 字面色归一为 #RRGGBB[AA], 引用其他键直接写键名."""
        if depth > 8:
            raise ParseError('递归过深')
        t = e[0]
        if t == 'null':
            return None
        if t == 'str':
            return self.hexnorm(e[1]) if e[1].startswith('#') else e[1]
        if t == 'num':
            return ('%g' % e[1])
        if t == 'bool':
            return 'true' if e[1] else 'false'
        if t == 'id':
            if e[1] in self.var2key:
                return self.var2key[e[1]]
            v = self.lookup_const(e[1], depth)
            if v is None:
                raise ParseError(f'无法解析标识符 {e[1]}')
            return v
        if t == 'member':
            if e[1] == ('id', self.color_cls) and e[2] in NAMED:
                return NAMED[e[2]]
            raise ParseError(f'未知成员 {e}')
        if t == 'obj':
            if 'op' in e[1]:
                op = int(e[1]['op'][1])
                return self.fmt_op(op, [e[1].get(f) for f in OP_FIELDS[op]], depth)
            raise ParseError('对象不是 op 表达式')
        if t == 'new':
            # new Color(new RGBA(r,g,b,a))
            inner = e[2][0] if e[2] else None
            if inner and inner[0] == 'new' and all(a[0] == 'num' for a in inner[2]):
                r, g, b, *a = [x[1] for x in inner[2]]
                return '#%02X%02X%02X' % (int(r), int(g), int(b)) + ('%02X' % round(a[0] * 255) if a and a[0] != 1 else '')
            raise ParseError('未知 new 表达式')
        if t == 'call':
            callee, args = e[1], e[2]
            if callee[0] == 'id' and callee[1] in self.factories:
                op = self.factories[callee[1]]
                if op == 4:
                    return 'oneOf(' + ', '.join(str(self.render(a, depth + 1)) for a in args) + ')'
                return self.fmt_op(op, args, depth)
            if callee[0] == 'member' and callee[1] == ('id', self.color_cls) and callee[2] == 'fromHex':
                return self.hexnorm(args[0][1])
            if callee[0] == 'member' and callee[2] in ('transparent', 'lighten', 'darken') and len(args) == 1:
                base = self.render(callee[1], depth + 1)
                factor = self.render(args[0], depth + 1)
                if callee[2] == 'transparent' and re.fullmatch(r'#[0-9A-F]{6}', base or ''):
                    return base + '%02X' % round(float(factor) * 255)
                return f'{callee[2]}({base}, {factor})'
            raise ParseError(f'未知调用 {callee}')
        raise ParseError(f'未知节点 {t}')

    def fmt_op(self, op, args, depth):
        if op == 4:
            vals = args[0][1] if args and args[0] and args[0][0] == 'arr' else args
            return 'oneOf(' + ', '.join(str(self.render(a, depth + 1)) for a in vals) + ')'
        parts = [str(self.render(a, depth + 1)) if a is not None else 'null' for a in args]
        return f'{OPS[op]}(' + ', '.join(parts) + ')'

    def text(self, e):
        """说明: d(N, null, ...args) -> nls.messages.json[N] 并代入 {0}.."""
        if e[0] == 'str':
            return e[1]
        if e[0] == 'call' and e[1][0] == 'id' and e[2] and e[2][0][0] == 'num':
            msg = self.messages[int(e[2][0][1])]
            for i, a in enumerate(e[2][2:]):
                msg = msg.replace('{%d}' % i, a[1] if a[0] == 'str' else self.render(a))
            return msg
        raise ParseError(f'说明不是本地化调用 {e[0]}')


REG = 'ae'


def main():
    global REG
    src = open(BUNDLE, encoding='utf-8').read()
    messages = json.load(open(os.path.join(RES, 'out', 'nls.messages.json'), encoding='utf-8'))
    version = json.load(open(os.path.join(RES, 'package.json')))['version']
    REG = re.search(r'(?<![\w$])([\w$]+)\("editor\.background",\{', src).group(1)
    ctx = Ctx(src, messages)
    call_re = re.compile(r'(?<![\w$.])' + re.escape(REG) + r'\(')
    calls = []
    # 第一遍: 解析全部调用, 建立 变量名 -> 颜色键
    for m in call_re.finditer(src):
        try:
            p = P(src, m.end() - 1)
            args = p.args()
        except (ParseError, IndexError) as ex:
            calls.append((None, None, f'参数解析失败: {ex}', m.start()))
            continue
        if not args or args[0][0] != 'str':
            calls.append((None, args, '颜色 id 不是字符串字面量(循环注册)', m.start()))
            continue
        key = args[0][1]
        if lm := re.search(r'([\w$]+)=$', src[max(0, m.start() - 60):m.start()]):
            ctx.var2key.setdefault(lm.group(1), key)
        calls.append((key, args, None, m.start()))
    out, failed = {}, {}
    for key, args, err, pos in calls:
        if key is None:
            failed[f'@{pos}'] = err
            continue
        if key in out:
            continue
        entry = {'description': None, 'defaults': {}, 'needsTransparency': False, 'deprecationMessage': None, 'source': 'workbench'}
        errs = []
        try:
            entry['description'] = ctx.text(args[2]) if len(args) > 2 else None
        except (ParseError, IndexError, KeyError) as ex:
            errs.append(f'说明: {ex}')
        d = args[1]
        for mode in MODES:
            try:
                if d[0] == 'obj' and 'op' not in d[1]:
                    v = d[1].get(mode)
                    entry['defaults'][mode] = ctx.render(v) if v is not None else None
                else:
                    entry['defaults'][mode] = ctx.render(d)
            except (ParseError, IndexError, KeyError, ValueError, TypeError) as ex:
                entry['defaults'][mode] = '?'
                errs.append(f'{mode}: {ex}')
        if len(args) > 3:
            entry['needsTransparency'] = args[3] == ('bool', True)
        if len(args) > 4 and args[4][0] != 'null':
            try:
                entry['deprecationMessage'] = ctx.text(args[4])
            except ParseError as ex:
                errs.append(f'废弃说明: {ex}')
        if errs:
            entry['errors'] = errs
            failed[key] = '; '.join(errs)
        out[key] = entry
    # 终端 16 色: 映射表 {"terminal.ansiX": {index, defaults}} 循环注册, 说明模板 "'{0}' ANSI color in the terminal."
    tmpl = None
    if tm := re.search(re.escape(REG) + r'\(s,o\.defaults,[\w$]+\((\d+),null,e\)\)', src):
        tmpl = messages[int(tm.group(1))]
    for m in re.finditer(r'"(terminal\.ansi\w+)":(\{index:\d+,defaults:\{[^{}]*\}\})', src):
        try:
            obj = P(m.group(2), 0).expr()
            dv = obj[1]['defaults'][1]
            out.setdefault(m.group(1), {'description': tmpl.replace('{0}', m.group(1)[13:]) if tmpl else None,
                                        'defaults': {k: ctx.render(dv[k]) if k in dv else None for k in MODES},
                                        'needsTransparency': False, 'deprecationMessage': None, 'source': 'workbench'})
        except (ParseError, KeyError) as ex:
            failed[m.group(1)] = f'终端色解析失败: {ex}'
    if any(k.startswith('@') for k in failed) and any(k.startswith('terminal.ansi') for k in out):
        for k in [k for k, v in failed.items() if k.startswith('@') and '循环注册' in v]:
            del failed[k]  # 循环注册已由终端映射表覆盖
    # 内置扩展 contributes.colors, 说明 "%x%" 走 package.nls.json; hc 缺省时回落到 dark / light(与 workbench 注册逻辑一致)
    extdir = os.path.join(RES, 'extensions')
    for ext in sorted(os.listdir(extdir)):
        pj = os.path.join(extdir, ext, 'package.json')
        if not os.path.isfile(pj):
            continue
        cols = json.load(open(pj, encoding='utf-8')).get('contributes', {}).get('colors', [])
        if not cols:
            continue
        nlsf = os.path.join(extdir, ext, 'package.nls.json')
        nls = json.load(open(nlsf, encoding='utf-8')) if os.path.isfile(nlsf) else {}
        for c in cols:
            desc = c.get('description')
            if isinstance(desc, str) and re.fullmatch(r'%.+%', desc):
                v = nls.get(desc[1:-1])
                desc = v.get('message') if isinstance(v, dict) else v
            dd = c.get('defaults') or {}
            raw = {'dark': dd.get('dark'), 'light': dd.get('light'), 'hcDark': dd.get('highContrast', dd.get('dark')),
                   'hcLight': dd.get('highContrastLight', dd.get('light'))}
            out.setdefault(c['id'], {'description': desc,
                                     'defaults': {k: (ctx.hexnorm(v) if isinstance(v, str) and v.startswith('#') else v) for k, v in raw.items()},
                                     'needsTransparency': False, 'deprecationMessage': None, 'source': f'extension:{ext}'})
            if not desc:
                failed[c['id']] = '扩展未提供说明'
    ok = sum(1 for k, v in out.items() if 'errors' not in v and v['description'])
    json.dump({'vscodeVersion': version, 'count': len(out), 'ok': ok, 'failed': failed, 'colors': dict(sorted(out.items()))},
              open(OUT, 'w', encoding='utf-8'), indent='\t', ensure_ascii=False)
    print(f'VS Code {version}: {len(out)} 键, 说明与默认值完整 {ok}, 失败 {len(failed)} -> {OUT}')
    for k, v in list(failed.items())[:40]:
        print('  失败', k, v)


if __name__ == '__main__':
    main()
