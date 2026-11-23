import streamlit as st
from supabase import create_client
from passlib.hash import pbkdf2_sha256
from datetime import datetime, timezone
import uuid
import mimetypes

st.set_page_config(page_title="ریاضی‌یار ۴", page_icon="🌸", layout="wide")

PINK = "#D94F91"
PALE = "#FCE7F3"
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'Vazirmatn', sans-serif; direction:rtl;}
.stApp {background:#fffafd;}
section[data-testid="stSidebar"] {background:#fff0f7;}
h1,h2,h3 {color:#9d2863;}
div.stButton > button {background:#d94f91;color:white;border:0;border-radius:12px;}
div.stButton > button:hover {background:#b83275;color:white;}
div[data-testid="stFileUploader"] {background:#fff4f9;border:1px dashed #e78ab8;border-radius:14px;padding:12px;}
footer {visibility:hidden;}
.creator {text-align:center;color:#a83270;border-top:1px solid #f3c6dc;padding:18px;margin-top:35px;font-weight:700;}
.smallnote {color:#8b6478;font-size:0.9rem;}
</style>
""", unsafe_allow_html=True)

def get_client():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        return create_client(url, key)
    except Exception:
        st.error("اتصال پایگاه داده تنظیم نشده است. راهنمای README را بخوانید و اطلاعات Supabase را در Streamlit Secrets قرار دهید.")
        st.stop()

sb = get_client()

def q(table):
    return sb.table(table)

def current_user():
    return st.session_state.get("user")

def is_role(*roles):
    u = current_user()
    return bool(u and u.get("role") in roles)

def school_ids_for_user(user):
    if user["role"] == "designer":
        return [x["id"] for x in q("schools").select("id").execute().data]
    return [user.get("school_id")] if user.get("school_id") else []

def safe_error(err):
    st.error("عملیات انجام نشد. دسترسی، اتصال و اطلاعات واردشده را بررسی کنید.")
    st.caption(str(err)[:250])

def footer():
    st.markdown('<div class="creator">🌸 طراح و سازنده سامانه: ملیکا فیض‌پور 🌸</div>', unsafe_allow_html=True)

def login():
    st.markdown("<h1 style='text-align:center'>🌸 ریاضی‌یار ۴</h1><p style='text-align:center'>سامانه آموزش و مدیریت ریاضی پایه هشتم</p>", unsafe_allow_html=True)
    with st.form("login"):
        username = st.text_input("نام کاربری")
        password = st.text_input("گذرواژه", type="password")
        ok = st.form_submit_button("ورود به سامانه", use_container_width=True)
    if ok:
        try:
            rows = q("users").select("*").eq("username", username.strip()).eq("active", True).limit(1).execute().data
            if rows and pbkdf2_sha256.verify(password, rows[0]["password_hash"]):
                st.session_state.user = rows[0]
                st.rerun()
            else:
                st.error("نام کاربری یا گذرواژه صحیح نیست.")
        except Exception as e:
            safe_error(e)
    st.info("ساخت حساب طراح اصلی و تنظیم اولیه در راهنمای README توضیح داده شده است.")

def select_school(label="مدرسه"):
    schools = q("schools").select("id,name").order("name").execute().data
    if not schools:
        st.warning("هنوز مدرسه‌ای ثبت نشده است.")
        return None
    opts = {x["name"]: x["id"] for x in schools}
    name = st.selectbox(label, list(opts))
    return opts[name]

def add_school():
    st.subheader("افزودن مدرسه")
    with st.form("add_school"):
        name = st.text_input("نام مدرسه")
        city = st.text_input("شهر / منطقه")
        manager_name = st.text_input("نام مدیر مدرسه")
        username = st.text_input("نام کاربری مدیر")
        password = st.text_input("گذرواژه اولیه مدیر", type="password")
        submit = st.form_submit_button("ثبت مدرسه و حساب مدیر")
    if submit:
        if not all([name.strip(), username.strip(), password, manager_name.strip()]):
            st.warning("لطفاً فیلدهای ضروری را کامل کنید.")
            return
        try:
            if q("users").select("id").eq("username", username.strip()).execute().data:
                st.error("این نام کاربری قبلاً استفاده شده است.")
                return
            sid = str(uuid.uuid4())
            q("schools").insert({"id":sid,"name":name.strip(),"city":city.strip(),"active":True}).execute()
            q("users").insert({"id":str(uuid.uuid4()),"username":username.strip(),"full_name":manager_name.strip(),
                "password_hash":pbkdf2_sha256.hash(password),"role":"school_admin","school_id":sid,"active":True}).execute()
            st.success("مدرسه و حساب مدیر ساخته شد.")
        except Exception as e: safe_error(e)

def manage_users():
    u = current_user()
    st.subheader("مدیریت معلمان و دانش‌آموزان")
    if u["role"] == "designer":
        sid = select_school()
    else:
        sid = u["school_id"]
        st.caption("مدرسه: " + str(q("schools").select("name").eq("id",sid).single().execute().data["name"]))
    if not sid: return
    with st.form("new_user"):
        role = st.selectbox("نوع حساب", ["teacher","student"])
        full_name = st.text_input("نام و نام خانوادگی")
        username = st.text_input("نام کاربری")
        password = st.text_input("گذرواژه اولیه", type="password")
        class_rows = q("classes").select("id,name").eq("school_id",sid).execute().data
        class_map = {x["name"]:x["id"] for x in class_rows}
        chosen_class = st.selectbox("کلاس (برای دانش‌آموز)", ["—"] + list(class_map))
        submit = st.form_submit_button("ایجاد حساب")
    if submit:
        if not all([full_name.strip(), username.strip(), password]):
            st.warning("نام، نام کاربری و گذرواژه ضروری است.")
        else:
            try:
                if q("users").select("id").eq("username",username.strip()).execute().data:
                    st.error("نام کاربری تکراری است.")
                else:
                    q("users").insert({"id":str(uuid.uuid4()),"username":username.strip(),"full_name":full_name.strip(),
                        "password_hash":pbkdf2_sha256.hash(password),"role":role,"school_id":sid,
                        "class_id":class_map.get(chosen_class),"active":True}).execute()
                    st.success("حساب کاربری ساخته شد.")
            except Exception as e: safe_error(e)
    st.markdown("**حساب‌های این مدرسه**")
    users = q("users").select("id,full_name,username,role,active").eq("school_id",sid).execute().data
    if users:
        st.dataframe([{"نام":x["full_name"],"نام کاربری":x["username"],"نقش":x["role"],"فعال":x["active"]} for x in users], use_container_width=True)
        ids = {f'{x["full_name"]} ({x["username"]})':x["id"] for x in users}
        chosen = st.selectbox("انتخاب حساب برای فعال/غیرفعال‌سازی", list(ids))
        if st.button("تغییر وضعیت حساب"):
            target = next(x for x in users if x["id"] == ids[chosen])
            q("users").update({"active":not target["active"]}).eq("id",target["id"]).execute()
            st.rerun()
    else: st.caption("هنوز حسابی ثبت نشده است.")

def manage_classes():
    u = current_user()
    st.subheader("مدیریت کلاس‌ها")
    sid = select_school() if u["role"] == "designer" else u["school_id"]
    if not sid: return
    with st.form("class_form"):
        name = st.text_input("نام کلاس (مثلاً هشتم الف)")
        grade = st.text_input("پایه", value="هشتم")
        submit = st.form_submit_button("ایجاد کلاس")
    if submit and name.strip():
        try:
            q("classes").insert({"id":str(uuid.uuid4()),"school_id":sid,"name":name.strip(),"grade":grade.strip()}).execute()
            st.success("کلاس ایجاد شد.")
        except Exception as e: safe_error(e)
    classes = q("classes").select("name,grade").eq("school_id",sid).execute().data
    if classes: st.dataframe([{"کلاس":x["name"],"پایه":x["grade"]} for x in classes], use_container_width=True)

def upload_content():
    u=current_user()
    st.subheader("بارگذاری محتوا در خود سایت")
    if u["role"] == "designer":
        sid=select_school("مدرسه مقصد")
    else: sid=u["school_id"]
    if not sid: return
    classes=q("classes").select("id,name").eq("school_id",sid).execute().data
    class_map={"همه کلاس‌های مدرسه":None}
    class_map.update({x["name"]:x["id"] for x in classes})
    with st.form("upload_form"):
        title=st.text_input("عنوان فایل")
        chapter=st.text_input("فصل / درس")
        audience=st.selectbox("مخاطبان",list(class_map))
        uploaded=st.file_uploader("انتخاب فایل از دستگاه",type=["pdf","mp4","mov","png","jpg","jpeg","docx","pptx"])
        publish=st.form_submit_button("بارگذاری و انتشار")
    if publish:
        if not uploaded or not title.strip():
            st.warning("عنوان و فایل را انتخاب کنید.")
            return
        try:
            ext=uploaded.name.rsplit(".",1)[-1].lower()
            path=f"{sid}/{uuid.uuid4()}.{ext}"
            mime=uploaded.type or mimetypes.guess_type(uploaded.name)[0] or "application/octet-stream"
            sb.storage.from_("learning-files").upload(path,uploaded.getvalue(),{"content-type":mime,"upsert":"false"})
            q("materials").insert({"id":str(uuid.uuid4()),"school_id":sid,"class_id":class_map[audience],
                "title":title.strip(),"chapter":chapter.strip(),"storage_path":path,"original_name":uploaded.name,
                "uploaded_by":u["id"],"created_at":datetime.now(timezone.utc).isoformat()}).execute()
            st.success("فایل با موفقیت در فضای آنلاین ذخیره و ثبت شد.")
        except Exception as e: safe_error(e)
    st.caption("فایل‌ها در مخزن خصوصی ذخیره می‌شوند و لینک عمومی ندارند.")

def show_materials():
    u=current_user()
    st.subheader("محتوای آموزشی")
    try:
        query=q("materials").select("*").eq("school_id",u["school_id"])
        if u["role"]=="student":
            query=query.or_(f"class_id.is.null,class_id.eq.{u.get('class_id')}")
        rows=query.order("created_at",desc=True).execute().data
        for m in rows:
            with st.expander(f"📘 {m['title']} — {m.get('chapter','')}"):
                st.write("نام فایل:",m["original_name"])
                if st.button("دریافت فایل",key="dl_"+m["id"]):
                    signed=sb.storage.from_("learning-files").create_signed_url(m["storage_path"],60)
                    st.link_button("باز کردن / دریافت فایل",signed["signedURL"])
    except Exception as e: safe_error(e)

def grades():
    u=current_user()
    st.subheader("نمرات و نتایج")
    if u["role"]=="designer":
        st.warning("برای حفظ حریم خصوصی، پنل طراح اصلی به نمرات، کارنامه‌ها و پاسخ‌های خصوصی آزمون دسترسی ندارد.")
        return
    if u["role"]=="student":
        rows=q("grades").select("subject,assessment,score,created_at").eq("student_id",u["id"]).execute().data
    elif u["role"]=="teacher":
        rows=q("grades").select("subject,assessment,score,created_at,student_id").eq("teacher_id",u["id"]).execute().data
    else:
        rows=q("grades").select("subject,assessment,score,created_at,student_id").eq("school_id",u["school_id"]).execute().data
    if rows:
        st.dataframe([{"درس":x["subject"],"ارزیابی":x["assessment"],"نمره":x["score"],"تاریخ":x["created_at"]} for x in rows],use_container_width=True)
    else: st.info("هنوز نمره‌ای ثبت نشده است.")
    if u["role"] in ("teacher","school_admin"):
        st.markdown("**ثبت نمره**")
        sid=u["school_id"]
        students=q("users").select("id,full_name").eq("school_id",sid).eq("role","student").execute().data
        if students:
            smap={x["full_name"]:x["id"] for x in students}
            with st.form("grade_form"):
                student=st.selectbox("دانش‌آموز",list(smap))
                subject=st.text_input("درس")
                assessment=st.text_input("عنوان آزمون / ارزیابی")
                score=st.number_input("نمره",min_value=0.0,max_value=20.0,step=0.25)
                save=st.form_submit_button("ثبت نمره")
            if save and subject.strip() and assessment.strip():
                try:
                    q("grades").insert({"id":str(uuid.uuid4()),"school_id":sid,"student_id":smap[student],
                        "teacher_id":u["id"],"subject":subject.strip(),"assessment":assessment.strip(),"score":score}).execute()
                    st.success("نمره ثبت شد.")
                    st.rerun()
                except Exception as e: safe_error(e)

def designer_dashboard():
    st.subheader("مدیریت کل سامانه")
    schools=q("schools").select("id,name,city,active").execute().data
    users=q("users").select("id,role,active").execute().data
    c1,c2,c3=st.columns(3)
    c1.metric("مدارس",len(schools)); c2.metric("معلمان",sum(x["role"]=="teacher" for x in users)); c3.metric("دانش‌آموزان",sum(x["role"]=="student" for x in users))
    st.markdown("**مدارس ثبت‌شده**")
    if schools: st.dataframe([{"مدرسه":x["name"],"شهر":x.get("city",""),"فعال":x["active"]} for x in schools],use_container_width=True)
    add_school()

def main():
    if not current_user():
        login(); footer(); return
    u=current_user()
    st.sidebar.markdown("## 🌸 ریاضی‌یار ۴")
    st.sidebar.write(f"کاربر: **{u['full_name']}**")
    st.sidebar.caption({"designer":"طراح اصلی","school_admin":"مدیر مدرسه","teacher":"معلم","student":"دانش‌آموز"}.get(u["role"],u["role"]))
    if st.sidebar.button("خروج"):
        st.session_state.clear(); st.rerun()
    if u["role"]=="designer":
        page=st.sidebar.radio("منو",["داشبورد اصلی","مدیریت کلاس‌ها","مدیریت کاربران","بارگذاری محتوا","محتوای آموزشی","نمرات"])
        if page=="داشبورد اصلی": designer_dashboard()
        elif page=="مدیریت کلاس‌ها": manage_classes()
        elif page=="مدیریت کاربران": manage_users()
        elif page=="بارگذاری محتوا": upload_content()
        elif page=="محتوای آموزشی": show_materials()
        else: grades()
    else:
        pages=["صفحه اصلی","محتوای آموزشی","نمرات"]
        if u["role"] in ("school_admin","teacher"): pages += ["مدیریت کلاس‌ها","مدیریت کاربران","بارگذاری محتوا"]
        page=st.sidebar.radio("منو",pages)
        if page=="صفحه اصلی":
            st.title("🌸 خوش آمدید به ریاضی‌یار ۴")
            st.write("سامانه آموزش و مدیریت ریاضی پایه هشتم")
        elif page=="محتوای آموزشی": show_materials()
        elif page=="نمرات": grades()
        elif page=="مدیریت کلاس‌ها": manage_classes()
        elif page=="مدیریت کاربران": manage_users()
        elif page=="بارگذاری محتوا": upload_content()
    footer()

if __name__=="__main__":
    main()
