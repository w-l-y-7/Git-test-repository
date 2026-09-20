# -*- coding: utf-8 -*-
"""chart_econ.py 的单元测试。

说明：本机没有安装 matplotlib，而 chart_econ.py 一被导入就会画图。
这里用一个"替身"模块顶替掉 matplotlib（不安装任何东西），
这样脚本里真正要验证的东西——实际增速序列、锚点线性插值、统计量——就能被检查到。
图画得好不好看不是单元测试该管的，这里不验证绘图效果。
"""
import sys
import types
import unittest
from pathlib import Path


def _install_fake_matplotlib():
    """在导入 chart_econ 之前，把 matplotlib 换成不会真画图的替身。"""
    if "chart_econ" in sys.modules:
        return

    mpl = types.ModuleType("matplotlib")
    mpl.use = lambda *a, **k: None

    plt = types.ModuleType("matplotlib.pyplot")
    plt.rcParams = {}

    class _Spines:
        def __getitem__(self, key):
            return self

        def set_visible(self, v):
            pass

    class _FakeAx:
        def __init__(self):
            self.spines = _Spines()

        def __getattr__(self, name):
            return lambda *a, **k: None

    class _FakeFig:
        def savefig(self, *a, **k):
            pass

        def text(self, *a, **k):
            pass

    def subplots(*a, **k):
        return _FakeFig(), _FakeAx()

    plt.subplots = subplots
    mpl.pyplot = plt
    sys.modules["matplotlib"] = mpl
    sys.modules["matplotlib.pyplot"] = plt


_install_fake_matplotlib()
import chart_econ  # noqa: E402


class TestActualSeries(unittest.TestCase):
    """实际增速序列（2016-2025）。"""

    def test_years_are_2016_to_2025(self):
        self.assertEqual(chart_econ.actual_years, list(range(2016, 2026)))

    def test_growth_length_matches_years(self):
        self.assertEqual(len(chart_econ.actual_growth), len(chart_econ.actual_years))

    def test_growth_values(self):
        self.assertEqual(
            chart_econ.actual_growth,
            [6.7, 6.9, 6.6, 6.0, 2.2, 8.4, 3.0, 5.2, 5.0, 5.0],
        )

    def test_2020_is_the_low_point(self):
        # 边界：2020 年疫情冲击，数值明显低于其他年份
        idx = chart_econ.actual_years.index(2020)
        self.assertEqual(chart_econ.actual_growth[idx], 2.2)
        self.assertEqual(min(chart_econ.actual_growth), 2.2)

    def test_2021_is_the_high_point(self):
        self.assertEqual(max(chart_econ.actual_growth), 8.4)


class TestForecastInterpolation(unittest.TestCase):
    """2026-2046 情景测算（锚点之间线性插值）。"""

    def test_fy_range(self):
        fy = list(chart_econ.fy)
        self.assertEqual(fy[0], 2025)
        self.assertEqual(fy[-1], 2046)
        self.assertEqual(len(fy), 22)

    def test_knots_pass_through_interpolation(self):
        # 每个锚点年份，插值结果应正好等于锚点给的数值
        fy = list(chart_econ.fy)
        for year, value in chart_econ.knots:
            self.assertAlmostEqual(
                chart_econ.fg[fy.index(year)], value, places=9,
                msg=f"{year} 年插值应等于锚点 {value}",
            )

    def test_first_knot_is_2025_join_point(self):
        # 虚线自 2025 衔接点开始，与实线最后一点（5.0）重合
        self.assertAlmostEqual(chart_econ.fg[0], 5.0, places=9)
        self.assertEqual(chart_econ.fg[0], chart_econ.actual_growth[-1])

    def test_2046_value(self):
        self.assertAlmostEqual(chart_econ.fg[-1], 3.3, places=9)

    def test_midpoint_between_keys(self):
        # 正常输入：2028(4.9) 与 2033(4.5) 之间的中点 2029 应为 4.82
        fy = list(chart_econ.fy)
        self.assertAlmostEqual(chart_econ.fg[fy.index(2029)], 4.82, places=9)
        self.assertAlmostEqual(chart_econ.fg[fy.index(2026)], 4.966666666, places=6)

    def test_monotonic_non_increasing(self):
        # 情景测算一路缓慢下移，不应出现反弹
        vals = list(chart_econ.fg)
        for a, b in zip(vals, vals[1:]):
            self.assertGreaterEqual(a + 1e-12, b)


class TestStatistics(unittest.TestCase):
    """脚本里算出来的统计量。"""

    def test_decade_mean(self):
        expected = sum(chart_econ.actual_growth) / len(chart_econ.actual_growth)
        self.assertAlmostEqual(chart_econ.decade_mean, expected, places=9)
        self.assertAlmostEqual(chart_econ.decade_mean, 5.5, places=9)

    def test_f2046_matches_last_forecast(self):
        self.assertEqual(chart_econ.f2046, chart_econ.fg[-1])
        self.assertAlmostEqual(chart_econ.f2046, 3.3, places=9)

    def test_structural_decline(self):
        # 长期看：2025 衔接点高于 2046 情景值
        self.assertGreater(chart_econ.fg[0], chart_econ.f2046)


class TestOutputPath(unittest.TestCase):
    """图片保存路径应落在脚本所在目录（而不是写死的旧目录）。"""

    def test_output_name(self):
        self.assertEqual(chart_econ.out.name, "china_gdp_growth_2016_2046.png")

    def test_output_dir_is_script_dir(self):
        script_dir = Path(chart_econ.__file__).resolve().parent
        self.assertEqual(chart_econ.out.resolve().parent, script_dir)

    def test_output_is_a_path_object(self):
        self.assertIsInstance(chart_econ.out, Path)


if __name__ == "__main__":
    unittest.main()
