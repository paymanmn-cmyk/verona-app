import streamlit as st
import pandas as pd
import jdatetime
from io import BytesIO
from datetime import datetime, date, timedelta
from supabase import create_client, Client

# --- تنظیمات صفحه ---
st.set_page_config(page_title="مدیریت ساختمان ورونا", layout="wide", initial_sidebar_state="collapsed")

# تنظیم استایل راست‌چین و فونت
st.markdown("""
<style>
    .stApp {
        direction: rtl;
        text-align: right;
    }
    th, td {
        text-align: right !important;
    }
</style>
""", unsafe_allow_html=True)

# --- اتصال به دیتابیس Supabase ---
SUPABASE_URL = "https://iqlvucczvqozzzvpxave.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlxbHZ1Y2N6dnFvenp6dnB4YXZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA1NzA1MzUsImV4cCI6MjEwNjE0NjUzNX0.9z1kimVyhZ9jNOD0JZKSpvdiNIBxaA5m7wCBb1LaMn0"


@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- سانس‌های استاندارد ---
POOL_SLOTS = [
    ("08:00", "09:45"),
    ("10:00", "11:45"),
    ("12:00", "13:45"),
    ("14:00", "15:45"),
    ("16:00", "17:45"),
    ("18:00", "19:45"),
    ("20:00", "21:45"),
]

ROOF_SLOTS = [
    ("09:00", "10:45"),
    ("11:00", "12:45"),
    ("13:00", "14:45"),
    ("15:00", "16:45"),
    ("17:00", "18:45"),
    ("19:00", "23:45"),
]


# --- تبدیل تاریخ میلادی به شمسی و برعکس ---
def to_jalali(g_date):
    """ورودی: رشته یا آبجکت تاریخ میلادی -> خروجی: رشته شمسی"""
    try:
        if isinstance(g_date, str):
            g_date = datetime.strptime(str(g_date)[:10], "%Y-%m-%d").date()
        return jdatetime.date.fromgregorian(date=g_date).strftime("%Y/%m/%d")
    except Exception:
        return str(g_date)

def jalali_to_gregorian(j_str):
    """ورودی: رشته شمسی مثل 1403/07/15 -> خروجی: تاریخ میلادی"""
    try:
        j_str = j_str.strip().replace("-", "/")
        y, m, d = [int(x) for x in j_str.split("/")]
        return jdatetime.date(y, m, d).togregorian()
    except Exception:
        return None
# --- توابع رزروها و واحدها ---
def get_units():
    try:
        res = supabase.table("units").select("*").order("unit_number").execute()
        return res.data or []
    except Exception:
        return []

def get_bookings(facility=None):
    try:
        query = supabase.table("bookings").select("*, units(unit_number)").order("booking_date").order("start_time")
        if facility:
            query = query.eq("facility", facility)
        res = query.execute()
        return res.data or []
    except Exception:
        return []

def create_booking(unit_id, facility, b_date, s_time, e_time):
    data = {
        "unit_id": unit_id,
        "facility": facility,
        "booking_date": str(b_date),
        "start_time": s_time,
        "end_time": e_time,
        "status": "pending"
    }
    return supabase.table("bookings").insert(data).execute()

def update_booking_status(booking_id, status):
    return supabase.table("bookings").update({"status": status}).eq("id", booking_id).execute()

# --- توابع مدیریت مالی و اخطارها ---
def get_finance_ledger():
    try:
        res = supabase.table("finance_ledger").select("*").order("id", desc=False).execute()
        return res.data or []
    except Exception:
        return []

def add_finance_entry(entry_date, subject, cost, deposit):
    ledger = get_finance_ledger()
    prev_balance = ledger[-1]["balance"] if ledger else 0
    new_balance = float(prev_balance) + float(deposit) - float(cost)
    
    data = {
        "entry_date": str(entry_date),
        "subject": subject,
        "cost_amount": float(cost),
        "deposit_amount": float(deposit),
        "balance": new_balance
    }
    return supabase.table("finance_ledger").insert(data).execute()

def send_payment_notice(unit_number, subject, amount, message=""):
    data = {
        "unit_number": str(unit_number),
        "subject": subject,
        "amount": float(amount),
        "message": message
    }
    return supabase.table("payment_notices").insert(data).execute()

def delete_payment_notice(notice_id):
    return supabase.table("payment_notices").delete().eq("id", notice_id).execute()

def logout():
    st.session_state.user = None
    st.rerun()

# --- مدیریت لاگین و نشست ---
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🏢 سامانه مدیریت ساختمان ورونا")
    st.subheader("ورود به سامانه")
    
    login_tab_resident, login_tab_admin = st.tabs(["🔑 ورود ساکنین", "🛡️ ورود مدیریت (ادمین)"])
    
    # تب ۱: ورود ساکنین
    with login_tab_resident:
        with st.form("resident_login_form"):
            phone_input = st.text_input("شماره تلفن همراه:")
            code_input = st.text_input("کد اختصاصی واحد:", type="password")
            submitted_resident = st.form_submit_button("ورود به عنوان ساکن", use_container_width=True)
            
            if submitted_resident:
                units = get_units()
                found = False
                for u in units:
                    if str(u.get("phone_number")).strip() == str(phone_input).strip() and str(u.get("access_code")).strip() == str(code_input).strip():
                        st.session_state.user = {
                            "role": "resident",
                            "unit_number": str(u.get("unit_number")),
                            "id": u.get("id")
                        }
                        found = True
                        st.success(f"خوش آمدید، واحد {u.get('unit_number')}!")
                        st.rerun()
                if not found:
                    st.error("شماره تلفن یا کد اختصاصی اشتباه است.")

    # تب ۲: ورود مدیریت
    with login_tab_admin:
        with st.form("admin_login_form"):
            admin_user = st.text_input("نام کاربری مدیریت:")
            admin_pass = st.text_input("رمز عبور مدیریت:", type="password")
            submitted_admin = st.form_submit_button("ورود به پنل مدیریت", use_container_width=True)
            
            if submitted_admin:
                if (admin_user.upper() == "SYSTEM" and admin_pass == "SYSTEM") or (admin_user.lower() == "admin" and admin_pass == "admin"):
                    st.session_state.user = {
                        "role": "admin",
                        "unit_number": "مدیریت ساختمان",
                        "id": None
                    }
                    st.success("ورود مدیریت با موفقیت انجام شد.")
                    st.rerun()
                else:
                    st.error("نام کاربری یا رمز عبور مدیریت اشتباه است.")
    st.stop()

# --- هدر بالای صفحه ---
top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.markdown(f"### کاربر: **{st.session_state.user['unit_number']}** ({'مدیر سیستم' if st.session_state.user['role'] == 'admin' else 'ساکن'})")
with top_col2:
    if st.button("خروج از حساب", use_container_width=True):
        logout()

st.divider()

# ==========================================
# ۱. پنل ادمین
# ==========================================
if st.session_state.user["role"] == "admin":
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "📋 درخواست‌های در انتظار",
        "📅 تقویم و سانس‌های مشاعات",
        "💰 دفتر کل مالی ساختمان",
        "⚠️ ارسال و مدیریت اخطارها"
    ])
    
    # تب ۱: تایید/رد درخواست‌ها
    with admin_tab1:
        st.subheader("درخواست‌های در انتظار بررسی")
        pending_bookings = supabase.table("bookings").select("*, units(unit_number)").eq("status", "pending").order("created_at").execute().data or []
        
        if not pending_bookings:
            st.info("هیچ درخواستی در انتظار تایید نیست.")
        else:
            for b in pending_bookings:
                u_num = b['units']['unit_number'] if b.get('units') else 'نامشخص'
                with st.expander(f"درخواست واحد {u_num} - {b['facility']} ({to_jalali(b['booking_date'])})"):
                    st.write(f"**ساعت:** {b['start_time']} تا {b['end_time']}")
                    st.write(f"**تاریخ:** {b['booking_date']}")
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("✅ تایید درخواست", key=f"app_{b['id']}"):
                            update_booking_status(b['id'], "approved")
                            st.success("تایید شد.")
                            st.rerun()
                    with col_btn2:
                        if st.button("❌ رد درخواست", key=f"rej_{b['id']}"):
                            update_booking_status(b['id'], "rejected")
                            st.warning("رد شد.")
                            st.rerun()

    # تب ۲: تقویم سانس‌ها
    with admin_tab2:
        st.subheader("وضعیت کلی رزروها")
        facility_choice = st.radio("انتخاب فضا:", ["pool", "roof_garden"], format_func=lambda x: "استخر" if x == "pool" else "پشت‌بام", horizontal=True)
        all_b = get_bookings(facility_choice)
        if all_b:
            df_b = pd.DataFrame([{
                "واحد": item["units"]["unit_number"] if item.get("units") else "-",
                "تاریخ": to_jalali(item["booking_date"]),
                "شروع": item["start_time"],
                "پایان": item["end_time"],
                "وضعیت": "🔴 تایید شده" if item["status"] in ["confirmed", "approved"] else ("🟠 در انتظار" if item["status"] == "pending" else "⚪ رد شده")
            } for item in all_b])
            st.dataframe(df_b, use_container_width=True)
        else:
            st.info("هنوز رزروی ثبت نشده است.")

    # تب ۳: دفتر مالی
       # تب ۳: دفتر مالی (نسخه جدید با شمسی، اکسل و حذف)
    with admin_tab3:
        st.subheader("📊 دفتر کل درآمد و هزینه‌های ساختمان")
        ledger_data = get_finance_ledger()
        
        if ledger_data:
            df_ledger = pd.DataFrame([{
                "ردیف": idx + 1,
                "شناسه": row["id"],
                "تاریخ": to_jalali(row.get("entry_date")),
                "موضوع": row.get("subject", "-"),
                "هزینه (ریال)": int(row.get("cost_amount", 0)),
                "واریزی (ریال)": int(row.get("deposit_amount", 0)),
                "مانده (ریال)": int(row.get("balance", 0))
            } for idx, row in enumerate(ledger_data)])
            st.dataframe(df_ledger, use_container_width=True)
            
            last_balance = ledger_data[-1].get("balance", 0)
            st.metric("مانده صندوق ساختمان:", f"{int(last_balance):,} ریال")

            # --- خروجی اکسل ---
            export_df = df_ledger.drop(columns=["شناسه"])
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False, sheet_name="دفتر مالی")
            st.download_button(
                "⬇️ دانلود خروجی اکسل دفتر مالی",
                data=buf.getvalue(),
                file_name="finance_ledger.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # --- حذف رکورد مالی ---
            st.markdown("---")
            st.subheader("🗑️ حذف رکورد مالی")
            rec_options = {f"{to_jalali(r.get('entry_date'))} | {r.get('subject','-')} | هزینه: {int(r.get('cost_amount',0)):,} | واریزی: {int(r.get('deposit_amount',0)):,}": r["id"] for r in ledger_data}
            with st.form("delete_finance_form"):
                rec_to_del = st.selectbox("رکورد مورد نظر برای حذف را انتخاب کنید:", list(rec_options.keys()))
                del_confirm = st.form_submit_button("🗑️ حذف این رکورد", use_container_width=True)
                if del_confirm:
                    supabase.table("finance_ledger").delete().eq("id", rec_options[rec_to_del]).execute()
                    # بازسازی مانده حساب بعد از حذف
                    remaining = get_finance_ledger()
                    run_bal = 0
                    for r in remaining:
                        run_bal += float(r.get("deposit_amount", 0)) - float(r.get("cost_amount", 0))
                        supabase.table("finance_ledger").update({"balance": run_bal}).eq("id", r["id"]).execute()
                    st.success("رکورد حذف و مانده‌ها بازسازی شد.")
                    st.rerun()
        else:
            st.info("هنوز ردیف مالی ثبت نشده است.")

                # --- ورود اطلاعات از فایل اکسل (اصلاح شده) ---
        st.markdown("---")
        st.subheader("📥 ورود رکوردهای مالی از فایل اکسل")
        st.caption("فایل اکسل باید ۴ ستون داشته باشد: تاریخ (شمسی مانند 1403/07/15) | موضوع | هزینه | واریزی")
        up_file = st.file_uploader("انتخاب فایل اکسل:", type=["xlsx", "xls"])
        
        if up_file is not None:
            try:
                # خواندن فایل اکسل
                df_in = pd.read_excel(up_file)
                
                # تنظیم ۴ ستون اول
                col_names = ["تاریخ", "موضوع", "هزینه", "واریزی"]
                df_in = df_in.iloc[:, :4]
                df_in.columns = col_names[:len(df_in.columns)]
                
                # پاک‌سازی مقادیر خالی (NaN) برای جلوگیری از خطای JSON
                df_in["هزینه"] = pd.to_numeric(df_in["هزینه"], errors="coerce").fillna(0)
                df_in["واریزی"] = pd.to_numeric(df_in["واریزی"], errors="coerce").fillna(0)
                df_in["موضوع"] = df_in["موضوع"].fillna("سایر").astype(str)
                df_in["تاریخ"] = df_in["تاریخ"].astype(str)
                
                # حذف ردیف‌های کاملاً خالی
                df_in = df_in[df_in["تاریخ"].str.strip() != "nan"]
                
                st.dataframe(df_in, use_container_width=True)
                
                if st.button("💾 تایید و درج در دفتر مالی", use_container_width=True):
                    inserted = 0
                    for _, row in df_in.iterrows():
                        raw_date = str(row["تاریخ"]).strip()
                        g_date = jalali_to_gregorian(raw_date)
                        
                        # اگر تاریخ شمسی معتبر بود ثبت شود
                        if g_date is not None:
                            cost = float(row["هزینه"])
                            deposit = float(row["واریزی"])
                            subject = str(row["موضوع"]).strip()
                            
                            add_finance_entry(g_date, subject, cost, deposit)
                            inserted += 1
                    
                    if inserted > 0:
                        st.success(f"✅ {inserted} ردیف با موفقیت از اکسل وارد دفتر مالی شد.")
                        st.rerun()
                    else:
                        st.error("هیچ ردیفی با فرمت تاریخ شمسی معتبر (مثل 1403/07/15) پیدا نشد.")
            except Exception as e:
                st.error(f"خطا در پردازش فایل: {e}")


        # --- ثبت ردیف جدید (با تاریخ شمسی) ---
        st.markdown("---")
        st.subheader("➕ ثبت ردیف جدید در دفتر مالی")
        with st.form("add_finance_form"):
            col1, col2 = st.columns(2)
            with col1:
                f_date_j = st.text_input("تاریخ شمسی (مثال: 1403/07/15):", value=jdatetime.date.fromgregorian(date=date.today()).strftime("%Y/%m/%d"))
                subject_select = st.selectbox("موضوع پیش‌فرض:", ["حقوق سرایدار", "قبض برق", "قبض آب", "قبض گاز", "شارژ و واریزی واحد", "تعمیرات و نگهداری", "سایر"])
            with col2:
                custom_subject = st.text_input("توضیحات یا موضوع اختصاصی (اختیاری):", placeholder="در صورت تمایل متن دلخواه بنویسید")
                cost_val = st.number_input("مبلغ هزینه (ریال):", min_value=0.0, step=100000.0)
                dep_val = st.number_input("مبلغ واریزی (ریال):", min_value=0.0, step=100000.0)
                
            submitted_f = st.form_submit_button("💾 ثبت در دفتر مالی", use_container_width=True)
            if submitted_f:
                g_date = jalali_to_gregorian(f_date_j)
                if g_date is None:
                    st.error("فرمت تاریخ شمسی صحیح نیست. مثال صحیح: 1403/07/15")
                elif cost_val == 0 and dep_val == 0:
                    st.error("حداقل باید یکی از مقادیر هزینه یا واریزی بیشتر از صفر باشد.")
                else:
                    final_sub = custom_subject.strip() if custom_subject.strip() else subject_select
                    add_finance_entry(g_date, final_sub, cost_val, dep_val)
                    st.success("ردیف مالی با موفقیت ثبت شد.")
                    st.rerun()


    # تب ۴: ارسال و حذف اخطارها
    with admin_tab4:
        st.subheader("📢 ارسال و مدیریت اخطارهای مالی به واحدها")
        col_n1, col_n2 = st.columns([1, 1])

        with col_n1:
            st.markdown("##### ✍️ ارسال اخطار جدید")
            units_list = get_units()
            unit_choices = [str(u["unit_number"]) for u in units_list] if units_list else [str(i) for i in range(1, 11)]
            
            with st.form("send_notice_form"):
                target_unit = st.selectbox("انتخاب واحد:", unit_choices)
                notice_sub = st.text_input("موضوع اخطار:", placeholder="مثال: عدم پرداخت شارژ شهریور")
                notice_amt = st.number_input("مبلغ بدهی (ریال):", min_value=0.0, step=50000.0)
                notice_desc = st.text_area("متن توضیحات اخطار:", placeholder="توضیحات تکمیلی را اینجا وارد کنید...")
                submit_notice = st.form_submit_button("🚀 ارسال اخطار به واحد", use_container_width=True)
                
                if submit_notice:
                    if not notice_sub.strip():
                        st.error("لطفاً موضوع اخطار را وارد کنید.")
                    else:
                        send_payment_notice(target_unit, notice_sub.strip(), notice_amt, notice_desc.strip())
                        st.success(f"اخطار با موفقیت برای واحد {target_unit} ارسال شد.")
                        st.rerun()

        with col_n2:
            st.markdown("##### 📋 لیست اخطارهای فعال (امکان حذف)")
            active_notices = supabase.table("payment_notices").select("*").order("id", desc=True).execute().data or []
            if active_notices:
                for n in active_notices:
                    with st.container():
                        c_text, c_del = st.columns([3, 1])
                        with c_text:
                            st.write(f"🏢 **واحد {n['unit_number']}** | **{n['subject']}** | {int(n.get('amount', 0)):,} ریال")
                            if n.get("message"):
                                st.caption(f"توضیحات: {n['message']}")
                        with c_del:
                            if st.button("🗑️ حذف", key=f"del_not_{n['id']}"):
                                delete_payment_notice(n["id"])
                                st.success("اخطار حذف شد.")
                                st.rerun()
                        st.divider()
            else:
                st.info("هیچ اخطار فعالی در سامانه ثبت نشده است.")

# ==========================================
# ۲. پنل ساکنین
# ==========================================
else:
    res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
        "📅 رزرو استخر و پشت‌بام",
        "📜 سوابق رزروهای من",
        "📊 بیلان و هزینه‌های ساختمان",
        "⚠️ اخطارهای مالی واحد شما"
    ])
    
    # تب ۱: رزرو سانس جدید
    with res_tab1:
        st.subheader("ثبت درخواست رزرو جدید")
        fac = st.selectbox("انتخاب فضا:", ["pool", "roof_garden"], format_func=lambda x: "🏊‍♂️ استخر" if x == "pool" else "🌿 روف‌گاردن / پشت‌بام")
        res_date = st.date_input("تاریخ رزرو:", min_value=date.today(), value=date.today() + timedelta(days=1))
        
        slots = POOL_SLOTS if fac == "pool" else ROOF_SLOTS
        
        # بررسی سانس‌های رزرو شده
        existing = supabase.table("bookings").select("*").eq("facility", fac).eq("booking_date", str(res_date)).neq("status", "rejected").execute().data or []
        booked_times = [item["start_time"] for item in existing]
        
        slot_options = []
        for s, e in slots:
            if s in booked_times:
                slot_options.append(f"{s} تا {e} (❌ رزرو شده)")
            else:
                slot_options.append(f"{s} تا {e} (✅ آزاد)")
                
        selected_slot_str = st.selectbox("انتخاب سانس:", slot_options)
        
        if st.button("🚀 ثبت درخواست رزرو"):
            if "❌" in selected_slot_str:
                st.error("این سانس قبلاً رزرو شده است. لطفاً سانس دیگری را انتخاب کنید.")
            else:
                s_time = selected_slot_str.split(" تا ")[0].strip()
                e_time = selected_slot_str.split(" تا ")[1].split(" ")[0].strip()
                create_booking(st.session_state.user["id"], fac, res_date, s_time, e_time)
                st.success("درخواست رزرو ثبت شد و در انتظار تایید مدیریت قرار گرفت.")
                st.rerun()

        # تب ۲: رزروهای من
    with res_tab2:
        st.subheader("تاریخچه رزروهای واحد شما")
        my_bookings = supabase.table("bookings").select("*").eq("unit_id", st.session_state.user["id"]).order("booking_date", desc=True).execute().data or []
        if my_bookings:
            df_my = pd.DataFrame([{
                "فضا": "استخر" if b["facility"] == "pool" else "پشت‌بام",
                "تاریخ": to_jalali(b["booking_date"]),
                "ساعت": f"{b['start_time']} تا {b['end_time']}",
                "وضعیت": "🔴 تایید شده" if b["status"] in ["confirmed", "approved"] else ("🟠 در انتظار تایید" if b["status"] == "pending" else "⚪ رد شده")
            } for b in my_bookings])
            st.dataframe(df_my, use_container_width=True)
        else:
            st.info("تاکنون درخواستی ثبت نکرده‌اید.")


    # تب ۳: بیلان و هزینه‌های ساختمان (مشاهده برای ساکنان)
    with res_tab3:
        st.subheader("📊 گزارش گردش مالی و هزینه‌های ساختمان")
        ledger = get_finance_ledger()
        if ledger:
            df_view = pd.DataFrame([{
                "تاریخ": to_jalali(row.get("entry_date")),
                "موضوع": row.get("subject", "-"),
                "مبلغ هزینه (ریال)": f"{int(row.get('cost_amount', 0)):,}",
                "مبلغ واریزی (ریال)": f"{int(row.get('deposit_amount', 0)):,}",
                "بیلان (ریال)": f"{int(row.get('balance', 0)):,}"
            } for row in ledger])
            st.dataframe(df_view, use_container_width=True)
            
            last_bal = ledger[-1].get("balance", 0)
            color = "green" if last_bal >= 0 else "red"
            st.markdown(f"**مانده صندوق ساختمان:** :{color}[{int(last_bal):,} ریال]")
        else:
            st.info("هنوز رکوردی در دفتر مالی ثبت نشده است.")

    # تب ۴: اخطارهای مالی واحد
    with res_tab4:
        st.subheader("⚠️ اخطارها و بدهی‌های مالی واحد شما")
        my_unit = str(st.session_state.user.get("unit_number"))
        notices = supabase.table("payment_notices").select("*").eq("unit_number", my_unit).order("id", desc=True).execute().data or []
        
        if notices:
            for n in notices:
                st.error(f"🔴 **موضوع:** {n['subject']} | **مبلغ بدهی:** {int(n.get('amount', 0)):,} ریال\n\n📝 **توضیحات مدیر:** {n.get('message', '---')}")
        else:
            st.success("✅ واحد شما هیچ‌گونه بدهی یا اخطار معوقه‌ای ندارد.")
