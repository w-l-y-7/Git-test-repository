# -*- coding: utf-8 -*-
import requests

def get_quote(code):
    url = f"https://qt.gtimg.cn/q={code}"
    r = requests.get(url, timeout=15)
    r.encoding = "gbk"
    seg = r.text.split("~")
    if len(seg) < 45:
        return None
    return dict(name=seg[1], code=seg[2], price=float(seg[3]),
                prev=float(seg[4]), pct=float(seg[32]),
                high=float(seg[33]), low=float(seg[34]),
                vol_wan=seg[6])

stocks = [
    ("sz002185", "华天科技"), ("sh600499", "科达制造"), ("sh601991", "大唐发电"),
    ("sz000021", "深科技"), ("sz002475", "立讯精密"), ("sz000062", "深圳华强"),
    ("sh603416", "信捷电气"), ("sz000063", "中兴通讯"), ("sz002229", "鸿博股份"),
    ("sz000938", "紫光股份"), ("sz002245", "蔚蓝锂芯"),
]

print(f"{'名称':<8}{'代码':<8}{'现价':>8}{'涨跌%':>8}{'最高':>8}{'最低':>8}  100股成本")
for code, _ in stocks:
    q = get_quote(code)
    if not q:
        print(code, "FAILED"); continue
    cost_100 = q["price"] * 100
    print(f"{q['name']:<8}{q['code']:<8}{q['price']:>8.2f}{q['pct']:>8.2f}"
          f"{q['high']:>8.2f}{q['low']:>8.2f}  {cost_100:>9.0f}元")
