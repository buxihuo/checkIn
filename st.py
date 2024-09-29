# streamlit run  st.py --server.port 6006
import streamlit as st
from streamlit_js_eval import streamlit_js_eval, copy_to_clipboard, create_share_link, get_geolocation
import json,os
import sqlite3
from datetime import datetime
from streamlit_cookie import EncryptedCookieManager

deviceFlag = 0
st.title("打卡系统")
# 根据 User-Agent 判断设备类型
device_type = streamlit_js_eval(js_expressions="navigator.userAgent", key="getUserAgent")
if device_type is not None:
    if "Mobi" in device_type or "Android" in device_type:
        # st.write("您使用的是移动设备")
        deviceFlag = 1 
    elif "iPad" in device_type or "Tablet" in device_type:
        st.write("您使用的是平板设备,请使用移动设备打卡")
        deviceFlag = 0
    else:
        deviceFlag = 0
        st.warning("您使用的是桌面设备,请使用移动设备打卡")
    print(device_type)

# 使用 streamlit_js_eval 获取设备类型
cookies = EncryptedCookieManager(
    prefix="streamlit-cookie/",
    password=os.environ.get("COOKIES_PASSWORD", "My secret password"),
)

if not cookies.ready():
    # Wait for the component to load and send us current cookies.
    st.stop()

if deviceFlag:
    # 创建 SQLite 数据库连接
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # 创建表格，如果表格不存在
    c.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        department TEXT,
        date TEXT,
        check_in TEXT,
        check_in_location TEXT,
        check_out TEXT,
        check_out_location TEXT,
        UNIQUE(name, department, date)
    )
    ''')
    conn.commit()
    
    # 获取当前日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # 获取用户输入的姓名和部门
    nameStr = cookies['name'] if 'name' in cookies else ""
    name = st.text_input("请输入姓名",value = nameStr)

    # 部门选择框，默认值为“知识系统部”
    department_options = ['知识系统部', '其他']
    department = '知识系统部' # st.selectbox("请选择部门", options=department_options, index=department_options.index('知识系统部'))    
    # 位置输入框
    locationBox = True # st.checkbox("获取用户位置信息",value=True)
    
    # 确保用户输入了姓名
    if not name:
        st.warning("请先输入姓名")
    elif not locationBox:
        st.warning("请先获取位置")
    else:
        # 定义函数进行上班打卡
        if name != cookies.get('name'):
            cookies['name'] = name
            print(111)
        location = get_geolocation()
        if location:
            location = str(location['coords']['latitude']) + ',' + str(location['coords']['longitude'])
        st.write(f"位置： {location}")
        def check_in():
            current_time = datetime.now().strftime('%H:%M:%S')
            # 检查当天是否已有上班打卡记录
            c.execute("SELECT check_in FROM attendance WHERE name = ? AND department = ? AND date = ?", (name, department, current_date))
            record = c.fetchone()
            if record and record[0]:
                st.error("您今天已经打过上班卡，无法重复打卡。")
            else:
                # 插入新的上班打卡记录
                if location:
                    c.execute("INSERT OR IGNORE INTO attendance (name, department, date, check_in, check_in_location) VALUES (?, ?, ?, ?, ?)", 
                              (name, department, current_date, current_time, location))
                    conn.commit()
                    st.success(f"{name}, 您的上班打卡时间: {current_time}, 位置: {location}")
                else:
                    st.warning("位置获取失败")
        # 定义函数进行下班打卡
        def check_out():
            current_time = datetime.now().strftime('%H:%M:%S')
            # 检查当天是否已有下班打卡记录
            c.execute("SELECT check_out FROM attendance WHERE name = ? AND department = ? AND date = ?", (name, department, current_date))
            record = c.fetchone()
            if record and record[0]:
                st.error("您今天已经打过下班卡，无法重复打卡。")
            else:
                # 检查是否已经有上班记录，如果有，则更新下班打卡时间
                c.execute("SELECT check_in FROM attendance WHERE name = ? AND department = ? AND date = ?", (name, department, current_date))
                record = c.fetchone()
                if record and record[0]:
                    if location:
                        c.execute("UPDATE attendance SET check_out = ?, check_out_location = ? WHERE name = ? AND department = ? AND date = ?", 
                                  (current_time, location, name, department, current_date))
                        conn.commit()
                        st.success(f"{name}, 您的下班打卡时间: {current_time}, 位置: {location}")
                    else:
                        st.warning("位置获取失败")
                else:
                    st.error("请先打上班卡。")
    
        # Streamlit 按钮
        checkboxFlag = st.checkbox("确认打卡")
        checkInFlag = st.button("上班打卡")
        checkOutFlag = st.button("下班打卡")

        if checkInFlag or checkOutFlag:
            if not checkboxFlag:
                st.warning("请先勾选确认打卡")
            
        if checkboxFlag:
            if checkInFlag:
                check_in()
            if checkOutFlag:
                check_out()
            
        # 显示该用户当天的打卡记录
        c.execute("SELECT * FROM attendance WHERE name = ? AND department = ? AND date = ?", (name, department, current_date))
        record = c.fetchone()
        if record:
            st.write(f"今天的打卡记录: 上班时间: {record[4]} (位置: {record[5]}) 下班时间: {record[6]} (位置: {record[7]})")
        else:
            st.write("今天还没有打卡记录")
    
    # 关闭数据库连接
    conn.close()
