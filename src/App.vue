<template>
  <div class="hospital-dashboard">
    <!-- 1. MÀN HÌNH ĐĂNG NHẬP -->
    <div v-if="!isLoggedIn" class="login-overlay">
      <div class="login-card">
        <div class="login-icon">⚕️</div>
        <h2>CLINICAL LOGIN</h2>
        <p>BME Real-Time Monitoring System</p>
        <div class="input-group">
          <input v-model="email" type="email" placeholder="Email bác sĩ..." />
          <input v-model="password" type="password" placeholder="Mật khẩu..." @keyup.enter="login" />
        </div>
        <button @click="login" :disabled="loading" class="login-btn">
          {{ loading ? 'ĐANG XÁC THỰC...' : 'XÁC THỰC BẢO MẬT' }}
        </button>
      </div>
    </div>

    <!-- 2. GIAO DIỆN CHÍNH -->
    <template v-else>
      <aside class="sidebar">
        <div class="sidebar-header">
          <div class="brand">🏥 BME TeleCardiology</div>
          <div class="patient-info-box">
            <p>BS: <b>{{ email.split('@')[0].toUpperCase() }}</b></p>
            <div class="patient-inputs">
              <label>Tên Bệnh nhân:</label>
              <input v-model="patientName" placeholder="Tên..." />
              <label>ID Bệnh nhân:</label>
              <input v-model="patientID" @change="syncSession" placeholder="ID (ví dụ: BN0005)..." />
              <button @click="syncSession" class="sync-btn">CẬP NHẬT PHIÊN</button>
            </div>
          </div>
          
          <nav class="nav-menu">
            <button @click="showMonitor" :class="{ active: currentTab === 'monitor' }">📊 Giám sát trực tiếp</button>
            <button @click="fetchHistory" :class="{ active: currentTab === 'history' }">📜 Lịch sử bệnh án</button>
          </nav>
          
          <button @click="logout" class="logout-btn">Đăng xuất</button>
        </div>

        <div v-if="currentTab === 'monitor'" class="alerts-section">
          <h3>⚠️ CẢNH BÁO (ID: {{patientID}})</h3>
          <div class="records-list">
            <div v-for="(record, index) in notableRecords" :key="index" class="record-card">
              <div class="record-time">{{ record.timestamp }}</div>
              <div class="record-data">❤️ {{ record.bpm }} BPM | 🩸 {{ record.spo2 }}%</div>
              <div class="record-status">{{ record.status }}</div>
            </div>
            <div v-if="notableRecords.length === 0" class="no-data">Không có cảnh báo</div>
          </div>
        </div>
      </aside>

      <main class="main-content">
        <template v-if="currentTab === 'monitor'">
          <header class="main-header">
            <h1>HỆ THỐNG GIÁM SÁT: {{ patientID }}</h1>
            <div class="status-bar"><span class="dot"></span> ĐANG NHẬN DỮ LIỆU TỪ ARDUINO</div>
          </header>

          <div class="stats-grid">
            <div class="stat-card bpm">
              <span class="label">❤️ NHỊP TIM</span>
              <div class="value-group"><span class="value">{{ stats.bpm }}</span><span class="unit">BPM</span></div>
            </div>
            <div class="stat-card spo2">
              <span class="label">🩸 SpO2</span>
              <div class="value-group"><span class="value">{{ stats.spo2 }}</span><span class="unit">%</span></div>
            </div>
            <div class="stat-card temp">
              <span class="label">🌡️ NHIỆT ĐỘ</span>
              <div class="value-group"><span class="value">{{ stats.temp }}</span><span class="unit">°C</span></div>
            </div>
            <div class="stat-card motion" :class="{ 'motion-detected': stats.motion }">
              <span class="label">🚶 TRẠNG THÁI</span>
              <div class="value-group"><span class="value">{{ stats.motion ? 'CHUYỂN ĐỘNG' : 'YÊN TĨNH' }}</span></div>
            </div>
          </div>

          <!-- BIỂU ĐỒ IR THỰC TẾ (THAY CHO ECG GIẢ) -->
          <div class="chart-container main-ecg">
            <div class="chart-header">
              <h3>Real-Time Infrared (IR) Waveform - Sóng mạch thực</h3>
              <button class="save-btn" @click="saveSnapshot">☁️ Lưu hồ sơ Firestore</button>
            </div>
            <div class="ecg-canvas-wrapper">
              <canvas id="irChart"></canvas>
            </div>
          </div>

          <div class="trend-grid">
            <div class="chart-box"><h4>Xu hướng BPM</h4><canvas id="bpmTrendChart"></canvas></div>
            <div class="chart-box"><h4>Xu hướng SpO2</h4><canvas id="spo2TrendChart"></canvas></div>
          </div>
        </template>

        <template v-else>
          <header class="main-header"><h1>HỒ SƠ LƯU TRỮ TRÊN CLOUD</h1></header>
          <div class="card history-card">
            <table class="history-table">
              <thead>
                <tr><th>Thời gian</th><th>ID</th><th>Tên</th><th>HR (BPM)</th><th>SpO2</th></tr>
              </thead>
              <tbody>
                <tr v-for="(rec, index) in historyRecords" :key="index">
                  <td>{{ rec.timestamp }}</td>
                  <td>{{ rec.patientID }}</td>
                  <td>{{ rec.patientName }}</td>
                  <td><b>{{ rec.heartRate }}</b></td>
                  <td><b>{{ rec.spo2 }}%</b></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </main>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onUnmounted } from 'vue';
import Chart from 'chart.js/auto';

// FIREBASE
import { initializeApp } from "firebase/app";
import { getAuth, signInWithEmailAndPassword, signOut } from 'firebase/auth';
import { getDatabase, ref as dbRef, onValue, set, off } from "firebase/database";
import { getFirestore, collection, addDoc, query, orderBy, getDocs } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  databaseURL: import.meta.env.VITE_FIREBASE_DATABASE_URL,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const rtdb = getDatabase(app);
const fs = getFirestore(app);

const isLoggedIn = ref(false);
const loading = ref(false);
const email = ref('');
const password = ref('');
const currentTab = ref('monitor');

const patientName = ref('Guest');
const patientID = ref('guest');
const stats = ref({ bpm: 0, spo2: 0, temp: 0, motion: 0, ir: 0 });
const notableRecords = ref([]);
const historyRecords = ref([]);

let irChart, bpmTrendChart, spo2TrendChart;

// --- ĐĂNG NHẬP ---
const login = async () => {
  if (!email.value || !password.value) return;
  loading.value = true;
  try {
    await signInWithEmailAndPassword(auth, email.value, password.value);
    isLoggedIn.value = true;
  } catch (error) {
    alert("Lỗi đăng nhập: " + error.message);
  } finally {
    loading.value = false;
  }
};

// --- ĐỒNG BỘ VỚI PYTHON & FIREBASE ---
const syncSession = () => {
  if (!isLoggedIn.value) return;
  set(dbRef(rtdb, 'active_session'), patientID.value);
  
  // Ngắt kết nối cũ trước khi lắng nghe ID mới
  off(dbRef(rtdb, `patients/${patientID.value}/live`));

  onValue(dbRef(rtdb, `patients/${patientID.value}/live`), (snap) => {
    const data = snap.val();
    if (data) {
      stats.value = data;
      updateAllCharts(data);
    }
  });

  onValue(dbRef(rtdb, `patients/${patientID.value}/notable_records`), (snap) => {
    if (snap.val()) notableRecords.value = Object.values(snap.val()).reverse().slice(0, 10);
    else notableRecords.value = [];
  });
};

const logout = () => {
  set(dbRef(rtdb, 'active_session'), 'guest');
  signOut(auth);
  location.reload();
};

// --- KHỞI TẠO BIỂU ĐỒ ---
const initCharts = () => {
  const commonOptions = { 
    responsive: true, 
    maintainAspectRatio: false, 
    animation: false, 
    plugins: { legend: { display: false } },
    scales: { x: { display: false } }
  };

  // 1. Biểu đồ IR (Sóng mạch thực tế)
  const ctxIr = document.getElementById('irChart');
  if (irChart) irChart.destroy();
  irChart = new Chart(ctxIr, {
    type: 'line',
    data: { 
      labels: Array(100).fill(''), 
      datasets: [{ 
        data: Array(100).fill(null), 
        borderColor: '#2ecc71', 
        borderWidth: 2, 
        pointRadius: 0, 
        tension: 0.3,
        fill: true,
        backgroundColor: 'rgba(46, 204, 113, 0.1)'
      }] 
    },
    options: { 
      ...commonOptions, 
      scales: { 
        y: { 
          beginAtZero: false, 
          grace: '10%',
          grid: { color: 'rgba(0,0,0,0.05)' }
        },
        x: { display: false }
      } 
    }
  });

  // 2. Biểu đồ xu hướng BPM
  if (bpmTrendChart) bpmTrendChart.destroy();
  bpmTrendChart = new Chart(document.getElementById('bpmTrendChart'), {
    type: 'line',
    data: { labels: Array(30).fill(''), datasets: [{ data: [], borderColor: '#ff4757', tension: 0.4, pointRadius: 0 }] },
    options: commonOptions
  });

  // 3. Biểu đồ xu hướng SpO2
  if (spo2TrendChart) spo2TrendChart.destroy();
  spo2TrendChart = new Chart(document.getElementById('spo2TrendChart'), {
    type: 'line',
    data: { labels: Array(30).fill(''), datasets: [{ data: [], borderColor: '#3498db', tension: 0.4, pointRadius: 0 }] },
    options: commonOptions
  });
};

const updateAllCharts = (data) => {
  // Cập nhật biểu đồ IR (Sóng tức thời)
  if (irChart) {
    irChart.data.datasets[0].data.push(data.ir);
    if (irChart.data.datasets[0].data.length > 100) irChart.data.datasets[0].data.shift();
    irChart.update('none');
  }

  // Cập nhật biểu đồ xu hướng (BPM & SpO2)
  if (bpmTrendChart && spo2TrendChart) {
    bpmTrendChart.data.datasets[0].data.push(data.bpm);
    if (bpmTrendChart.data.datasets[0].data.length > 30) bpmTrendChart.data.datasets[0].data.shift();
    bpmTrendChart.update('none');

    spo2TrendChart.data.datasets[0].data.push(data.spo2);
    if (spo2TrendChart.data.datasets[0].data.length > 30) spo2TrendChart.data.datasets[0].data.shift();
    spo2TrendChart.update('none');
  }
};

// --- LỊCH SỬ CLOUD ---
const saveSnapshot = async () => {
  try {
    await addDoc(collection(fs, "medical_records"), {
      patientID: patientID.value,
      patientName: patientName.value,
      heartRate: stats.value.bpm,
      spo2: stats.value.spo2,
      timestamp: new Date().toLocaleString(),
      timestampRaw: new Date()
    });
    alert("Đã lưu hồ sơ bệnh án thành công!");
  } catch (e) { alert("Lỗi: " + e.message); }
};

const fetchHistory = async () => {
  currentTab.value = 'history';
  historyRecords.value = [];
  try {
    const q = query(collection(fs, "medical_records"), orderBy("timestampRaw", "desc"));
    const snapshot = await getDocs(q);
    snapshot.forEach(doc => historyRecords.value.push(doc.data()));
  } catch (e) { console.error(e); }
};

const showMonitor = async () => {
  currentTab.value = 'monitor';
  await nextTick();
  initCharts();
  syncSession();
};

watch(isLoggedIn, async (val) => {
  if (val) {
    await nextTick();
    initCharts();
    syncSession();
  }
});
</script>

<style scoped>
/* Giữ nguyên các Style đẹp của bạn */
.hospital-dashboard { display: flex; height: 100vh; width: 100vw; background: #f1f2f6; overflow: hidden; }
.sidebar { width: 280px; background: #2f3542; color: white; display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 20px; border-bottom: 1px solid #57606f; }
.brand { font-size: 1.1rem; font-weight: 800; color: #2ecc71; margin-bottom: 15px; }
.patient-inputs label { font-size: 0.7rem; color: #a4b0be; display: block; margin-top: 8px; }
.patient-inputs input { width: 100%; background: #3e4451; border: none; padding: 8px; border-radius: 4px; color: white; margin-top: 4px; font-size: 0.9rem; }
.sync-btn { width: 100%; margin-top: 10px; background: #1e90ff; color: white; border: none; padding: 8px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 0.7rem; }
.nav-menu { flex: 1; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
.nav-menu button { text-align: left; background: transparent; color: #ced6e0; padding: 12px; border-radius: 8px; border: none; cursor: pointer; }
.nav-menu button.active { background: #3498db; color: white; }
.alerts-section { padding: 15px; background: #1e222d; height: 250px; overflow-y: auto; }
.record-card { background: #2f3542; padding: 8px; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #ff4757; font-size: 0.75rem; }
.main-content { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
.main-header { display: flex; justify-content: space-between; align-items: center; }
.main-header h1 { font-size: 1.2rem; color: #2f3542; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.stat-card .label { font-size: 0.7rem; font-weight: bold; color: #747d8c; }
.stat-card .value { font-size: 1.8rem; font-weight: 800; display: block; margin-top: 5px; }
.stat-card .unit { font-size: 0.8rem; color: #a4b0be; }
.bpm .value { color: #ff4757; } .spo2 .value { color: #3498db; } .temp .value { color: #ffa502; }
.motion-detected { background: #e8f8f5; border: 1px solid #2ecc71; }
.main-ecg { background: white; padding: 15px; border-radius: 12px; }
.ecg-canvas-wrapper { height: 250px; width: 100%; background-color: #fffafa; background-image: linear-gradient(rgba(0,0,0,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.02) 1px, transparent 1px); background-size: 20px 20px; border: 1px solid #eee; }
.trend-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.chart-box { background: white; padding: 15px; border-radius: 12px; height: 180px; }
.history-table { width: 100%; border-collapse: collapse; background: white; }
.history-table th, td { padding: 12px; text-align: left; border-bottom: 1px solid #f1f2f6; font-size: 0.9rem; }
.login-overlay { position: fixed; inset: 0; background: #2f3542; display: flex; align-items: center; justify-content: center; z-index: 1000; }
.login-card { background: white; padding: 30px; border-radius: 15px; width: 350px; text-align: center; }
.login-btn { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 10px; }
.logout-btn { margin: 15px; padding: 8px; background: #e74c3c; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.dot { width: 8px; height: 8px; background: #2ecc71; border-radius: 50%; display: inline-block; animation: blink 1s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
</style>