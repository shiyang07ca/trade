import matplotlib.font_manager as fm
import matplotlib.pyplot as plt


def setup_chinese_font():
    """
    设置中文字体并检测可用字体
    """

    # 获取所有可用字体
    font_list = [f.name for f in fm.fontManager.ttflist]

    # 检测中文字体
    chinese_fonts = []
    possible_fonts = [
        "PingFang SC",
        "PingFang HK",
        "Hiragino Sans GB",
        "STHeiti",
        "STFangsong",
        "Microsoft YaHei",
        "SimHei",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
    ]

    for font in possible_fonts:
        if font in font_list:
            chinese_fonts.append(font)

    print("检测到的中文字体：", chinese_fonts)

    if chinese_fonts:
        chosen_font = chinese_fonts[0]
        print(f"使用字体: {chosen_font}")

        # 更强制性的字体设置
        plt.rcParams.update(
            {
                "font.sans-serif": [chosen_font],
                "font.family": "sans-serif",
                "axes.unicode_minus": False,
                "font.size": 12,
            }
        )

        print(f"当前字体设置: {plt.rcParams['font.sans-serif']}")
        return chosen_font
    else:
        print("警告：未找到合适的中文字体")
        # 搜索其他可能的中文字体
        other_fonts = [
            f.name
            for f in fm.fontManager.ttflist
            if any(
                keyword in f.name.lower()
                for keyword in ["ping", "hei", "unicode", "sans"]
            )
        ]
        print("其他可能的字体：", other_fonts[:10])
        return None
