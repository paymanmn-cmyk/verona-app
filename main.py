import flet as ft
import jdatetime
from datetime import timedelta

# بازه‌های زمانی
ROOF_SLOTS = [
    ("سانس ۱", "09:00 الی 10:45"),
    ("سانس ۲", "11:00 الی 12:45"),
    ("سانس ۳", "13:00 الی 14:45"),
    ("سانس ۴", "15:00 الی 16:45"),
    ("سانس ۵", "17:00 الی 18:45"),
    ("سانس ۶", "19:00 الی 24:00"),
]

POOL_SLOTS = [
    ("سانس ۱", "08:00 الی 09:30"),
    ("سانس ۲", "10:00 الی 11:30"),
    ("سانس ۳", "13:00 الی 14:30"),
    ("سانس ۴", "15:00 الی 16:30"),
    ("سانس ۵", "17:00 الی 18:30"),
    ("سانس ۶", "19:00 الی 20:30"),
    ("سانس ۷", "21:00 الی 22:30"),
]

BASE_DATE = jdatetime.date(1405, 7, 1)
ROOF_START_UNIT = 5

# مبنای استخر طبق جدول رسمی: ۲ فروردین ۱۴۰۵ (شنبه) -> سانس ۱ = واحد ۴
# چرخه روزانه و پیوسته است؛ جمعه‌ها فقط نمایش هماهنگی دارند ولی در چرخش شمارش می‌شوند.
POOL_BASE_DATE = jdatetime.date(1405, 1, 2)
POOL_BASE_UNIT = 4

WEEK_DAYS = {
    0: "شنبه",
    1: "یکشنبه",
    2: "دوشنبه",
    3: "سه‌شنبه",
    4: "چهارشنبه",
    5: "پنج‌شنبه",
    6: "جمعه",
}

MONTH_NAMES = {
    1: "فروردین",
    2: "اردیبهشت",
    3: "خرداد",
    4: "تیر",
    5: "مرداد",
    6: "شهریور",
    7: "مهر",
    8: "آبان",
    9: "آذر",
    10: "دی",
    11: "بهمن",
    12: "اسفند",
}


def get_day_offset(target_date):
    return (target_date - BASE_DATE).days


def get_pool_day_offset(target_date):
    return (target_date - POOL_BASE_DATE).days


def get_unit(start_unit, offset):
    return ((start_unit - 1 + offset) % 6) + 1


# توابع سازگاری برای تمام نسخه‌های Flet
def get_alignment_center():
    try:
        return ft.Alignment(0, 0)
    except Exception:
        return None


def get_border_all(width, color):
    try:
        return ft.border.all(width, color)
    except Exception:
        try:
            return ft.Border.all(width, color)
        except Exception:
            return None


def main(page: ft.Page):
    page.title = "نوبت‌بندی مشاعات ورونا"
    page.rtl = True
    page.padding = 16
    page.scroll = "auto"

    current_date = jdatetime.date.today()
    selected_unit = 1
    current_tab = "roof"

    date_title = ft.Text(size=16, weight="bold", color="#0d47a1")
    slots_column = ft.Column(spacing=10)
    unit_buttons_row = ft.Row(alignment="center", spacing=6)

    # دکمه‌های تب بالا
    roof_tab_btn = ft.Container(
        content=ft.Text("🌿 پشت‌بام", size=15, weight="bold", color="#ffffff"),
        bgcolor="#1565c0",
        padding=10,
        border_radius=10,
        alignment=get_alignment_center(),
        width=130,
    )
    pool_tab_btn = ft.Container(
        content=ft.Text("🏊‍♂️ استخر", size=15, weight="bold", color="#37474f"),
        bgcolor="#eceff1",
        padding=10,
        border_radius=10,
        alignment=get_alignment_center(),
        width=130,
    )

    def create_card(slot_name, time_str, unit_num, is_pool_friday=False):
        is_mine = (unit_num == selected_unit)

        if is_pool_friday:
            badge_bg = "#757575"
            badge_text = "هماهنگی با سرایدار"
            border_color = "#bdbdbd"
            bg_color = "#f5f5f5"
        elif is_mine:
            badge_bg = "#2e7d32"
            badge_text = f"⭐ نوبت شما (واحد {unit_num})"
            border_color = "#43a047"
            bg_color = "#e8f5e9"
        else:
            badge_bg = "#1565c0"
            badge_text = f"واحد {unit_num}"
            border_color = "#90caf9"
            bg_color = "#ffffff"

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(slot_name, size=15, weight="bold"),
                            ft.Text(f"⏰ {time_str}", size=13, color="#616161"),
                        ],
                        spacing=2,
                    ),
                    ft.Container(
                        content=ft.Text(badge_text, color="#ffffff", size=13, weight="bold"),
                        bgcolor=badge_bg,
                        padding=8,
                        border_radius=15,
                    )
                ],
                alignment="spaceBetween",
            ),
            bgcolor=bg_color,
            padding=12,
            border=get_border_all(1, border_color),
            border_radius=10,
        )

    def on_unit_click(e):
        nonlocal selected_unit
        selected_unit = e.control.data
        render_unit_selector()
        update_view()

    def render_unit_selector():
        unit_buttons_row.controls.clear()
        for u in range(1, 7):
            is_active = (u == selected_unit)
            btn = ft.Container(
                content=ft.Text(
                    f"واحد {u}",
                    size=13,
                    weight="bold",
                    color="#ffffff" if is_active else "#0d47a1",
                ),
                bgcolor="#1976d2" if is_active else "#e3f2fd",
                border=get_border_all(1, "#1976d2"),
                padding=8,
                border_radius=8,
                data=u,
                on_click=on_unit_click,
            )
            unit_buttons_row.controls.append(btn)

    def update_view():
        nonlocal current_date
        d_name = WEEK_DAYS[current_date.weekday()]
        m_name = MONTH_NAMES[current_date.month]
        date_title.value = f"📅 {d_name} {current_date.day} {m_name} {current_date.year}"

        is_friday = (current_date.weekday() == 6)

        slots_column.controls.clear()

        if current_tab == "roof":
            roof_tab_btn.bgcolor = "#1565c0"
            roof_tab_btn.content.color = "#ffffff"
            pool_tab_btn.bgcolor = "#eceff1"
            pool_tab_btn.content.color = "#37474f"

            roof_first = get_unit(ROOF_START_UNIT, get_day_offset(current_date))
            for i, slot in enumerate(ROOF_SLOTS):
                u_num = get_unit(roof_first, i)
                slots_column.controls.append(create_card(slot[0], slot[1], u_num))
        else:
            pool_tab_btn.bgcolor = "#1565c0"
            pool_tab_btn.content.color = "#ffffff"
            roof_tab_btn.bgcolor = "#eceff1"
            roof_tab_btn.content.color = "#37474f"

            pool_first = get_unit(POOL_BASE_UNIT, get_pool_day_offset(current_date))

            if is_friday:
                slots_column.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "⚠️ جمعه‌ها استخر صرفاً با هماهنگی قبلی با سرایدار قابل استفاده است.",
                            color="#b71c1c",
                            size=13,
                        ),
                        bgcolor="#ffebee",
                        padding=10,
                        border_radius=8,
                    )
                )
                for slot in POOL_SLOTS:
                    slots_column.controls.append(
                        create_card(slot[0], slot[1], None, is_pool_friday=True)
                    )
            else:
                for i, slot in enumerate(POOL_SLOTS):
                    u_num = get_unit(pool_first, i)
                    slots_column.controls.append(create_card(slot[0], slot[1], u_num))

        page.update()

    def change_date(days):
        nonlocal current_date
        current_date += timedelta(days=days)
        update_view()

    def go_today(e):
        nonlocal current_date
        current_date = jdatetime.date.today()
        update_view()

    def set_tab(tab_name):
        nonlocal current_tab
        current_tab = tab_name
        update_view()

    roof_tab_btn.on_click = lambda e: set_tab("roof")
    pool_tab_btn.on_click = lambda e: set_tab("pool")

    # دکمه‌های ناوبری تاریخ
    btn_prev = ft.Container(
        content=ft.Text("⬅️ روز قبل", size=13, color="#ffffff"),
        bgcolor="#1e88e5",
        padding=8,
        border_radius=8,
        on_click=lambda e: change_date(-1),
    )
    btn_today = ft.Container(
        content=ft.Text("امروز", size=13, color="#0d47a1"),
        bgcolor="#bbdefb",
        padding=8,
        border_radius=8,
        on_click=go_today,
    )
    btn_next = ft.Container(
        content=ft.Text("روز بعد ➡️", size=13, color="#ffffff"),
        bgcolor="#1e88e5",
        padding=8,
        border_radius=8,
        on_click=lambda e: change_date(1),
    )

    render_unit_selector()

    page.add(
        ft.Row(
            [ft.Text("🏢 نوبت‌بندی مشاعات ورونا", size=18, weight="bold", color="#0d47a1")],
            alignment="center",
        ),
        ft.Divider(),
        ft.Text("واحد خود را انتخاب کنید:", size=13, color="#424242"),
        unit_buttons_row,
        ft.Container(height=5),
        ft.Container(
            content=ft.Column([
                ft.Container(content=date_title, alignment=get_alignment_center()),
                ft.Row([btn_prev, btn_today, btn_next], alignment="center", spacing=8),
            ]),
            bgcolor="#e3f2fd",
            padding=10,
            border_radius=10,
        ),
        ft.Container(height=10),
        ft.Row([roof_tab_btn, pool_tab_btn], alignment="center", spacing=10),
        ft.Container(height=5),
        slots_column,
    )

    update_view()


if __name__ == "__main__":
    try:
        ft.run(main)
    except AttributeError:
        try:
            ft.app(target=main)
        except AttributeError:
            import flet.app as flet_app

            flet_app.app(target=main)
