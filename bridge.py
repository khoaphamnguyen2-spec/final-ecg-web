import serial
import json
import firebase_admin
from firebase_admin import credentials, db
import time

# 1. Kết nối Firebase
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://healthmonitor-50ab9-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# Biến lưu trữ ID bệnh nhân hiện tại (Mặc định là guest)
current_patient_id = "guest"

# Hàm lắng nghe khi bạn đổi ID trên giao diện Web (App.vue)
def on_session_change(event):
    global current_patient_id
    if event.data:
        current_patient_id = event.data
        print(f"\n🔔 ĐÃ CHUYỂN PHIÊN KHÁM: Bệnh nhân {current_patient_id}")

# Đăng ký lắng nghe biến active_session trên Firebase
db.reference('active_session').listen(on_session_change)

# 2. Kết nối Serial (Đảm bảo đúng cổng COM)
try:
    ser = serial.Serial('COM3', 115200, timeout=0.1)
    time.sleep(2) # Đợi Arduino ổn định
    print("✅ Đã kết nối với Arduino!")
    print("🚀 Đang truyền dữ liệu lên Cloud... (Nhấn Ctrl+C để dừng)")
except Exception as e:
    print(f"❌ Lỗi kết nối Serial: {e}")
    exit()

while True:
    # Chống lag: Nếu dữ liệu trong cổng COM bị dồn quá nhiều, xóa bớt
    if ser.in_waiting > 500:
        ser.reset_input_buffer()

    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8').strip()
            
            if line.startswith('{'):
                data = json.loads(line)
                
                # Đường dẫn lưu trữ: patients/ID_BENH_NHAN/...
                path_live = f'patients/{current_patient_id}/live'
                path_records = f'patients/{current_patient_id}/notable_records'

                # 1. Cập nhật dữ liệu Realtime (Dashboard)
                db.reference(path_live).set(data)

                # 2. Kiểm tra bất thường để lưu Hồ sơ bệnh án
                if (data['bpm'] > 100 or (data['bpm'] < 50 and data['bpm'] > 0)):
                    print(f"⚠️ CẢNH BÁO: Nhịp tim {data['bpm']} BPM! Đang lưu hồ sơ...")
                    db.reference(path_records).push({
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'bpm': data['bpm'],
                        'spo2': data['spo2'],
                        'status': 'Phát hiện nhịp tim bất thường'
                    })

                # 3. IN DỮ LIỆU RA TERMINAL (Để bạn không thấy máy bị treo)
                print(f"[{current_patient_id}] BPM: {data['bpm']} | SpO2: {data['spo2']}% | Temp: {data['temp']}°C", end='\r')

        except Exception as e:
            # Không in lỗi quá nhiều để tránh rối mắt
            pass