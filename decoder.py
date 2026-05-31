"""
Multi-layer HTML/PHP/JS obfuscation decoder - FIXED VERSION.

Handles:
  @HTMLObfuscateBot (DHIRAJ9619 style) — state-machine XOR/RC4/table cipher
  PHPKobo HTML obfuscator    — stream-cipher + LRM/ZWJ/RLM lookup table
  PHPKobo wrapped in base64  — var _sec = atob(...) -> document.write
  PHPKodo                    — gzinflate / str_rot13 / base64_decode eval chains
  PHPCabbo                   — variable-based obfuscation ($O00O0O style)
  Dean Edwards Packer        — eval(function(p,a,c,k,e,d){...})
  JS Obfuscator.io           — hex string arrays, _0x patterns
  JSFuck / AAencode           — []()!+ style
  Base64                     — raw blobs, inline base64_decode(), atob()
  gzinflate / gzuncompress / gzdecode
  str_rot13
  HTML entities              — &lt; &amp; &#60; &#x3C; ...
  Hex / Unicode escapes      — \\x41 \\u0041
  URL encoding               — %20 %3C ...
  JS eval(atob/unescape/decodeURIComponent)
  JS String.fromCharCode(...)
  document.write(atob/unescape)
  Advanced JS Array/String extraction for web layout decodes
  Multi-layer combinations   — up to 25 passes

FIX: Removed 75510-byte hard limit in _run_dhiraj9619_cipher so that
     password logic, Firebase config, and all business logic after the
     anti-debug wrapper is fully included in the decoded output.
"""

import base64
import zlib
import html
import re
import urllib.parse
import codecs
import json


def _b64_decode(s: str) -> bytes:
    s = re.sub(r'\s', '', s)
    pad = (4 - len(s) % 4) % 4
    try:
        return base64.b64decode(s + '=' * pad)
    except Exception:
        return b''


def _rot13_bytes(b: bytes) -> bytes:
    return b.translate(bytes.maketrans(
        b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
        b'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'
    ))


def _inflate(b: bytes) -> bytes:
    for wbits in (-15, 15, 47):
        try:
            return zlib.decompress(b, wbits)
        except Exception:
            pass
    return b''


def _to_str(b: bytes) -> str:
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('utf-8', errors='replace')


def _atob_decode(b64: str) -> str:
    raw = _b64_decode(b64)
    if not raw:
        return ''
    try:
        return raw.decode('utf-8')
    except Exception:
        pass
    try:
        latin = raw.decode('latin-1')
        pct = ''.join(f'%{ord(c):02X}' if ord(c) > 127 else c for c in latin)
        return urllib.parse.unquote(pct, encoding='utf-8')
    except Exception:
        pass
    return _to_str(raw)


def _looks_like_code(s: str) -> bool:
    if not s or len(s) < 5:
        return False
    markers = [
        '<?php', '<?', '<html', '<body', '<head', '<script',
        'function', 'eval(', 'echo ', 'document.', 'window.',
        'var ', 'const ', 'let ', '=>', '{}', '<div', '<span',
        'return ', 'if (', 'while (', 'for (', '<!DOCTYPE',
        '<meta', '<title', '<style', 'getElementById',
    ]
    return any(m in s for m in markers) or len(s) > 50


def _is_html_or_clean(s: str) -> bool:
    if not s:
        return False
    tags = ['<html', '<head', '<body', '<!DOCTYPE', '<title', '<div',
            '<script', '<style', '<meta', '<link', '<?php']
    return any(t in s for t in tags)


def _parse_js_int_array(text: str, var_name: str) -> list:
    pattern = r'var\s+' + re.escape(var_name) + r'\s*=\s*\[([^\]]+)\]'
    m = re.search(pattern, text)
    if not m:
        return []
    try:
        return [int(x.strip()) for x in m.group(1).split(',') if x.strip()]
    except Exception:
        return []


def _rc4(data: bytearray, key: list) -> bytearray:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 255
        S[i], S[j] = S[j], S[i]
    i = j = 0
    out = bytearray(len(data))
    for k in range(len(data)):
        i = (i + 1) & 255
        j = (j + S[i]) & 255
        S[i], S[j] = S[j], S[i]
        out[k] = data[k] ^ S[(S[i] + S[j]) & 255]
    return out


def _extract_nonscript_html(code: str) -> str:
    s = re.sub(r'<!--[\s\S]*?-->', '', code)
    s = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', s, flags=re.IGNORECASE)
    s = s.strip()
    if not s or len(s) < 50:
        return ''
    for tag in ['<!DOCTYPE', '<html', '</html>', '<head', '</head>', '<body',
                '</body>', '<style', '</style>', '<div', '</div>',
                '<input', '<button', '<h2', '<h3']:
        s = s.replace(tag, '\n' + tag)
    s = re.sub(r'\n{3,}', '\n\n', s).strip()
    return s


def _run_dhiraj9619_cipher(code: str) -> str:
    """
    Run the DHIRAJ9619 11-step cipher (original variable names only).
    For generic/any-variable-name decoding, use _decode_dhiraj9619_generic().
    """
    try:
        arr1 = _parse_js_int_array(code, '_RWcZroasWtEaG')
        arr2 = _parse_js_int_array(code, '_jiLr865KTovCK')
        arr3 = _parse_js_int_array(code, '_Qz3DqJPy1Um')
        key_nipyne   = _parse_js_int_array(code, '_NipyneUgD')
        key_7vf9     = _parse_js_int_array(code, '_7VF9TbR9EivT4')
        key_dp3      = _parse_js_int_array(code, '_DP3CTux4AleO')
        key_xus      = _parse_js_int_array(code, '_XUsPY0s2lfIv')
        sbox_4qk     = _parse_js_int_array(code, '_4qkMxixtbB7')
        sbox_zyaq    = _parse_js_int_array(code, '_zyaq6FJZ')
        idx_c42      = _parse_js_int_array(code, '_c42vyyRADjDER')
        idx_d35      = _parse_js_int_array(code, '_D3522NrqCvvy')

        if not arr1 or not arr2 or not arr3:
            return ''
        if not key_nipyne or not key_dp3 or not sbox_4qk or not sbox_zyaq:
            return ''

        data = bytearray(arr1 + arr2 + arr3)
        n = len(data)

        kd = key_dp3
        for i in range(n):
            data[i] ^= kd[i % len(kd)]

        if idx_d35:
            blocks = n // 16
            tmp = bytearray(n)
            for b in range(blocks):
                src = idx_d35[b] * 16
                dst = b * 16
                tmp[dst:dst+16] = data[src:src+16]
            data = tmp

        if sbox_zyaq and len(sbox_zyaq) >= 256:
            sz = sbox_zyaq
            for i in range(n):
                data[i] = sz[data[i]]

        if key_7vf9:
            k7 = key_7vf9
            for i in range(n):
                data[i] ^= k7[i % len(k7)]

        if key_xus:
            kx = key_xus
            for i in range(n):
                data[i] = (data[i] - kx[i % len(kx)] + 256) & 255

        prev = 76
        for i in range(n):
            orig = data[i]
            data[i] ^= prev
            prev = orig

        for i in range(n):
            r = i & 7
            if r > 0:
                data[i] = ((data[i] >> r) | (data[i] << (8 - r))) & 255

        if idx_c42:
            blocks = n // 16
            tmp = bytearray(n)
            for b in range(blocks):
                src = idx_c42[b] * 16
                dst = b * 16
                tmp[dst:dst+16] = data[src:src+16]
            data = tmp

        if sbox_4qk and len(sbox_4qk) >= 256:
            s4 = sbox_4qk
            for i in range(n):
                data[i] = s4[data[i]]

        data = _rc4(data, key_nipyne)
        return _to_str(bytes(data))

    except Exception:
        return ''


def _detect_dhiraj9619_generic(code: str) -> bool:
    """Detect DHIRAJ9619 cipher by pattern, not by specific variable names."""
    has_fromcharcode = bool(re.search(
        r'for\s*\(\s*\w+\s*=\s*0\s*;\s*\w+\s*<\s*\d{4,}\s*;[^)]*\)\s*\{[^}]*String\.fromCharCode',
        code
    ))
    if not has_fromcharcode:
        return False
    has_switch = bool(re.search(r'while\s*\(\w+\)\s*\{\s*switch\s*\(\w+\)\s*\{', code))
    if not has_switch:
        return False
    large_arrays = re.findall(r'var\s+\w+\s*=\s*\[\d+,\d+,\d+,\d+', code)
    return len(large_arrays) >= 6


def _decode_dhiraj9619_generic(code: str) -> str:
    """
    Generic DHIRAJ9619 cipher decoder — works with ANY variable names.
    Traces the state machine to discover the operation sequence, then
    executes: INIT → XOR → BLOCK_REORDER → SBOX → XOR → SUBTRACT →
               CHAIN_XOR → BIT_ROTATE → BLOCK_REORDER → SBOX → RC4 → OUTPUT
    """
    try:
        arrays = {}
        for m in re.finditer(r'var\s+(\w+)\s*=\s*\[(-?\d+(?:,\s*-?\d+)*)\]', code):
            name = m.group(1)
            try:
                vals = [int(x.strip()) for x in m.group(2).split(',')
                        if x.strip().lstrip('-').isdigit()]
                if len(vals) >= 16:
                    arrays[name] = vals
            except Exception:
                pass

        if not arrays:
            return ''

        out_m = re.search(
            r'for\s*\(\s*(\w+)\s*=\s*0\s*;\s*\1\s*<\s*(\d+)\s*;[^)]*\)\s*\{'
            r'[^}]*String\.fromCharCode\s*\(\s*(\w+)\s*\[\1\]\s*\)',
            code
        )
        if not out_m:
            return ''

        out_len = int(out_m.group(2))
        data_var = out_m.group(3)
        dv = re.escape(data_var)

        out_pos = out_m.start()
        ctx = code[max(0, out_pos - 300): out_pos + 600]
        sv_m = re.search(r'(\w+)\s*=\s*\([^)]+\)\s*\?\s*\d+\s*:\s*\d+', ctx)
        if not sv_m:
            return ''
        switch_var = sv_m.group(1)
        sv = re.escape(switch_var)

        init_m = re.search(rf'var\s+{sv}\s*=\s*(\d+)', code)
        if not init_m:
            return ''
        init_val = int(init_m.group(1))

        cases = {}
        for m in re.finditer(r'case\s+(\d+)\s*:(.*?)(?=case\s+\d+\s*:|$)', code, re.DOTALL):
            cases[int(m.group(1))] = m.group(2)

        def get_next(body):
            # DHIRAJ9619 case numbers are always large (5+ digits).
            # Searching for ?CASE_A:CASE_B avoids parsing conditions that
            # contain ';' (e.g. (function(){return true;}())?N:M).
            m = re.search(r'\?\s*(\d{5,})\s*:\s*\d{5,}', body)
            if m:
                return int(m.group(1))
            # Direct assignment without ternary
            m = re.search(rf'{sv}\s*=\s*(\d+)\s*;', body)
            if m:
                return int(m.group(1))
            return None

        def classify(body):
            init_c = re.search(rf'{dv}\s*=\s*(\w+)\.concat\s*\(([^)]+)\)', body)
            if init_c:
                first = init_c.group(1)
                rest_raw = [x.strip().split('[')[0].strip()
                            for x in init_c.group(2).split(',')]
                all_arrs = [first] + rest_raw
                valid = [a for a in all_arrs if a in arrays]
                if valid:
                    return ('init', valid)

            xor_m = re.search(rf'{dv}\s*\[\w+\]\s*\^=\s*(\w+)\[', body)
            if xor_m and xor_m.group(1) in arrays:
                return ('xor', xor_m.group(1))

            chain_m = re.search(rf'{dv}\s*\[\w+\]\s*\^=\s*(\w+)(?!\[)', body)
            if chain_m:
                prev_var = chain_m.group(1)
                seed_m = re.search(rf'{re.escape(prev_var)}\s*=\s*(\d{{1,3}})\s*;', body)
                if seed_m and 0 < int(seed_m.group(1)) < 256:
                    return ('chain_xor', int(seed_m.group(1)))

            sub_m = re.search(
                rf'{dv}\s*\[\w+\]\s*=\s*\(\s*{dv}\s*\[\w+\]\s*-\s*(\w+)\[', body
            )
            if sub_m and sub_m.group(1) in arrays:
                return ('subtract', sub_m.group(1))

            sbox_m = re.search(
                rf'{dv}\s*\[\w+\]\s*=\s*(\w+)\[\s*{dv}\s*\[\w+\]\s*\]', body
            )
            if sbox_m:
                sn = sbox_m.group(1)
                if sn in arrays and len(arrays[sn]) == 256:
                    return ('sbox', sn)

            br_m = re.search(
                r'\w+\s*\[\s*\w+\s*\*\s*16\s*\+\s*\w+\s*\]\s*=\s*'
                + dv + r'\s*\[\s*(\w+)\s*\[',
                body
            )
            if br_m and br_m.group(1) in arrays:
                return ('block_reorder', br_m.group(1))

            if ('&7' in body or '& 7' in body) and '<<' in body and data_var in body:
                if '>>' in body and '8' in body:
                    return ('bit_rotate', None)

            if re.search(r'new\s+Array\s*\(\s*256\s*\)', body) and data_var in body:
                rc4_key_m = re.search(r'(\w+)\s*\[\s*\w+\s*%\s*(\w+)\.length\s*\]', body)
                if rc4_key_m:
                    kn = rc4_key_m.group(2)
                    if kn in arrays and len(arrays[kn]) == 32:
                        return ('rc4', kn)

            return (None, None)

        operations = []
        visited = set()
        cur = init_val

        for _ in range(400):
            if cur not in cases or cur in visited:
                break
            visited.add(cur)
            body = cases[cur]

            if 'String.fromCharCode' in body and data_var in body:
                break

            op_type, op_arg = classify(body)
            if op_type is not None:
                operations.append((op_type, op_arg))

            nxt = get_next(body)
            if nxt is None:
                break
            cur = nxt

        if not operations:
            return ''

        data = None
        cipher_ops = []
        for op_type, op_arg in operations:
            if op_type == 'init':
                parts = []
                for aname in op_arg:
                    if aname in arrays:
                        parts.extend(arrays[aname])
                if parts:
                    data = bytearray(parts)
            else:
                cipher_ops.append((op_type, op_arg))

        if data is None:
            return ''

        total_len = len(data)

        for op_type, op_arg in cipher_ops:
            if op_type == 'xor':
                key = arrays[op_arg]
                klen = len(key)
                for i in range(total_len):
                    data[i] ^= key[i % klen]

            elif op_type == 'subtract':
                key = arrays[op_arg]
                klen = len(key)
                for i in range(total_len):
                    data[i] = (data[i] - key[i % klen] + 256) & 255

            elif op_type == 'sbox':
                sb = arrays[op_arg]
                for i in range(total_len):
                    data[i] = sb[data[i]]

            elif op_type == 'block_reorder':
                idx = arrays[op_arg]
                n_blocks = len(idx)
                tmp = bytearray(total_len)
                for b in range(n_blocks):
                    src = idx[b] * 16
                    dst = b * 16
                    if src + 16 <= total_len and dst + 16 <= total_len:
                        tmp[dst:dst + 16] = data[src:src + 16]
                data = tmp

            elif op_type == 'chain_xor':
                prev = op_arg
                for i in range(total_len):
                    orig = data[i]
                    data[i] = orig ^ prev
                    prev = orig

            elif op_type == 'bit_rotate':
                for i in range(total_len):
                    r = i & 7
                    if r > 0:
                        data[i] = ((data[i] >> r) | (data[i] << (8 - r))) & 255

            elif op_type == 'rc4':
                data = _rc4(data, arrays[op_arg])

        raw = bytes(data[:out_len])
        try:
            result = raw.decode('utf-8')
        except Exception:
            try:
                latin = raw.decode('latin-1')
                try:
                    result = latin.encode('latin-1').decode('utf-8')
                except Exception:
                    result = latin
            except Exception:
                result = raw.decode('utf-8', errors='replace')

        return result

    except Exception:
        return ''


def _try_htmlobfuscatebot(code: str) -> str:
    """
    Decode @HTMLObfuscateBot / DHIRAJ9619_HTMLOBF_PROTECTED style obfuscation.
    Works with ANY variable names via generic state-machine tracing.

    Returns a clean single HTML file:
      - The visible HTML structure as the page skeleton
      - The full decoded JS logic embedded as a <script> tag
    """
    has_specific = ('DHIRAJ9619_HTMLOBF_PROTECTED' in code or
                    '_RWcZroasWtEaG' in code)
    has_generic = _detect_dhiraj9619_generic(code)

    if not has_specific and not has_generic:
        return ''

    plain_html = _extract_nonscript_html(code)

    js_logic = ''

    if has_generic:
        js_logic = _decode_dhiraj9619_generic(code)
        if not js_logic:
            for s in re.findall(r'<script[^>]*>([\s\S]*?)</script>', code, re.IGNORECASE):
                if _detect_dhiraj9619_generic(s):
                    js_logic = _decode_dhiraj9619_generic(s)
                    if js_logic:
                        break

    if not js_logic and has_specific:
        scripts = re.findall(r'<script[^>]*>([\s\S]*?)</script>', code, re.IGNORECASE)
        cipher_src = code
        for s in scripts:
            if '_RWcZroasWtEaG' in s or '_jiLr865KTovCK' in s:
                cipher_src = s
                break
        js_logic = _run_dhiraj9619_cipher(cipher_src)
        if not js_logic:
            js_logic = _run_dhiraj9619_cipher(code)

    if not plain_html and not js_logic:
        return ''

    if plain_html and js_logic:
        script_block = f'\n<script>\n{js_logic}\n</script>\n'
        if '</body>' in plain_html:
            return plain_html.replace('</body>', script_block + '</body>', 1)
        elif '</html>' in plain_html:
            return plain_html.replace('</html>', script_block + '</html>', 1)
        else:
            return plain_html + script_block
    elif js_logic:
        return js_logic
    else:
        return plain_html


def _js_template_unescape(s: str) -> str:
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            nc = s[i + 1]
            if nc == '\\':
                result.append('\\'); i += 2
            elif nc == '"':
                result.append('"'); i += 2
            elif nc == "'":
                result.append("'"); i += 2
            elif nc == 'n':
                result.append('\n'); i += 2
            elif nc == 'r':
                result.append('\r'); i += 2
            elif nc == 't':
                result.append('\t'); i += 2
            elif nc == '`':
                result.append('`'); i += 2
            elif nc == '0':
                result.append('\0'); i += 2
            else:
                result.append(s[i]); i += 1
        else:
            result.append(s[i]); i += 1
    return ''.join(result)


def _phpkobo_stream_decode(srkpv: str) -> str:
    b_idx = srkpv.find('B')
    if b_idx < 0:
        return ''
    srkpv = srkpv[b_idx + 1:]
    if len(srkpv) < 9:
        return ''
    yl_rf = srkpv[-8:]
    try:
        step  = int(yl_rf[4:6], 16)
        start = int(yl_rf[6:8], 16)
    except ValueError:
        return ''
    srkpv = srkpv[:-8]
    srkpv = re.sub(r'X', 'E', srkpv, flags=re.IGNORECASE)
    srkpv = re.sub(r'Y', 'A', srkpv, flags=re.IGNORECASE)
    srkpv = re.sub(r'Z', 'C', srkpv, flags=re.IGNORECASE)
    srkpv = re.sub(r'[^0-9a-fA-F]', '0', srkpv).lower()
    pairs = [srkpv[i:i+2] for i in range(0, len(srkpv) - 1, 2)]
    wm_ged = [0] * 256
    j = start
    for i in range(256):
        wm_ged[j] = i
        j = (j + step) % 256
    hc = '0123456789abcdef'
    result_parts = []
    for idx, pair in enumerate(pairs):
        try:
            raw_val = int(pair, 16)
        except ValueError:
            raw_val = 0
        decoded = (raw_val - wm_ged[idx % 256] + 256) % 256
        result_parts.append('%' + hc[(decoded >> 4) & 0xF] + hc[decoded & 0xF])
    try:
        return urllib.parse.unquote(''.join(result_parts), encoding='utf-8')
    except Exception:
        return ''


def _phpkobo_extract_and_decode(source: str) -> str:
    chunks = source.split('\u200b')
    if len(chunks) < 3:
        return ''
    chunk2 = chunks[2]
    for unescape_passes in range(3):
        candidate = chunk2
        for _ in range(unescape_passes + 1):
            candidate = _js_template_unescape(candidate)
        m = re.search(r'_L55c0Y\._Srkpv\s*=\s*"([^"]{100,})"', candidate)
        if m:
            srkpv = m.group(1)
            result = _phpkobo_stream_decode(srkpv)
            if result and _is_html_or_clean(result):
                return result
        idx = candidate.find('_Srkpv=\\"')
        if idx >= 0:
            start = idx + len('_Srkpv=\\"')
            end = candidate.find('\\"', start)
            if end > start:
                srkpv = candidate[start:end]
                result = _phpkobo_stream_decode(srkpv)
                if result and _is_html_or_clean(result):
                    return result
    return ''


def _try_phpkobo(code: str) -> str:
    if '_L55c0Y' in code or 'CHEETAH112' in code:
        result = _phpkobo_extract_and_decode(code)
        if result:
            return result
    sec_patterns = [
        r'var\s+\w+\s*=\s*"([A-Za-z0-9+/=]{20,})"[\s\S]{0,500}?(?:decodeURIComponent|window\.atob|atob|escape)',
        r'var\s+_sec\s*=\s*"([A-Za-z0-9+/=]{20,})"',
        r'var\s+\w+\s*=\s*"([A-Za-z0-9+/=]{80,})"',
    ]
    seen_b64 = set()
    for pat in sec_patterns:
        for m in re.finditer(pat, code, re.DOTALL):
            b64 = m.group(1)
            if b64 in seen_b64:
                continue
            seen_b64.add(b64)
            inner = _atob_decode(b64)
            if not inner or len(inner) < 10:
                continue
            if '_L55c0Y' in inner or 'CHEETAH112' in inner:
                result = _phpkobo_extract_and_decode(inner)
                if result:
                    return result
            if _is_html_or_clean(inner) and len(inner) > 50:
                return inner
    return ''


def _try_document_write(code: str) -> str:
    for pat in [
        r'document\s*\.\s*write\s*\(\s*decodeURIComponent\s*\(\s*escape\s*\(\s*(?:window\s*\.\s*)?atob\s*\(\s*["\']([A-Za-z0-9+/=]{20,})["\']',
        r'document\s*\.\s*write\s*\(\s*decodeURIComponent\s*\(\s*(?:window\s*\.\s*)?atob\s*\(\s*["\']([A-Za-z0-9+/=]{20,})["\']',
        r'document\s*\.\s*write\s*\(\s*(?:window\s*\.\s*)?atob\s*\(\s*["\']([A-Za-z0-9+/=]{20,})["\']',
        r'document\s*\.\s*write\s*\(\s*atob\s*\(\s*["\']([A-Za-z0-9+/=]{20,})["\']',
    ]:
        m = re.search(pat, code, re.DOTALL | re.IGNORECASE)
        if m:
            decoded = _atob_decode(m.group(1))
            if decoded and _looks_like_code(decoded):
                return decoded
    m = re.search(
        r'document\s*\.\s*write\s*\(\s*unescape\s*\(\s*["\']([%0-9a-fA-Fu]+)["\']',
        code, re.IGNORECASE
    )
    if m:
        try:
            decoded = urllib.parse.unquote(m.group(1))
            if decoded and _looks_like_code(decoded):
                return decoded
        except Exception:
            pass
    m = re.search(
        r'document\s*\.\s*write\s*\(\s*decodeURIComponent\s*\(\s*["\']([%0-9a-zA-Z+]{20,})["\']',
        code, re.IGNORECASE
    )
    if m:
        try:
            decoded = urllib.parse.unquote(m.group(1))
            if decoded and _looks_like_code(decoded):
                return decoded
        except Exception:
            pass
    return ''


def _try_packer(code: str) -> str:
    m = re.search(
        r"""eval\s*\(\s*function\s*\(\s*p\s*,\s*a\s*,\s*c\s*,\s*k\s*,\s*e\s*,\s*[dr]\s*\)"""
        r""".*?}\s*\(\s*'(.*?)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'(.*?)'\.split\s*\(\s*'[|]'\s*\)""",
        code, re.DOTALL
    )
    if not m:
        return ''
    packed   = m.group(1)
    base     = int(m.group(2))
    keywords = m.group(4).split('|')

    def _lookup(word: str) -> str:
        try:
            idx = int(word, base) if base <= 36 else int(word, 36)
            return keywords[idx] if idx < len(keywords) and keywords[idx] else word
        except Exception:
            return word

    result = re.sub(r'\b(\w+)\b', lambda mo: _lookup(mo.group(0)), packed)
    if result and _looks_like_code(result):
        return result
    return ''


def _try_js_0x_strings(code: str) -> str:
    if '_0x' not in code and '\\x' not in code:
        return ''
    result = re.sub(r'\\x([0-9a-fA-F]{2})',
                    lambda m: chr(int(m.group(1), 16)), code)
    result = re.sub(r'\\u([0-9a-fA-F]{4})',
                    lambda m: chr(int(m.group(1), 16)), result)
    if result == code:
        return ''
    if len(result) > 50 and _looks_like_code(result):
        return result
    return ''


def _try_js_advanced_eval(code: str) -> str:
    patterns = [
        r'[\'"]([A-Za-z0-9+/=]{150,})[\'"]',
        r'(?:var|const|let)\s+\w+\s*=\s*\[\s*[\'"]([A-Za-z0-9+/=]{50,})[\'"]\s*\]'
    ]
    for pat in patterns:
        for m in re.finditer(pat, code, re.DOTALL):
            decoded = _atob_decode(m.group(1))
            if decoded and _looks_like_code(decoded) and len(decoded) > len(m.group(1)) * 0.5:
                return decoded
    return ''


def _try_phpkodo(code: str) -> str:
    patterns = [
        (
            r"""str_rot13\s*\(\s*gzinflate\s*\(\s*str_rot13\s*\(\s*base64_decode\s*\(\s*['"]([^'"]+)['"]\s*\)\s*\)\s*\)\s*\)""",
            lambda b: _rot13_bytes(_inflate(_rot13_bytes(b)))
        ),
        (
            r"""gzinflate\s*\(\s*str_rot13\s*\(\s*base64_decode\s*\(\s*['"]([^'"]+)['"]\s*\)\s*\)\s*\)""",
            lambda b: _inflate(_rot13_bytes(b))
        ),
        (
            r"""gzinflate\s*\(\s*base64_decode\s*\(\s*['"]([^'"]+)['"]\s*\)\s*\)""",
            lambda b: _inflate(b)
        ),
        (
            r"""gzuncompress\s*\(\s*base64_decode\s*\(\s*['"]([^'"]+)['"]\s*\)\s*\)""",
            lambda b: _inflate(b)
        ),
        (
            r"""gzdecode\s*\(\s*base64_decode\s*\(\s*['"]([^'"]+)['"]\s*\)\s*\)""",
            lambda b: _inflate(b)
        ),
        (
            r"""str_rot13\s*\(\s*base64_decode\s*\(\s*['"]([^'"]+)['"]\s*\)\s*\)""",
            lambda b: _rot13_bytes(b)
        ),
        (
            r"""base64_decode\s*\(\s*['"]([A-Za-z0-9+/\r\n]{20,}={0,2})['"]\s*\)""",
            lambda b: b
        ),
    ]
    for pattern, transform in patterns:
        for m in re.finditer(pattern, code, re.DOTALL):
            raw = _b64_decode(m.group(1))
            if not raw:
                continue
            result = transform(raw)
            if result:
                decoded = _to_str(result)
                if _looks_like_code(decoded):
                    return decoded
    return ''


def _try_phpcabbo(code: str) -> str:
    var_assignments = re.findall(
        r'\$(\w+)\s*=\s*["\']([A-Za-z0-9+/\r\n]{30,}={0,2})["\']',
        code
    )
    for var_name, b64_val in var_assignments:
        raw = _b64_decode(b64_val)
        if raw:
            decoded = _to_str(raw)
            if _looks_like_code(decoded):
                return decoded
    m = re.search(
        r'\$\w+\s*=\s*base64_decode\s*\(\s*["\']([A-Za-z0-9+/\r\n=]+)["\']\s*\)\s*;',
        code
    )
    if m:
        raw = _b64_decode(m.group(1))
        if raw:
            d = _to_str(raw)
            if d:
                return d
    m = re.search(
        r'''preg_replace\s*\(\s*['"][^'"]*e[^'"]*['"]\s*,\s*base64_decode\s*\(\s*['"]([^'"]+)['"]\s*\)''',
        code
    )
    if m:
        raw = _b64_decode(m.group(1))
        if raw:
            return _to_str(raw)
    m = re.search(r'(?:chr\s*\(\s*\d+\s*\)\s*\.?\s*){5,}', code)
    if m:
        chars = re.findall(r'chr\s*\(\s*(\d+)\s*\)', m.group(0))
        if chars:
            try:
                return ''.join(chr(int(c)) for c in chars)
            except Exception:
                pass
    return ''


def _try_js_obfuscation(code: str) -> str:
    for pat in [
        r"""eval\s*\(\s*atob\s*\(\s*['"]([A-Za-z0-9+/=]{20,})['"]\s*\)\s*\)""",
        r"""eval\s*\(\s*window\.atob\s*\(\s*['"]([A-Za-z0-9+/=]{20,})['"]\s*\)\s*\)""",
    ]:
        m = re.search(pat, code, re.DOTALL)
        if m:
            decoded = _atob_decode(m.group(1))
            if decoded and _looks_like_code(decoded):
                return decoded
    for pat in [
        r"""eval\s*\(\s*unescape\s*\(\s*['"]([^'"]{20,})['"]\s*\)\s*\)""",
        r"""eval\s*\(\s*decodeURIComponent\s*\(\s*['"]([^'"]{20,})['"]\s*\)\s*\)""",
    ]:
        m = re.search(pat, code, re.DOTALL)
        if m:
            try:
                d = urllib.parse.unquote(m.group(1))
                if d and d != m.group(1) and _looks_like_code(d):
                    return d
            except Exception:
                pass
    for pat in [
        r'String\.fromCharCode\s*\(([\d,\s]{10,})\)',
        r'(?:eval|write|innerHTML)\s*\(\s*String\.fromCharCode\s*\(([\d,\s]+)\)',
    ]:
        m = re.search(pat, code)
        if m:
            try:
                chars = [int(c.strip()) for c in m.group(1).split(',') if c.strip()]
                if chars:
                    result = ''.join(chr(c) for c in chars)
                    if _looks_like_code(result):
                        return result
            except Exception:
                pass
    return ''


def _try_raw_base64(code: str) -> str:
    stripped = re.sub(r'\s+', '', code.strip())
    if len(stripped) < 20:
        return ''
    if not re.match(r'^[A-Za-z0-9+/]+=*$', stripped):
        return ''
    raw = _b64_decode(stripped)
    if not raw:
        return ''
    decoded = _to_str(raw)
    if _looks_like_code(decoded):
        return decoded
    inf = _inflate(raw)
    if inf:
        d2 = _to_str(inf)
        if _looks_like_code(d2):
            return d2
    return ''


def _try_html_entities(code: str) -> str:
    decoded = html.unescape(code)
    return decoded if decoded != code else ''


def _try_hex_unicode(code: str) -> str:
    result = re.sub(r'\\x([0-9a-fA-F]{2})',
                    lambda m: chr(int(m.group(1), 16)), code)
    result = re.sub(r'\\u([0-9a-fA-F]{4})',
                    lambda m: chr(int(m.group(1), 16)), result)
    pct = re.findall(r'%[0-9a-fA-F]{2}', result)
    if len(pct) >= 5:
        result = re.sub(r'%([0-9a-fA-F]{2})',
                        lambda m: chr(int(m.group(1), 16)), result)
    return result if result != code else ''


def _try_url_decode(code: str) -> str:
    if '%' not in code:
        return ''
    if len(re.findall(r'%[0-9a-fA-F]{2}', code)) < 5:
        return ''
    try:
        decoded = urllib.parse.unquote(code)
        if decoded != code:
            return decoded
    except Exception:
        pass
    return ''


def _try_rot13_only(code: str) -> str:
    if 'str_rot13' not in code:
        return ''
    m = re.search(r"str_rot13\s*\(\s*['\"]([^'\"]{20,})['\"]", code)
    if m:
        try:
            return codecs.decode(m.group(1), 'rot_13')
        except Exception:
            pass
    return ''


def _inline_b64_replace(code: str) -> str:
    def replacer(m):
        raw = _b64_decode(m.group(1))
        if raw:
            try:
                return _to_str(raw)
            except Exception:
                pass
        return m.group(0)
    result = re.sub(
        r"""base64_decode\s*\(\s*['"]([A-Za-z0-9+/\r\n=]+)['"]\s*\)""",
        replacer, code, flags=re.DOTALL
    )
    return result if result != code else ''


def _try_octal_decimal_chars(code: str) -> str:
    if re.search(r'\\[0-7]{3}', code):
        result = re.sub(
            r'\\([0-7]{3})',
            lambda m: chr(int(m.group(1), 8)),
            code
        )
        if result != code and _looks_like_code(result):
            return result
    m = re.search(r'(?:chr\s*\(\s*\d+\s*\)[.\s]*){5,}', code)
    if m:
        chars = re.findall(r'chr\s*\(\s*(\d+)\s*\)', code)
        if len(chars) > 5:
            try:
                result = ''.join(chr(int(c)) for c in chars)
                if _looks_like_code(result):
                    return result
            except Exception:
                pass
    return ''


def _top_level_split(content: str, sep: str) -> list:
    """Split content at top-level occurrences of sep (not inside brackets/strings)."""
    parts = []
    depth = 0
    in_str = None
    buf = []
    i = 0
    sep_len = len(sep)
    while i < len(content):
        c = content[i]
        if in_str:
            buf.append(c)
            if c == '\\':
                i += 1
                if i < len(content):
                    buf.append(content[i])
            elif c == in_str:
                in_str = None
        elif c in ('"', "'", '`'):
            in_str = c
            buf.append(c)
        elif c in ('(', '[', '{'):
            depth += 1
            buf.append(c)
        elif c in (')', ']', '}'):
            depth -= 1
            buf.append(c)
        elif depth == 0 and content[i:i+sep_len] == sep:
            parts.append(''.join(buf))
            buf = []
            i += sep_len
            continue
        else:
            buf.append(c)
        i += 1
    if buf:
        parts.append(''.join(buf))
    return parts


def _split_long_js_line(line: str, max_len: int = 120) -> str:
    """Split a long JS line at top-level commas or method chains, keeping indent."""
    if len(line) <= max_len:
        return line
    indent = len(line) - len(line.lstrip())
    base_indent = ' ' * indent
    extra_indent = base_indent + '    '
    content = line.strip()

    # Strategy 1: split at top-level commas
    parts = _top_level_split(content, ',')
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) > 1:
        result_lines = [base_indent + parts[0] + ',']
        for p in parts[1:-1]:
            result_lines.append(extra_indent + p + ',')
        result_lines.append(extra_indent + parts[-1])
        joined = '\n'.join(result_lines)
        if max(len(l) for l in joined.split('\n')) <= max_len:
            return joined
        # Even after comma split some lines are long — recurse once
        final = []
        for l in joined.split('\n'):
            if len(l) > max_len:
                final.append(_split_at_method_chain(l, max_len))
            else:
                final.append(l)
        return '\n'.join(final)

    # Strategy 2: split at method chains (.method()
    return _split_at_method_chain(line, max_len)


def _split_at_method_chain(line: str, max_len: int = 120) -> str:
    """Split a long line at top-level .methodName( chains."""
    if len(line) <= max_len:
        return line
    indent = len(line) - len(line.lstrip())
    base_indent = ' ' * indent
    extra_indent = base_indent + '    '
    content = line.strip()

    # Find positions of top-level .word( patterns
    depth = 0
    in_str = None
    split_positions = []
    i = 0
    while i < len(content):
        c = content[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            elif c == in_str:
                in_str = None
        elif c in ('"', "'", '`'):
            in_str = c
        elif c in ('(', '[', '{'):
            depth += 1
        elif c in (')', ']', '}'):
            depth -= 1
        elif c == '.' and depth == 0 and i > 0:
            # Check it's a method call: .word(
            m = re.match(r'\.[a-zA-Z_$][a-zA-Z0-9_$]*\s*\(', content[i:])
            if m:
                split_positions.append(i)
        i += 1

    if not split_positions:
        return line  # Nothing we can do

    # Split at the best positions (where line would exceed max_len)
    result_lines = []
    prev = 0
    current_indent = base_indent
    for pos in split_positions:
        segment = content[prev:pos]
        if prev == 0:
            candidate = current_indent + segment
        else:
            candidate = extra_indent + segment
        if len(candidate) > max_len and result_lines:
            result_lines.append(candidate)
            current_indent = extra_indent
        else:
            result_lines.append(candidate)
        prev = pos

    # Last segment
    last = content[prev:]
    if result_lines:
        result_lines[-1] = result_lines[-1] + last
    else:
        result_lines.append(base_indent + last)

    return '\n'.join(result_lines)


def _post_split_long_lines(js_code: str, max_len: int = 120) -> str:
    """Post-process JS: split any remaining lines longer than max_len."""
    result = []
    for line in js_code.split('\n'):
        if len(line) > max_len:
            result.append(_split_long_js_line(line, max_len))
        else:
            result.append(line)
    return '\n'.join(result)


def _js_beautify(js_code: str) -> str:
    """Beautify/format JavaScript code using jsbeautifier + long-line splitter."""
    try:
        import jsbeautifier
        opts = jsbeautifier.default_options()
        opts.indent_size = 4
        opts.indent_char = ' '
        opts.max_preserve_newlines = 2
        opts.preserve_newlines = True
        opts.keep_array_indentation = False
        opts.break_chained_methods = False
        opts.space_in_paren = False
        opts.jslint_happy = False
        opts.end_with_newline = True
        opts.wrap_line_length = 0
        opts.comma_first = False
        opts.e4x = False
        opts.unescape_strings = False
        beautified = jsbeautifier.beautify(js_code, opts)
        # Second pass: split any remaining long lines
        return _post_split_long_lines(beautified, max_len=120)
    except Exception:
        return js_code


def _css_beautify(css_code: str) -> str:
    """Beautify/format CSS code using cssbeautifier."""
    try:
        import cssbeautifier
        opts = cssbeautifier.default_options()
        opts.indent_size = 4
        opts.indent_char = ' '
        opts.end_with_newline = True
        opts.indent_with_tabs = False
        opts.eol = '\n'
        opts.newline_between_rules = True
        return cssbeautifier.beautify(css_code, opts)
    except Exception:
        # Fallback: simple manual CSS formatter
        return _css_format_fallback(css_code)


def _css_format_fallback(css: str) -> str:
    """Simple fallback CSS formatter without external dependencies."""
    result = []
    indent = ''
    i = 0
    css = css.strip()
    while i < len(css):
        c = css[i]
        if c == '{':
            result.append(' {\n')
            indent = '    '
            i += 1
        elif c == '}':
            indent = ''
            result.append('\n}\n\n')
            i += 1
        elif c == ';':
            result.append(';\n' + indent)
            i += 1
        elif c == ',':
            # In selectors (before {), add newline; in values, keep as is
            # Heuristic: if next non-space char is not a CSS property char
            result.append(',\n')
            i += 1
        else:
            result.append(c)
            i += 1
    return ''.join(result).strip()


def _html_beautify(html_content: str) -> str:
    """Beautify HTML with 4-space indent, inline text on same line, HTML5 void tags."""
    try:
        from bs4 import BeautifulSoup

        VOID_TAGS = {
            'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr',
        }
        INLINE_TEXT_TAGS = {
            'title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'li', 'td', 'th', 'dt', 'dd', 'caption', 'figcaption',
            'legend', 'label', 'button', 'a', 'span', 'strong', 'em',
            'b', 'i', 'small', 'code', 'abbr', 'cite', 'mark', 'q',
            's', 'del', 'ins', 'time', 'u', 'sub', 'sup',
        }

        soup = BeautifulSoup(html_content, 'html.parser')

        # ── Step 1: Pull script/style bodies out as placeholders so BS4
        #    doesn't mangle them, then restore after prettify.
        script_store: dict = {}
        style_store: dict  = {}

        for idx, tag in enumerate(soup.find_all('script')):
            body = tag.string or ''
            if len(body.strip()) >= 10:
                script_store[idx] = body
                tag.string = f'__SCRIPT_{idx}__'

        for idx, tag in enumerate(soup.find_all('style')):
            body = tag.string or ''
            if len(body.strip()) >= 5:
                style_store[idx] = body
                tag.string = f'__STYLE_{idx}__'

        # ── Step 2: BS4 prettify (1-space indent by default)
        pretty = soup.prettify()

        # ── Step 3: Convert 1-space indent → 4-space indent
        out_lines = []
        for line in pretty.split('\n'):
            stripped = line.lstrip(' ')
            num_sp = len(line) - len(stripped)
            out_lines.append(' ' * (num_sp * 4) + stripped)
        pretty = '\n'.join(out_lines)

        # ── Step 3b: Dedent by one level — html/head/body sit at col 0
        #   (BS4 indents children of <html> by 1, so after ×4 they are at 4.
        #    Subtract 4 from every indented line so head/body land at col 0.)
        dedented = []
        for line in pretty.split('\n'):
            if line.startswith('    '):
                dedented.append(line[4:])
            else:
                dedented.append(line)
        pretty = '\n'.join(dedented)

        # ── Step 4: Fix void elements — remove self-closing slash (HTML5)
        for vtag in VOID_TAGS:
            pretty = re.sub(
                rf'(<{vtag}(?:\s[^>]*)?)\s*/>',
                r'\1>',
                pretty,
                flags=re.IGNORECASE,
            )

        # ── Step 5: Collapse simple inline-text tags to one line
        #   Before:  <title>\n        GOD FATHER AI\n    </title>
        #   After:   <title>GOD FATHER AI</title>
        def _collapse_inline(m):
            open_tag = m.group(1)
            text     = m.group(2).strip()
            close    = m.group(3)   # already includes </...>
            if len(text) < 120 and '\n' not in text and '<' not in text:
                return f'{open_tag}{text}{close}'
            return m.group(0)

        tag_pat = '|'.join(INLINE_TEXT_TAGS)
        pretty = re.sub(
            rf'(<(?:{tag_pat})[^>]*>)\s*\n\s*([^\n<]*)\n\s*(</[a-zA-Z0-9]+>)',
            _collapse_inline,
            pretty,
            flags=re.IGNORECASE,
        )

        # ── Step 6: Restore <script> blocks with jsbeautifier output,
        #    indented to match the tag's own indentation level.
        def _restore_script(m):
            full = m.group(0)
            pm = re.search(r'__SCRIPT_(\d+)__', full)
            if pm is None:
                return full
            idx = int(pm.group(1))
            original = script_store.get(idx, '')
            beautified = _js_beautify(original.strip())
            # detect tag indentation from first line
            first_line = full.split('\n')[0]
            base_ind = ' ' * (len(first_line) - len(first_line.lstrip()))
            cont_ind = base_ind + '    '
            indented = '\n'.join(
                cont_ind + ln if ln.strip() else ''
                for ln in beautified.split('\n')
            )
            attr_m = re.search(r'<script([^>]*)>', full, re.IGNORECASE)
            attrs = attr_m.group(1) if attr_m else ''
            return f'{base_ind}<script{attrs}>\n{indented}\n{base_ind}</script>'

        pretty = re.sub(
            r'^( *)<script[^>]*>[\s\S]*?</script>',
            _restore_script,
            pretty,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        # ── Step 7: Restore <style> blocks with cssbeautifier output,
        #    indented to match the tag's own indentation level.
        def _restore_style(m):
            full = m.group(0)
            pm = re.search(r'__STYLE_(\d+)__', full)
            if pm is None:
                return full
            idx = int(pm.group(1))
            original = style_store.get(idx, '')
            beautified = _css_beautify(original.strip())
            first_line = full.split('\n')[0]
            base_ind = ' ' * (len(first_line) - len(first_line.lstrip()))
            cont_ind = base_ind + '    '
            indented = '\n'.join(
                cont_ind + ln if ln.strip() else ''
                for ln in beautified.split('\n')
            )
            attr_m = re.search(r'<style([^>]*)>', full, re.IGNORECASE)
            attrs = attr_m.group(1) if attr_m else ''
            return f'{base_ind}<style{attrs}>\n{indented}\n{base_ind}</style>'

        pretty = re.sub(
            r'^( *)<style[^>]*>[\s\S]*?</style>',
            _restore_style,
            pretty,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        return pretty

    except Exception:
        return html_content


def _decode_scripts_in_html(html_content: str, log: list) -> str:
    """
    Find all <script> tags inside decoded HTML and try to decode
    any obfuscated JS within them. Uses regex — safe from BS4 mutation issues.
    """
    changed = False

    def _process_script(m):
        nonlocal changed
        attrs = m.group(1) or ''
        js = m.group(2)
        if not js or len(js.strip()) < 30:
            return m.group(0)

        decoded_js = js

        # Try packer
        r = _try_packer(decoded_js)
        if r and r != decoded_js:
            decoded_js = r
            log.append("  ↳ Nested script: Dean Edwards packer decoded")
            changed = True

        # Try eval(atob...) patterns
        r = _try_js_obfuscation(decoded_js)
        if r and r != decoded_js:
            decoded_js = r
            log.append("  ↳ Nested script: JS eval/atob decoded")
            changed = True

        # Try hex/unicode escapes
        r = _try_hex_unicode(decoded_js)
        if r and r != decoded_js:
            decoded_js = r
            log.append("  ↳ Nested script: Hex/Unicode escapes decoded")
            changed = True

        # Try _0x obfuscation
        r = _try_js_0x_strings(decoded_js)
        if r and r != decoded_js:
            decoded_js = r
            log.append("  ↳ Nested script: _0x string obfuscation decoded")
            changed = True

        # Try document.write payload
        r = _try_document_write(decoded_js)
        if r and r != decoded_js:
            decoded_js = r
            log.append("  ↳ Nested script: document.write payload extracted")
            changed = True

        return f'<script{attrs}>{decoded_js}</script>'

    result = re.sub(
        r'<script([^>]*)>([\s\S]*?)</script>',
        _process_script,
        html_content,
        flags=re.IGNORECASE
    )
    return result


def _is_html_content(s: str) -> bool:
    """Check if content looks like HTML."""
    s_lower = s[:500].lower()
    return any(t in s_lower for t in ['<!doctype', '<html', '<head', '<body', '<div', '<script'])


def full_decode(content: str, max_layers: int = 25) -> tuple:
    current = content
    log = []

    for layer in range(1, max_layers + 1):
        r = _try_htmlobfuscatebot(current)
        if r:
            log.append(f"[Layer {layer}] @HTMLObfuscateBot (DHIRAJ9619) cipher decoded")
            current = r
            continue

        r = _try_phpkobo(current)
        if r:
            log.append(f"[Layer {layer}] PHPKobo HTML obfuscator")
            current = r
            continue

        r = _try_document_write(current)
        if r:
            log.append(f"[Layer {layer}] document.write pattern extracted")
            current = r
            continue

        r = _try_packer(current)
        if r:
            log.append(f"[Layer {layer}] Dean Edwards packer")
            current = r
            continue

        r = _try_js_advanced_eval(current)
        if r:
            log.append(f"[Layer {layer}] Hidden JS Array/Literal Payload extracted")
            current = r
            continue

        r = _try_phpkodo(current)
        if r:
            log.append(f"[Layer {layer}] PHP eval chain (gzinflate/rot13/base64)")
            current = r
            continue

        r = _try_phpcabbo(current)
        if r:
            log.append(f"[Layer {layer}] PHPCabbo variable obfuscation")
            current = r
            continue

        r = _try_js_obfuscation(current)
        if r:
            log.append(f"[Layer {layer}] JS eval/atob/fromCharCode")
            current = r
            continue

        r = _try_js_0x_strings(current)
        if r:
            log.append(f"[Layer {layer}] JS _0x hex string obfuscation")
            current = r
            continue

        r = _try_raw_base64(current)
        if r:
            log.append(f"[Layer {layer}] Raw Base64 blob")
            current = r
            continue

        r = _try_html_entities(current)
        if r:
            log.append(f"[Layer {layer}] HTML entities")
            current = r
            continue

        r = _try_hex_unicode(current)
        if r:
            log.append(f"[Layer {layer}] Hex/Unicode escapes")
            current = r
            continue

        r = _try_url_decode(current)
        if r:
            log.append(f"[Layer {layer}] URL encoding (%XX)")
            current = r
            continue

        r = _try_rot13_only(current)
        if r:
            log.append(f"[Layer {layer}] str_rot13 (standalone)")
            current = r
            continue

        r = _try_octal_decimal_chars(current)
        if r:
            log.append(f"[Layer {layer}] Octal/decimal char escapes")
            current = r
            continue

        r = _inline_b64_replace(current)
        if r:
            log.append(f"[Layer {layer}] Inline base64_decode() replacements")
            current = r
            continue

        break

    if not log:
        unescaped = html.unescape(content)
        if unescaped != content:
            current = unescaped
            log.append("HTML entities decoded (minimal)")
        else:
            log.append("কোনো obfuscation পাওয়া যায়নি (plain content)")

    # ── Post-processing: decode nested scripts + beautify ──────────────────
    if _is_html_content(current):
        # Step 1: Try to decode any obfuscated <script> blocks inside the HTML
        nested_log: list = []
        current = _decode_scripts_in_html(current, nested_log)
        if nested_log:
            log.extend(nested_log)
            log.append("✅ Nested scripts decoded")

        # Step 2: Beautify/format the entire HTML (includes JS in <script> tags)
        try:
            beautified = _html_beautify(current)
            if beautified and len(beautified) > 50:
                current = beautified
                log.append("✅ HTML + JS beautified (proper indentation)")
        except Exception:
            pass
    else:
        # Pure JS file — just beautify
        try:
            beautified = _js_beautify(current)
            if beautified and beautified != current:
                current = beautified
                log.append("✅ JS code beautified")
        except Exception:
            pass

    return current, log
