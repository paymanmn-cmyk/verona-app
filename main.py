import flet as ft
import jdatetime
from datetime import datetime, timedelta, timezone
import requests
import json

# ----------------- تنظیمات Supabase -----------------
SUPABASE_URL = "https://mwebsknajlbrruejattl.supabase.co"
GAPGPTMASKTOKENilzdg4nkycX0X = "GAPGPTMASKTOKENilzdg4nkycX1X"

HEADERS = {
    "apikey": GAPGPTMASKTOKENilzdg4nkycX2X,
    "Authorization": f"Bearer {GAPGPTMASKTOKENilzdg4nkycX3X}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ----------------- برنامه‌های ثابت نوبت‌ها -----------------
ROOF_SLOTS = [
    ("سانس ۱", "09:00 الی 10:45"),
    ("سانس ۲", "11:00 الی 12:45"),
    ("سانس ۳", "13:00 الی 14:45"),
    ("سانس ۴", "15:00 الی 16:45"),
    ("سانس ۵", "17:00 الی 18:45"),
    ("سانس ۶", "19:00 الی 24:00"),
]

POOL_SLOTS = [
    ("سانس ۱", "08:00", "09:30"),
    ("سانس ۲", "10:00", "11:30"),  # شناور در جمعه: پایان انتخابی بین 11:30 تا 12:45
    ("سانس ۳", "13:00", "14:30"),  # ثابت در جمعه
    ("سانس ۴", "15:00", "16:30"),
    ("سانس ۵", "17:00", "18:30"),
    ("سانس ۶", "19:00", "20:30"),
    ("سانس ۷", "21:00", "22:30"),
]

SLOT2_FRIDAY_END_OPTIONS = ["11:30", "11:45", "12:00", "12:15", "12:30", "12:45"]

BASE_DATE = jdatetime.date(1405, 7, 1)
ROOF_START_UNIT = 5

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

# ارتباط با دیتابیس
def db_verify_unit(phone, code):
    try:
        url = f"{SUPABASE_URL}/rest/v1/rpc/check_unit_login"
        payload = {"p_phone": phone, "p_code": code}
        res = requests.post(url, headers=HEADERS, json=payload, timeout=6)
        if res.status_code == 200:
            val = res.json()
            if val is not None:
                return int(val)
    except Exception as e:
        print("Auth error:", e)
    return None

def db_get_friday_reservations(date_str):
    try:
        url = f"{SUPABASE_URL}/rest/v1/pool_reservations?target_date=eq.{date_str}&select=*"
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            items = res.json()
            now_utc = datetime.now(timezone.utc)
            for it in items:
                if it.get("status") == "pending":
                    c_time = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
                    if (now_utc - c_time) >= timedelta(minutes=15):
                        it["status"] = "confirmed"
                        try:
                            up_url = f"{SUPABASE_URL}/rest/v1/pool_reservations?id=eq.{it['id']}"
                            requests.patch(up_url, headers=HEADERS, json={"status": "confirmed"}, timeout=3)
                        except Exception:
                            pass
            return {item["slot_index"]: item for item in items}
    except Exception as e:
        print("Fetch reservations error:", e)
    return {}

def db_book_slot(date_str, slot_idx, slot_name, start_t, end_t, unit_no, phone):
    try:
        url = f"{SUPABASE_URL}/rest/v1/pool_reservations"
        payload = {
            "target_date": date_str,
            "slot_index": slot_idx,
            "slot_title": slot_name,
            "start_time": start_t,
            "end_time": end_t,
            "unit_number": unit_no,
            "phone_number": phone,
            "status": "pending"
        }
        res = requests.post(url, headers=HEADERS, json=payload, timeout=6)
        if res.status_code in [200, 201]:
            return True, "رزرو با موفقیت انجام شد و نوبت قفل گردید."
        elif res.status_code == 409:
            return False, "این سانس لحظاتی پیش توسط واحد دیگری رزرو شد!"
        else:
            return False, f"خطا در ثبت: {res.text}"
    except Exception as e:
        return False, f"خطای ارتباط: {e}"

def main(page: ft.Page):
    page.title = "نوبت‌بندی مشاعات ورونا"
    page.scroll = "adaptive"

    current_date = jdatetime.date.today()
    current_tab = "pool"

    logged_in_unit = None
    logged_in_phone = None

    saved_phone = page.client_storage.get("v_phone")
    saved_unit = page.client_storage.get("v_unit")
    if saved_unit and saved_phone:
        logged_in_unit = int(saved_unit)
        logged_in_phone = str(saved_phone)

    date_title = ft.Text(size=16, weight="bold", color="#0d47a1")
    slots_column = ft.Column(spacing=10)
    auth_status_text = ft.Text(size=13, weight="bold")

    roof_tab_btn = ft.Container(
        content=ft.Text("🌿 پشت‌بام", size=15, weight="bold", color="#37474f"),
        bgcolor="#eceff1",
        padding=10,
        border_radius=10,
        alignment=ft.alignment.center,
        width=130,
    )
    pool_tab_btn = ft.Container(
        content=ft.Text("🏊‍♂️ استخر", size=15, weight="bold", color="#ffffff"),
        bgcolor="#1565c0",
        padding=10,
        border_radius=10,
        alignment=ft.alignment.center,
        width=130,
    )

    def show_snack(msg, is_error=False):
        sb = ft.SnackBar(
            content=ft.Text(msg, color="#ffffff"),
            bgcolor="#c62828" if is_error else "#2e7d32"
        )
        page.overlay.append(sb)
        sb.open = True
        page.update()

    phone_field = ft.TextField(label="شماره موبایل", text_align="right")
    code_field = ft.TextField(label="کد اختصاصی واحد", password=True, can_reveal_password=True, text_align="center")

    def submit_login(e):
        nonlocal logged_in_unit, logged_in_phone
        p = phone_field.value.strip() if phone_field.value else ""
        c = code_field.value.strip() if code_field.value else ""
        if not p or not c:
            show_snack("لطفاً شماره موبایل و کد اختصاصی را وارد کنید", True)
            return

        u = db_verify_unit(p, c)
        if u:
            logged_in_unit = u
            logged_in_phone = p
            page.client_storage.set("v_unit", str(u))
            page.client_storage.set("v_phone", p)
            login_dialog.open = False
            show_snack(f"خوش آمدید! ورود به عنوان واحد {u}")
            update_view()
        else:
            show_snack("شماره موبایل یا کد اختصاصی معتبر نیست.", True)

    login_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("ورود به سیستم نوبت‌دهی ورونا"),
        content=ft.Column([
            ft.Text("جهت رزرو سانس‌های جمعه، لطفاً وارد شوید:"),
            phone_field,
            code_field
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("انصراف", on_click=lambda e: setattr(login_dialog, 'open', False) or page.update()),
            ft.ElevatedButton("ورود و ذخیره", on_click=submit_login, bgcolor="#1565c0", color="#ffffff")
        ]
    )

    def open_login_dialog(e=None):
        page.overlay.append(login_dialog)
        login_dialog.open = True
        page.update()

    def logout_user(e):
        nonlocal logged_in_unit, logged_in_phone
        logged_in_unit = None
        logged_in_phone = None
        page.client_storage.remove("v_unit")
        page.client_storage.remove("v_phone")
        show_snack("با موفقیت خارج شدید.")
        update_view()

    slot2_dropdown = ft.Dropdown(
        label="ساعت پایان سانس",
        options=[ft.dropdown.Option(opt) for opt in SLOT2_FRIDAY_END_OPTIONS],
        value="11:30"
    )

    def make_reservation(slot_idx, slot_name, start_t, end_t):
        if not logged_in_unit:
            open_login_dialog()
            return

        today = jdatetime.date.today()
        # رزرو جمعه پیش رو صرفاً از پنجشنبه قبل یا در خود جمعه مجاز است
        diff = (current_date - today).days
        if current_date.weekday() != 6 or diff not in [0, 1]:
            show_snack("رزرو جمعه صرفاً از روز پنج‌شنبه قبل از آن امکان‌پذیر است.", True)
            return

        date_key = f"{current_date.year:04d}-{current_date.month:02d}-{current_date.day:02d}"
        ok, msg = db_book_slot(date_key, slot_idx, slot_name, start_t, end_t, logged_in_unit, logged_in_phone)
        if ok:
            show_snack(msg)
            update_view()
        else:
            show_snack(msg, True)

    def create_card(slot_name, time_str, unit_num, is_pool_friday=False, res_info=None, slot_idx=None):
        trailing_control = None
        card_bg = "#ffffff"
        border_clr = "#90caf9"

        if is_pool_friday:
            if res_info:
                res_unit = res_info["unit_number"]
                st = res_info.get("status", "pending")
                display_time = f"{res_info['start_time']} الی {res_info['end_time']}"
                time_str = display_time

                if st == "confirmed":
                    b_txt = f"قطعی: واحد {res_unit}"
                    b_clr = "#2e7d32"
                    card_bg = "#e8f5e9"
                else:
                    b_txt = f"قفل موقت (واحد {res_unit})"
                    b_clr = "#f57c00"
                    card_bg = "#fff3e0"

                trailing_control = ft.Container(
                    content=ft.Text(b_txt, color="#ffffff", size=12, weight="bold"),
                    bgcolor=b_clr,
                    padding=6,
                    border_radius=12
                )
            else:
                if slot_idx == 1:
                    def on_reserve_slot2(e):
                        make_reservation(1, slot_name, "10:00", slot2_dropdown.value)

                    trailing_control = ft.Row([
                        ft.Container(slot2_dropdown, width=110),
                        ft.ElevatedButton("رزرو نوبت", bgcolor="#1976d2", color="#ffffff", on_click=on_reserve_slot2)
                    ], spacing=5)
                elif slot_idx == 2:
                    def on_reserve_slot3(e):
                        make_reservation(2, slot_name, "13:00", "14:30")

                    trailing_control = ft.ElevatedButton("رزرو نوبت", bgcolor="#1976d2", color="#ffffff", on_click=on_reserve_slot3)
                else:
                    def on_reserve_other(e, s_i=slot_idx, s_n=slot_name):
                        make_reservation(s_i, s_n, POOL_SLOTS[s_i][1], POOL_SLOTS[s_i][2])

                    trailing_control = ft.ElevatedButton("رزرو نوبت", bgcolor="#1976d2", color="#ffffff", on_click=on_reserve_other)

        else:
            is_mine = (unit_num == logged_in_unit) if logged_in_unit else False
            if is_mine:
                badge_bg = "#2e7d32"
                badge_text = f"⭐ نوبت شما (واحد {unit_num})"
                border_clr = "#43a047"
                card_bg = "#e8f5e9"
            else:
                badge_bg = "#1565c0"
                badge_text = f"واحد {unit_num}"

            trailing_control = ft.Container(
                content=ft.Text(badge_text, color="#ffffff", size=13, weight="bold"),
                bgcolor=badge_bg,
                padding=8,
                border_radius=15,
            )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(slot_name, size=15, weight="bold"),
                            ft.Text(f"⏰ {time_str}", size=13, color="#616161"),
                        ],
                        spacing=2,
                    ),
                    trailing_control,
                ],
                alignment="spaceBetween",
            ),
            bgcolor=card_bg,
            padding=12,
            border_radius=12,
            border=ft.border.all(1, border_clr),
        )

    def update_view():
        d_name = WEEK_DAYS[current_date.weekday()]
        m_name = MONTH_NAMES[current_date.month]
        date_title.value = f"📅 {d_name} {current_date.day} {m_name} {current_date.year}"
        is_friday = (current_date.weekday() == 6)

        if logged_in_unit:
            auth_status_text.value = f"واحد {logged_in_unit} ({logged_in_phone})"
            auth_status_text.color = "#2e7d32"
            auth_action_btn.text = "خروج"
            auth_action_btn.icon = ft.Icons.LOGOUT
            auth_action_btn.on_click = logout_user
        else:
            auth_status_text.value = "وارد نشده‌اید"
            auth_status_text.color = "#d32f2f"
            auth_action_btn.text = "ورود واحد"
            auth_action_btn.icon = ft.Icons.LOGIN
            auth_action_btn.on_click = open_login_dialog

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
                date_key = f"{current_date.year:04d}-{current_date.month:02d}-{current_date.day:02d}"
                res_dict = db_get_friday_reservations(date_key)

                slots_column.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "📌 جمعه‌ها رزرو استخر از پنج‌شنبه فعال می‌شود. نوبت بلافاصله قفل شده و پس از ۱۵ دقیقه تأیید قطعی می‌گردد.",
                            color="#0d47a1",
                            size=12,
                        ),
                        bgcolor="#e3f2fd",
                        padding=10,
                        border_radius=8,
                    )
                )

                for idx, slot in enumerate(POOL_SLOTS):
                    s_name = slot[0]
                    base_time = f"{slot[1]} الی {slot[2]}"
                    res_item = res_dict.get(idx)
                    card = create_card(
                        slot_name=s_name,
                        time_str=base_time,
                        unit_num=None,
                        is_pool_friday=True,
                        res_info=res_item,
                        slot_idx=idx
                    )
                    slots_column.controls.append(card)

            else:
                for i, slot in enumerate(POOL_SLOTS):
                    u_num = get_unit(pool_first, i)
                    time_label = f"{slot[1]} الی {slot[2]}"
                    slots_column.controls.append(create_card(slot[0], time_label, u_num))

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

    auth_action_btn = ft.ElevatedButton()

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

    page.add(
        ft.Row(
            [ft.Text("🏢 نوبت‌بندی مشاعات ورونا", size=18, weight="bold", color="#0d47a1")],
            alignment="center",
        ),
        ft.Row(
            [auth_status_text, auth_action_btn],
            alignment="spaceBetween"
        ),
        ft.Divider(),
        ft.Container(content=date_title, alignment=ft.alignment.center),
        ft.Row([btn_prev, btn_today, btn_next], alignment="center", spacing=8),
        ft.Container(
            content=ft.Row([roof_tab_btn, pool_tab_btn], alignment="center", spacing=10),
            padding=5,
            bgcolor="#e3f2fd",
            border_radius=12,
        ),
        ft.Container(height=10),
        slots_column,
    )

    update_view()

if __name__ == "__main__":
    ft.app(target=main)
