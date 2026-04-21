<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { signInWithEmailAndPassword, signOut } from 'firebase/auth'
import { collection, addDoc, query, orderBy, getDocs } from 'firebase/firestore'
import { auth, db } from './firebase'
import Chart from 'chart.js/auto'

// --- APP STATE ---
const isLoggedIn = ref(false)
const email = ref('')
const password = ref('')
const currentTab = ref('monitor') // 'monitor' or 'history'

// --- PATIENT DATA ---
const patientName = ref('xxx')
const patientID = ref('BME-xxxx')
const currentHeartRate = ref(0)
const historyRecords = ref([])

// --- ECG CHART VARIABLES ---
let ecgChart = null
let ecgInterval = null
const maxDataPoints = 100
let timeCounter = 0

// Simulated ECG Pattern (P, Q, R, S, T wave approximation)
const ecgPattern = [0, 0.1, 0.2, 0.1, 0, 0, -0.2, 1.5, -0.5, 0, 0.1, 0.3, 0.4, 0.2, 0, 0, 0, 0, 0, 0]
let patternIndex = 0

// --- AUTHENTICATION ---
async function login() {
  try {
    await signInWithEmailAndPassword(auth, email.value, password.value)
    isLoggedIn.value = true
    setTimeout(initChart, 500) // Start chart after UI loads
  } catch (error) {
    alert("Login failed: " + error.message)
  }
}

function logout() {
  signOut(auth)
  isLoggedIn.value = false
  if (ecgInterval) clearInterval(ecgInterval)
}

// --- LIVE ECG CHART LOGIC ---
function initChart() {
  const ctx = document.getElementById('ecgCanvas')
  if (!ctx) return

  ecgChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array(maxDataPoints).fill(''),
      datasets: [{
        label: 'ECG Amplitude (mV)',
        borderColor: '#27ae60', // Medical Green
        borderWidth: 2,
        pointRadius: 0, // Hide dots for smooth line
        tension: 0.4,
        data: Array(maxDataPoints).fill(0)
      }]
    },
    options: {
      responsive: true,
      animation: false, // Turn off animation for real-time speed
      scales: {
        y: { min: -1, max: 2, grid: { color: '#e0e0e0' } },
        x: { grid: { color: '#e0e0e0' } }
      }
    }
  })

  // Start feeding data every 50ms
  ecgInterval = setInterval(updateECG, 50)
}

function updateECG() {
  // Get next point in the ECG pattern, add slight random noise
  let nextValue = ecgPattern[patternIndex] + (Math.random() * 0.05 - 0.02)
  patternIndex = (patternIndex + 1) % ecgPattern.length

  // Calculate fake HR based on the loop
  currentHeartRate.value = Math.floor(60 + (Math.random() * 10))

  // Update chart arrays
  ecgChart.data.datasets[0].data.push(nextValue)
  ecgChart.data.datasets[0].data.shift() // remove oldest
  ecgChart.update()
}

// --- FIREBASE CLOUD STORAGE ---
async function saveRecord() {
  try {
    await addDoc(collection(db, "ecg_records"), {
      patientID: patientID.value,
      patientName: patientName.value,
      heartRate: currentHeartRate.value,
      timestamp: new Date().toLocaleString(),
      timestampRaw: new Date() // For sorting
    })
    alert("ECG Snapshot & Vitals saved to secure cloud.")
  } catch (e) {
    alert("Database Error: " + e.message)
  }
}

async function fetchHistory() {
  currentTab.value = 'history'
  historyRecords.value = [] // clear old
  try {
    const q = query(collection(db, "ecg_records"), orderBy("timestampRaw", "desc"))
    const snapshot = await getDocs(q)
    snapshot.forEach(doc => {
      historyRecords.value.push(doc.data())
    })
  } catch (e) {
    console.error(e)
  }
}

function showMonitor() {
  currentTab.value = 'monitor'
  setTimeout(initChart, 100) // Re-init chart when switching back
}

onUnmounted(() => {
  if (ecgInterval) clearInterval(ecgInterval)
})
</script>

<template>
  <div class="app-wrapper">
    <!-- LOGIN SCREEN -->
    <div v-if="!isLoggedIn" class="login-screen">
      <div class="card login-card">
        <h2>⚕️ Clinical Login</h2>
        <p>BME Real-Time ECG System</p>
        <input v-model="email" type="email" placeholder="Doctor Email (e.g. doctor@bme.edu)" />
        <input v-model="password" type="password" placeholder="Password" />
        <button class="btn-primary" @click="login">Secure Login</button>
      </div>
    </div>

    <!-- MAIN DASHBOARD -->
    <div v-else class="dashboard">
      <header class="top-nav">
        <div class="brand">🏥 BME TeleCardiology</div>
        <div class="nav-links">
          <button @click="showMonitor" :class="{ active: currentTab === 'monitor' }">Live ECG</button>
          <button @click="fetchHistory" :class="{ active: currentTab === 'history' }">Patient History</button>
          <button class="btn-danger" @click="logout">Logout</button>
        </div>
      </header>

      <main class="content">
        
        <!-- TAB 1: LIVE MONITOR -->
        <div v-if="currentTab === 'monitor'" class="monitor-grid">
          <!-- Patient Info Panel -->
          <div class="card patient-panel">
            <h3>Patient Information</h3>
            <label>Name:</label>
            <input v-model="patientName" type="text" />
            <label>ID / MRN:</label>
            <input v-model="patientID" type="text" />
            
            <div class="vitals">
              <h4>Live Heart Rate</h4>
              <div class="hr-display">
                <span class="heart">❤️</span> {{ currentHeartRate }} <span class="unit">BPM</span>
              </div>
            </div>

            <button class="btn-primary full-width" @click="saveRecord">☁️ Save Vitals to Cloud</button>
          </div>

          <!-- ECG Waveform Panel -->
          <div class="card ecg-panel">
            <h3>Live Lead II ECG</h3>
            <div class="canvas-container">
              <canvas id="ecgCanvas"></canvas>
            </div>
          </div>
        </div>

        <!-- TAB 2: HISTORY -->
        <div v-if="currentTab === 'history'" class="card history-panel">
          <h3>Historical Clinical Records</h3>
          <table class="history-table">
            <thead>
              <tr>
                <th>Date & Time</th>
                <th>Patient ID</th>
                <th>Name</th>
                <th>Avg Heart Rate</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(rec, index) in historyRecords" :key="index">
                <td>{{ rec.timestamp }}</td>
                <td>{{ rec.patientID }}</td>
                <td>{{ rec.patientName }}</td>
                <td><strong>{{ rec.heartRate }} BPM</strong></td>
              </tr>
            </tbody>
          </table>
          <p v-if="historyRecords.length === 0" class="text-muted">No records found in database.</p>
        </div>

      </main>
    </div>
  </div>
</template>

<style>
/* Reset & Base Styles */
* { box-sizing: border-box; font-family: 'Inter', system-ui, sans-serif; }
body { margin: 0; background-color: #f0f4f8; color: #2c3e50; }

.app-wrapper { min-height: 100vh; }

/* Cards */
.card {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05);
}

/* Login Screen */
.login-screen {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}
.login-card { width: 350px; text-align: center; }
.login-card input {
  width: 100%; padding: 12px; margin: 10px 0;
  border: 1px solid #ccc; border-radius: 6px;
}

/* Buttons */
button { cursor: pointer; padding: 10px 15px; border: none; border-radius: 6px; font-weight: bold; transition: 0.2s;}
.btn-primary { background: #3498db; color: white; }
.btn-primary:hover { background: #2980b9; }
.btn-danger { background: #e74c3c; color: white; }
.full-width { width: 100%; margin-top: 20px; padding: 15px; font-size: 1.1rem; }

/* Navigation */
.top-nav {
  display: flex; justify-content: space-between; align-items: center;
  background: #2c3e50; color: white; padding: 15px 30px;
}
.brand { font-size: 1.5rem; font-weight: 800; }
.nav-links button { background: transparent; color: white; margin-left: 10px; }
.nav-links button.active { border-bottom: 2px solid #3498db; border-radius: 0; }

/* Monitor Layout */
.content { padding: 30px; max-width: 1200px; margin: 0 auto; }
.monitor-grid { display: grid; grid-template-columns: 1fr 2.5fr; gap: 20px; }

/* Patient Panel */
.patient-panel label { display: block; margin-top: 15px; font-size: 0.9rem; color: #7f8c8d; }
.patient-panel input { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #bdc3c7; border-radius: 4px;}
.vitals { margin-top: 30px; text-align: center; background: #f8f9fa; padding: 20px; border-radius: 8px;}
.hr-display { font-size: 3rem; font-weight: bold; color: #2c3e50; }
.heart { animation: beat 1s infinite; display: inline-block; }
@keyframes beat { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.2); } }
.unit { font-size: 1rem; color: #7f8c8d; }

/* ECG Canvas */
.ecg-panel { position: relative; }
.canvas-container {
  width: 100%; height: 400px;
  background-image: linear-gradient(#e74c3c 1px, transparent 1px), linear-gradient(90deg, #e74c3c 1px, transparent 1px);
  background-size: 20px 20px; /* Medical graph paper effect */
  background-color: #fff9f9;
}

/* History Table */
.history-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
.history-table th, .history-table td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
.history-table th { background: #f4f6f7; }
</style>