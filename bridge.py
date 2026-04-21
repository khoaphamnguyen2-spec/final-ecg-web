import serial
import json
import firebase_admin
from firebase_admin import credentials, db
import time
import os  # Thêm thư viện này để xóa màn hình

# 1. Kết nối Firebase
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://healthmonitor-50ab9-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

current_patient_id = "guest"

def on_session_change(event):
    global current_patient_id
    if event.data:
        current_patient_id = event.data
        # Không in ra dòng này liên tục để tránh làm hỏng giao diện Dashboard

db.reference('active_session').listen(on_session_change)

# 2. Kết nối Serial
try:
    ser = serial.Serial('COM3', 115200, timeout=0.1)
    time.sleep(2) 
    print("✅ Đã kết nối với Arduino!")
except Exception as e:
    print(f"❌ Lỗi kết nối Serial: {e}")
    exit()

while True:
    if ser.in_waiting > 500:
        ser.reset_input_buffer()

    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8').strip()
            
            if line.startswith('{'):
                data = json.loads(line)
                
                # Gửi lên Firebase
                db.reference(f'patients/{current_patient_id}/live').set(data)

                # --- PHẦN FIX HIỂN THỊ: TẠO GIAO DIỆN DASHBOARD ---
                # Xóa màn hình Terminal (cls cho Windows, clear cho Mac/Linux)
                os.system('cls' if os.name == 'nt' else 'clear')

                print("====================================================")
                print(f"🏥 HỆ THỐNG GIÁM SÁT Y TẾ REAL-TIME")
                print("====================================================")
                print(f" PHIÊN KHÁM: {current_patient_id.upper()}")
                print("----------------------------------------------------")
                
                # Hiển thị các thông số quan trọng căn lề thẳng hàng
                # data.get('tên', 0) giúp tránh lỗi nếu Arduino thiếu dữ liệu
                print(f" ❤️ NHỊP TIM (BPM) : {data.get('bpm', 0):>5}")
                print(f" 🩸 SpO2 (%)      : {data.get('spo2', 0):>5}%")
                print(f" 🌡️ NHIỆT ĐỘ (°C)  : {data.get('temp', 0):>5.1f}°C")
                print(f" 📉 CHỈ SỐ IR      : {data.get('ir', 0):>5}") 
                print(f" 🚶 CHUYỂN ĐỘNG    : {'CÓ' if data.get('motion') else 'KHÔNG'}")
                
                print("----------------------------------------------------")
                print(f" ⏰ Cập nhật lúc  : {time.strftime('%H:%M:%S')}")
                print("====================================================")
                print(" (Nhấn Ctrl + C để dừng chương trình)")

                # Ghi log bất thường
                if (data.get('bpm', 0) > 100 or (data.get('bpm', 0) < 50 and data.get('bpm', 0) > 0)):
                    db.reference(f'patients/{current_patient_id}/notable_records').push({
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'bpm': data['bpm'],
                        'spo2': data['spo2'],
                        'status': 'Phát hiện nhịp tim bất thường'
                    })

        except Exception as e:
            # Nếu có lỗi (như JSON lỗi), bỏ qua để không làm hỏng giao diện
            pass

    # Nghỉ một chút để Terminal không bị nháy quá nhanh
    time.sleep(0.05)