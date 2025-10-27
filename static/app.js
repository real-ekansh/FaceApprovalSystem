// ========== GLOBAL VARIABLES ==========
let videoStream = null;
let capturedFaceData = null;
let currentSessionId = null;

const mainSections = {
  introSection: document.getElementById('introSection'),
  faceSection: document.getElementById('faceSection'),
  cameraSection: document.getElementById('cameraSection'),
  addInfoSection: document.getElementById('addInfoSection'),
  approveCameraSection: document.getElementById('approveCameraSection'),
  sessionSection: document.getElementById('sessionSection'),
  adminLoginSection: document.getElementById('adminLoginSection'),
  adminPanelSection: document.getElementById('adminPanelSection')
};

// ========== HELPER FUNCTIONS ==========

async function clearFaceData() {
  try {
    await fetch('/api/clear-face', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'}
    });
    console.log('Face data cleared from backend');
  } catch (error) {
    console.error('Error clearing face data:', error);
  }
}

async function adminLogout() {
  try {
    const response = await fetch('/api/admin-logout', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'}
    });
    const data = await response.json();
    if (data.success) {
      console.log('Admin logged out');
    }
  } catch (error) {
    console.error('Error logging out:', error);
  }
}

function stopCamera() {
  if (videoStream) {
    videoStream.getTracks().forEach(track => track.stop());
    videoStream = null;
  }
}

function showSection(sectionId) {
  stopCamera();
  
  const currentSection = Object.keys(mainSections).find(key => 
    !mainSections[key].classList.contains('hidden')
  );
  
  if (sectionId !== 'cameraSection' && sectionId !== 'approveCameraSection') {
    clearFaceData();
    capturedFaceData = null;
  }
  
  if (currentSection === 'adminPanelSection' && sectionId !== 'adminPanelSection') {
    adminLogout();
  }
  
  Object.values(mainSections).forEach(sec => sec.classList.add('hidden'));
  mainSections[sectionId].classList.remove('hidden');
  
  if (sectionId === 'addInfoSection') {
    document.getElementById('addInfoForm').reset();
    document.getElementById('addInfoForm').classList.remove('hidden');
    document.getElementById('addInfoSuccess').classList.add('hidden');
  }
  
  if (sectionId === 'adminLoginSection') {
    document.getElementById('adminLoginForm').reset();
    document.getElementById('adminLoginMsg').textContent = '';
  }

  if (sectionId === 'cameraSection') {
    document.getElementById('capturePreview').classList.add('hidden');
    document.getElementById('video').style.display = 'block';
    document.getElementById('captureBtn').style.display = 'inline-block';
    document.getElementById('cancelCameraBtn').style.display = 'inline-block';
  }
}

// ========== NAVIGATION ==========

document.getElementById('nav-intro').onclick = () => {
  clearFaceData();
  showSection('introSection');
};

document.getElementById('nav-face').onclick = () => {
  clearFaceData();
  showSection('faceSection');
};

document.getElementById('nav-admin').onclick = () => {
  clearFaceData();
  showSection('adminLoginSection');
};

document.getElementById('faceRecogniseBtn').onclick = () => {
  clearFaceData();
  showSection('faceSection');
};

// ========== REGISTRATION FLOW ==========

document.getElementById('addEntryBtn').onclick = async () => {
  await clearFaceData();
  showSection('cameraSection');
  try {
    const video = document.getElementById('video');
    const constraints = { video: { width: 640, height: 480, facingMode: 'user' } };
    videoStream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = videoStream;
    await video.play();
    console.log('Camera started successfully');
  } catch (error) {
    alert('Camera Error: ' + error.message + '\n\nPlease allow camera access and try again.');
    console.error('Camera error:', error);
    showSection('faceSection');
  }
};

document.getElementById('cancelCameraBtn').onclick = () => {
  stopCamera();
  clearFaceData();
  capturedFaceData = null;
  showSection('faceSection');
};

document.getElementById('captureBtn').onclick = async () => {
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  
  capturedFaceData = canvas.toDataURL('image/jpeg', 0.8);
  
  document.getElementById('previewImage').src = capturedFaceData;
  document.getElementById('capturePreview').classList.remove('hidden');
  document.getElementById('video').style.display = 'none';
  document.getElementById('captureBtn').style.display = 'none';
  document.getElementById('cancelCameraBtn').style.display = 'none';
  
  try {
    const response = await fetch('/api/capture-face', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ face_image: capturedFaceData })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to capture face');
    }
    
    const data = await response.json();
    if (!data.success) {
      alert('Failed to capture face: ' + (data.message || 'Unknown error'));
    }
  } catch (error) {
    alert('Error capturing face: ' + error.message);
  }
};

document.getElementById('retakeBtn').onclick = async () => {
  await clearFaceData();
  document.getElementById('capturePreview').classList.add('hidden');
  document.getElementById('video').style.display = 'block';
  document.getElementById('captureBtn').style.display = 'inline-block';
  document.getElementById('cancelCameraBtn').style.display = 'inline-block';
  capturedFaceData = null;
};

document.getElementById('proceedToInfoBtn').onclick = () => {
  if (!capturedFaceData) {
    alert('Please capture your face first');
    return;
  }
  stopCamera();
  showSection('addInfoSection');
};

// ✅ FIXED: Registration form submission with proper error handling
document.getElementById('addInfoForm').onsubmit = async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  
  try {
    const response = await fetch('/api/register-entry', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name: formData.get('name'),
        class: formData.get('class'),
        roll: formData.get('roll')
      })
    });
    
    // ✅ FIX: Check if response is successful
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Registration failed');
    }
    
    const data = await response.json();
    
    // ✅ FIX: Now we know data.success exists
    if (data.success) {
      document.getElementById('registeredName').textContent = data.name;
      document.getElementById('generatedString').textContent = data.code;
      document.getElementById('addInfoForm').classList.add('hidden');
      document.getElementById('addInfoSuccess').classList.remove('hidden');
      capturedFaceData = null;
    } else {
      alert('Registration failed: ' + (data.message || 'Unknown error'));
    }
  } catch (error) {
    alert('Registration error: ' + error.message);
    console.error('Registration error:', error);
  }
};

function handlePostRegistration() {
  clearFaceData();
  showSection('faceSection');
}

// ========== APPROVAL FLOW ==========

document.getElementById('approveFaceBtn').onclick = async () => {
  await clearFaceData();
  showSection('approveCameraSection');
  try {
    const video = document.getElementById('approveVideo');
    const constraints = { video: { width: 640, height: 480, facingMode: 'user' } };
    videoStream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = videoStream;
    await video.play();
  } catch (error) {
    alert('Camera Error: ' + error.message);
    showSection('faceSection');
  }
};

document.getElementById('cancelApproveBtn').onclick = () => {
  stopCamera();
  clearFaceData();
  showSection('faceSection');
};

// ✅ FIXED: Face approval with proper error handling
document.getElementById('approveCaptureBtn').onclick = async () => {
  const video = document.getElementById('approveVideo');
  const canvas = document.getElementById('approveCanvas');
  const ctx = canvas.getContext('2d');
  
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  
  const faceData = canvas.toDataURL('image/jpeg', 0.8);
  
  try {
    const response = await fetch('/api/approve-face', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ face_image: faceData })
    });
    
    stopCamera();
    
    // ✅ FIX: Check response status first
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Face recognition failed');
    }
    
    const data = await response.json();
    
    if (data.success) {
      currentSessionId = data.session_id;
      document.getElementById('sessionUserName').textContent = data.name;
      document.getElementById('sessionClass').textContent = data.class;
      document.getElementById('sessionRoll').textContent = data.roll;
      document.getElementById('sessionString').textContent = data.session_id;
      await clearFaceData();
      showSection('sessionSection');
    } else {
      alert(data.message || 'Face not recognized. Please register first.');
      await clearFaceData();
      showSection('faceSection');
    }
  } catch (error) {
    alert('Approval error: ' + error.message);
    console.error('Approval error:', error);
    await clearFaceData();
    showSection('faceSection');
  }
};

// ========== SESSION MANAGEMENT ==========

document.getElementById('endSessionBtn').onclick = async () => {
  if (!currentSessionId) return;
  
  if (!confirm('Are you sure you want to end this session?')) return;
  
  try {
    const response = await fetch('/api/end-session', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ session_id: currentSessionId })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to end session');
    }
    
    const data = await response.json();
    if (data.success) {
      alert('✅ Session ended successfully');
      currentSessionId = null;
      showSection('introSection');
    } else {
      alert('Failed to end session: ' + (data.message || 'Unknown error'));
    }
  } catch (error) {
    alert('Error ending session: ' + error.message);
    console.error('Session end error:', error);
  }
};

// ========== THEME TOGGLE ==========

const themeSwitch = document.getElementById('themeSwitch');
const mainContent = document.getElementById('mainContent');
const themeLabel = document.getElementById('themeLabel');
let isDark = false;

themeSwitch.onclick = () => {
  isDark = !isDark;
  mainContent.classList.toggle('dark');
  themeSwitch.classList.toggle('dark');
  themeLabel.textContent = isDark ? "Dark" : "Light";
};

// ========== ADMIN PANEL ==========

document.getElementById('adminLoginForm').onsubmit = async (e) => {
  e.preventDefault();
  
  try {
    const response = await fetch('/api/admin-login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: document.getElementById('adminUser').value,
        password: document.getElementById('adminPass').value
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      document.getElementById('adminLoginMsg').textContent = '❌ ' + (errorData.detail || 'Invalid credentials');
      return;
    }
    
    const data = await response.json();
    if (data.success) {
      document.getElementById('adminLoginMsg').textContent = '';
      await loadAdminData();
      showSection('adminPanelSection');
    } else {
      document.getElementById('adminLoginMsg').textContent = '❌ Invalid credentials';
    }
  } catch (error) {
    document.getElementById('adminLoginMsg').textContent = '❌ Login failed: ' + error.message;
    console.error('Admin login error:', error);
  }
};

function logoutAdmin() {
  if (confirm('Are you sure you want to logout from admin panel?')) {
    adminLogout();
    showSection('adminLoginSection');
  }
}

async function loadAdminData() {
  try {
    const response = await fetch('/api/admin-data');
    
    if (!response.ok) {
      throw new Error('Failed to load admin data');
    }
    
    const data = await response.json();
    
    document.getElementById('memberCount').textContent = data.members.length;
    document.getElementById('sessionCount').textContent = data.sessions.length;
    
    const membersList = document.getElementById('approvedMembers');
    if (data.members.length > 0) {
      membersList.innerHTML = data.members.map(m => 
        `<li><span class="material-icons">person</span> ${m}</li>`
      ).join('');
    } else {
      membersList.innerHTML = '<li class="empty-state">No members registered yet</li>';
    }
    
    const sessionsList = document.getElementById('currentSessions');
    if (data.sessions.length > 0) {
      sessionsList.innerHTML = data.sessions.map(s => 
        `<li>
          <span class="material-icons">access_time</span>
          <strong>${s.name}</strong>: ${s.session_id}
          <br><small>Started: ${s.started_at}</small>
        </li>`
      ).join('');
    } else {
      sessionsList.innerHTML = '<li class="empty-state">No active sessions</li>';
    }
    
    const userInfoDiv = document.getElementById('userInfo');
    if (data.users.length > 0) {
      userInfoDiv.innerHTML = data.users.map(u => 
        `<div class="user-card-admin">
          <div class="user-info">
            <span class="material-icons user-icon-admin">account_circle</span>
            <div>
              <h4>${u.name}</h4>
              <p><strong>Class:</strong> ${u.class} | <strong>Roll:</strong> ${u.roll}</p>
              <p><strong>Code:</strong> ${u.code}</p>
              <p><strong>Session:</strong> ${u.session_id}</p>
              <p class="status ${u.has_active_session ? 'active' : 'inactive'}">
                ${u.has_active_session ? '🟢 Active' : '⚫ Inactive'}
              </p>
            </div>
          </div>
          <div class="user-actions">
            <button onclick="editUser('${u.name}', '${u.class}', '${u.roll}')" class="edit-btn">
              <span class="material-icons">edit</span> Edit
            </button>
            <button onclick="deleteUser('${u.name}')" class="delete-btn">
              <span class="material-icons">delete</span> Delete
            </button>
          </div>
        </div>`
      ).join('');
    } else {
      userInfoDiv.innerHTML = '<p class="empty-state">No users registered</p>';
    }
    
    const consoleView = document.getElementById('consoleView');
    if (data.logs.length > 0) {
      consoleView.textContent = data.logs.join('\n');
      consoleView.scrollTop = consoleView.scrollHeight;
    } else {
      consoleView.textContent = 'No logs yet...';
    }
  } catch (error) {
    console.error('Error loading admin data:', error);
    alert('Failed to load admin data: ' + error.message);
  }
}

function editUser(name, className, roll) {
  document.getElementById('editOldName').value = name;
  document.getElementById('editName').value = name;
  document.getElementById('editClass').value = className;
  document.getElementById('editRoll').value = roll;
  document.getElementById('editModal').classList.remove('hidden');
}

function closeEditModal() {
  document.getElementById('editModal').classList.add('hidden');
}

document.getElementById('editUserForm').onsubmit = async (e) => {
  e.preventDefault();
  
  try {
    const response = await fetch('/api/edit-user', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        old_name: document.getElementById('editOldName').value,
        name: document.getElementById('editName').value,
        class: document.getElementById('editClass').value,
        roll: document.getElementById('editRoll').value
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to update user');
    }
    
    const data = await response.json();
    if (data.success) {
      alert('✅ User updated successfully');
      closeEditModal();
      loadAdminData();
    } else {
      alert('❌ Failed to update: ' + (data.message || 'Unknown error'));
    }
  } catch (error) {
    alert('❌ Update error: ' + error.message);
    console.error('Edit user error:', error);
  }
};

async function deleteUser(name) {
  if (!confirm(`Are you sure you want to delete user "${name}"?\n\nThis action cannot be undone.`)) {
    return;
  }
  
  try {
    const response = await fetch('/api/delete-user', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ name: name })
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to delete user');
    }
    
    const data = await response.json();
    if (data.success) {
      alert('✅ User deleted successfully');
      await clearFaceData();
      loadAdminData();
    } else {
      alert('❌ Failed to delete: ' + (data.message || 'Unknown error'));
    }
  } catch (error) {
    alert('❌ Delete error: ' + error.message);
    console.error('Delete user error:', error);
  }
}

window.onclick = (event) => {
  const modal = document.getElementById('editModal');
  if (event.target === modal) {
    closeEditModal();
  }
};

// ========== PAGE LIFECYCLE ==========

window.addEventListener('load', () => {
  clearFaceData();
});

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopCamera();
  }
});

window.addEventListener('beforeunload', (e) => {
  if (videoStream) {
    e.preventDefault();
    e.returnValue = 'Camera is still active. Are you sure you want to leave?';
    return e.returnValue;
  }
});
