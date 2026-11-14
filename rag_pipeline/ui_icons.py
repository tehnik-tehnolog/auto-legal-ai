"""
Утилита загрузки и встраивания SVG-иконок из ui/light/*.svg и ui/dark/*.svg
с автоматической адаптацией к светлой и темной теме Streamlit.
"""

import base64
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from rag_pipeline.config import UI_DIR

ICON_NAMES = [
    "add_file",
    "court",
    "pdd",
    "pin",
    "regulatory",
    "remove",
    "rename",
    "unpin",
]


def _clean_svg(raw_svg: str) -> str:
    """Удаление XML/DOCTYPE заголовков для корректного встраивания в HTML и data URI"""
    cleaned = re.sub(r"<\?xml[^>]*\?>", "", raw_svg, flags=re.IGNORECASE)
    cleaned = re.sub(r"<!DOCTYPE[^>]*>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


@lru_cache(maxsize=32)
def get_svg_data_uri(name: str, theme: str = "light") -> str:
    """Возвращает data:image/svg+xml;base64,... для иконки из ui/{theme}/{name}.svg"""
    folder = "dark" if theme == "dark" else "light"
    svg_path: Path = UI_DIR / folder / f"{name}.svg"
    if not svg_path.exists():
        # Пробуем альтернативную папку, если файл отсутствует
        alt_folder = "light" if folder == "dark" else "dark"
        svg_path = UI_DIR / alt_folder / f"{name}.svg"
    if not svg_path.exists():
        return ""

    raw = svg_path.read_text(encoding="utf-8", errors="ignore")
    cleaned = _clean_svg(raw)
    b64 = base64.b64encode(cleaned.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def detect_streamlit_theme(st_module) -> Optional[str]:
    """Определяет активную тему Streamlit ('light' или 'dark'), если доступно st.context.theme"""
    try:
        ctx = getattr(st_module, "context", None)
        theme_obj = getattr(ctx, "theme", None) if ctx else None
        t_type = getattr(theme_obj, "type", None) if theme_obj else None
        if t_type in ("light", "dark"):
            return t_type
    except Exception:
        pass
    return None


def icon_img_html(name: str, size: int = 18, theme: Optional[str] = None, margin_right: int = 6) -> str:
    """
    Генерирует HTML-тег иконки, адаптирующийся к светлой и темной теме.
    Если тема известна явно из st.context.theme — рендерит нужную версию;
    иначе рендерит пару light/dark с переключением через CSS prefers-color-scheme.
    """
    style = f"width:{size}px;height:{size}px;vertical-align:-0.2em;margin-right:{margin_right}px;flex-shrink:0;"
    if theme in ("light", "dark"):
        uri = get_svg_data_uri(name, theme)
        return f'<img src="{uri}" alt="{name}" style="{style}" />' if uri else ""

    light_uri = get_svg_data_uri(name, "light")
    dark_uri = get_svg_data_uri(name, "dark")
    if not light_uri and not dark_uri:
        return ""
    return (
        f'<img class="ui-theme-light" src="{light_uri}" alt="{name}" style="{style}" />'
        f'<img class="ui-theme-dark" src="{dark_uri}" alt="{name}" style="{style}" />'
    )


@lru_cache(maxsize=4)
def build_ui_icons_css(theme: Optional[str] = None) -> str:
    """
    CSS-стили для встраивания пользовательских SVG-иконок (ui/light и ui/dark)
    в кнопки навигации, управления чатами (pin/unpin/rename/remove)
    и кнопку прикрепления файла справа от окна ввода промпта (как в мессенджере).
    """
    active_theme = theme if theme in ("light", "dark") else "light"

    def _rule_for_button(selector: str, icon_name: str, icon_size: int = 16, only_icon: bool = False) -> str:
        l_uri = get_svg_data_uri(icon_name, "light")
        d_uri = get_svg_data_uri(icon_name, "dark")
        chosen = d_uri if active_theme == "dark" else l_uri

        base_css = ""
        if only_icon:
            base_css = f"""
            {selector} {{
                position: relative;
                min-height: 2.2rem !important;
                padding: 0.25rem !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}
            {selector} p, {selector} span {{
                display: none !important;
            }}
            {selector}::before {{
                content: "";
                display: inline-block;
                width: {icon_size}px;
                height: {icon_size}px;
                background-image: url("{chosen}");
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
            }}
            """
        else:
            base_css = f"""
            {selector} {{
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                gap: 8px !important;
                text-align: left !important;
            }}
            {selector}::before {{
                content: "";
                display: inline-block;
                width: {icon_size}px;
                height: {icon_size}px;
                flex-shrink: 0;
                background-image: url("{chosen}");
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
            }}
            """

        if theme is None and l_uri and d_uri:
            base_css += f"""
            @media (prefers-color-scheme: dark) {{
                {selector}::before {{
                    background-image: url("{d_uri}");
                }}
            }}
            """
        return base_css

    l_add = get_svg_data_uri("add_file", "light")
    d_add = get_svg_data_uri("add_file", "dark")
    chosen_add = d_add if active_theme == "dark" else l_add

    css = f"""
    <style>
    /* Адаптивное переключение inline-иконок если theme=None */
    .ui-theme-dark {{ display: none; }}
    .ui-theme-light {{ display: inline-block; }}
    @media (prefers-color-scheme: dark) {{
        .ui-theme-light {{ display: none !important; }}
        .ui-theme-dark {{ display: inline-block !important; }}
    }}

    /* Навигация в сайдбаре с кастомными SVG */
    {_rule_for_button('.st-key-nav_btn_chat button', 'court', icon_size=18, only_icon=False)}
    {_rule_for_button('.st-key-nav_btn_legal button', 'regulatory', icon_size=18, only_icon=False)}
    {_rule_for_button('.st-key-nav_btn_pdd button', 'pdd', icon_size=18, only_icon=False)}

    /* Кнопки управления чатами: pin, unpin, rename, remove */
    {_rule_for_button('[class*="st-key-pin_btn_"] button', 'pin', icon_size=15, only_icon=True)}
    {_rule_for_button('[class*="st-key-unpin_btn_"] button', 'unpin', icon_size=15, only_icon=True)}
    {_rule_for_button('[class*="st-key-rename_btn_"] button', 'rename', icon_size=15, only_icon=True)}
    {_rule_for_button('[class*="st-key-del_btn_"] button', 'remove', icon_size=15, only_icon=True)}
    {_rule_for_button('[class*="st-key-del_pin_btn_"] button', 'remove', icon_size=15, only_icon=True)}

    /* Иконка добавления файла правее от окна ввода промпта (как в мессенджере) */
    [data-testid="stBottom"] [data-testid="stPopover"] button {{
        height: 44px !important;
        min-height: 44px !important;
        width: 44px !important;
        padding: 0 !important;
        border-radius: 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    [data-testid="stBottom"] [data-testid="stPopover"] button p,
    [data-testid="stBottom"] [data-testid="stPopover"] button svg {{
        display: none !important;
    }}
    [data-testid="stBottom"] [data-testid="stPopover"] button::before {{
        content: "";
        display: inline-block;
        width: 20px;
        height: 20px;
        background-image: url("{chosen_add}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    """
    if theme is None and d_add:
        css += f"""
        @media (prefers-color-scheme: dark) {{
            [data-testid="stBottom"] [data-testid="stPopover"] button::before {{
                background-image: url("{d_add}");
            }}
        }}
        """
    css += "\n</style>\n"
    return css
