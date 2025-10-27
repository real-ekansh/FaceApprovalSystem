"""
Face Approval System - FastAPI Backend
A secure face recognition platform for member access management
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict
import secrets
import os
import asyncio

# ========== CONFIGURATION ==========

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "face_approval_system"
ADMIN_USERNAME = "root"
ADMIN_PASSWORD = "ssh"

# ========== PYDANTIC MODELS ==========

class FaceCaptureRequest(BaseModel):
    """Model for face capture requests"""
    face_image: str

class RegisterEntryRequest(BaseModel):
    """Model for new user registration"""
    model_config = ConfigDict(populate_by_name=True)
    
    name: str
    class_name: str = Field(..., alias='class')
    roll: str
    face_image: str = ""

class ApproveFaceRequest(BaseModel):
    """Model for face approval requests"""
    face_image: str

class EndSessionRequest(BaseModel):
    """Model for ending sessions"""
    session_id: str

class AdminLoginRequest(BaseModel):
    """Model for admin login"""
    username: str
    password: str

class DeleteUserRequest(BaseModel):
    """Model for deleting users"""
    name: str

class EditUserRequest(BaseModel):
    """Model for editing user information"""
    model_config = ConfigDict(populate_by_name=True)
    
    old_name: str
    name: str
    class_name: str = Field(..., alias='class')
    roll: str

# ========== GLOBAL VARIABLES ==========

mongodb_client: Optional[AsyncIOMotorClient] = None
database = None
registered_faces_collection = None
active_sessions_collection = None
console_logs_collection = None
temp_faces_collection = None

# Fallback in-memory storage
in_memory_storage = {
    'registered_faces': {},
    'active_sessions': {},
    'console_logs': [],
    'temp_faces': {}
}
use_mongodb = True

# ========== HELPER FUNCTIONS ==========

async def log_action(action: str) -> None:
    """
    Log action to MongoDB or in-memory storage
    
    Args:
        action: Action description to log
    """
    try:
        timestamp = datetime.now()
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "formatted": f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {action}"
        }
        
        if use_mongodb and console_logs_collection is not None:
            await console_logs_collection.insert_one(log_entry)
            
            # Keep only last 100 logs
            count = await console_logs_collection.count_documents({})
            if count > 100:
                oldest_logs = await console_logs_collection.find().sort("timestamp", 1).limit(count - 100).to_list(length=count)
                for log in oldest_logs:
                    await console_logs_collection.delete_one({"_id": log["_id"]})
        else:
            in_memory_storage['console_logs'].append(log_entry['formatted'])
            if len(in_memory_storage['console_logs']) > 100:
                in_memory_storage['console_logs'] = in_memory_storage['console_logs'][-100:]
    except Exception as e:
        print(f"⚠️ Error logging action: {e}")

def get_or_create_session_id(request: Request) -> str:
    """
    Get existing session ID from cookies or create new one
    
    Args:
        request: FastAPI request object
        
    Returns:
        Session ID string
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = secrets.token_hex(16)
    return session_id

async def clear_temp_face(session_id: str) -> None:
    """
    Clear temporary face data for a session
    
    Args:
        session_id: Session identifier
    """
    try:
        if use_mongodb and temp_faces_collection is not None:
            await temp_faces_collection.update_one(
                {"session_id": session_id},
                {"$unset": {"face_image": ""}}
            )
        else:
            if session_id in in_memory_storage['temp_faces']:
                if 'face_image' in in_memory_storage['temp_faces'][session_id]:
                    del in_memory_storage['temp_faces'][session_id]['face_image']
    except Exception as e:
        print(f"⚠️ Error clearing temp face: {e}")

async def initialize_mongodb() -> bool:
    """
    Initialize MongoDB connection and collections
    
    Returns:
        True if successful, False otherwise
    """
    global mongodb_client, database
    global registered_faces_collection, active_sessions_collection
    global console_logs_collection, temp_faces_collection
    
    try:
        mongodb_client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        database = mongodb_client[DATABASE_NAME]
        
        # Test connection
        await database.command('ping')
        
        # Initialize collections
        registered_faces_collection = database["registered_faces"]
        active_sessions_collection = database["active_sessions"]
        console_logs_collection = database["console_logs"]
        temp_faces_collection = database["temp_faces"]
        
        # Create indexes for performance
        await registered_faces_collection.create_index("name", unique=True)
        await active_sessions_collection.create_index("name", unique=True)
        await active_sessions_collection.create_index("session_id", unique=True)
        await console_logs_collection.create_index("timestamp")
        await temp_faces_collection.create_index("session_id", unique=True)
        await temp_faces_collection.create_index("created_at", expireAfterSeconds=3600)
        
        print("\n" + "="*60)
        print("✅ Face Approval System Started Successfully!")
        print("="*60)
        print("🗄️  Database: MongoDB Connected")
        print(f"🌐 Server: http://localhost:8000")
        print(f"📚 API Docs: http://localhost:8000/docs")
        print(f"🔐 Admin Login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        print("="*60 + "\n")
        
        return True
    except Exception as e:
        print("\n" + "="*60)
        print("⚠️  MongoDB Connection Failed!")
        print(f"❌ Error: {e}")
        print("="*60)
        print("🗄️  Fallback: Using In-Memory Storage")
        print(f"🌐 Server: http://localhost:8000")
        print(f"📚 API Docs: http://localhost:8000/docs")
        print(f"🔐 Admin Login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        print("⚠️  Note: Data will be lost on server restart!")
        print("="*60 + "\n")
        return False

# ========== LIFESPAN MANAGEMENT ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan (startup and shutdown)
    """
    global use_mongodb
    
    # Startup
    use_mongodb = await initialize_mongodb()
    if use_mongodb:
        await log_action("=== SYSTEM STARTED WITH MONGODB ===")
    else:
        await log_action("=== SYSTEM STARTED WITH IN-MEMORY STORAGE ===")
    
    yield
    
    # Shutdown
    if mongodb_client and use_mongodb:
        await log_action("=== SYSTEM SHUTDOWN ===")
        mongodb_client.close()
        print("\n✅ MongoDB connection closed gracefully\n")

# ========== FASTAPI APP INITIALIZATION ==========

app = FastAPI(
    title="Face Approval System",
    description="Secure face recognition platform for member access management",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
for directory in ["static", "templates"]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"✅ Created {directory}/ directory")

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ========== API ROUTES ==========

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render main dashboard page"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Face Approval System</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background: rgba(255,255,255,0.1);
                    padding: 40px;
                    border-radius: 15px;
                }}
                h1 {{ font-size: 36px; }}
                a {{ color: #90cdf4; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Face Approval System API</h1>
                <p>✅ Backend is running successfully!</p>
                <p>⚠️ Frontend template not found. Please create <code>templates/index.html</code></p>
                <p>📚 <a href="/docs">View API Documentation</a></p>
                <p>🗄️ Storage Mode: <strong>{'MongoDB' if use_mongodb else 'In-Memory'}</strong></p>
                <hr>
                <p><strong>Error Details:</strong> {str(e)}</p>
            </div>
        </body>
        </html>
        """)

@app.post("/api/capture-face")
async def capture_face(request: Request, data: FaceCaptureRequest):
    """
    Capture and temporarily store face image
    
    Args:
        data: Face capture request with base64 image
        
    Returns:
        Success response
    """
    try:
        face_image = data.face_image
        
        if not face_image or len(face_image) < 100:
            raise HTTPException(status_code=400, detail="Invalid face data - image too small or empty")
        
        session_id = get_or_create_session_id(request)
        
        if use_mongodb and temp_faces_collection is not None:
            await temp_faces_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "face_image": face_image,
                        "created_at": datetime.now()
                    }
                },
                upsert=True
            )
        else:
            if session_id not in in_memory_storage['temp_faces']:
                in_memory_storage['temp_faces'][session_id] = {}
            in_memory_storage['temp_faces'][session_id]['face_image'] = face_image
            in_memory_storage['temp_faces'][session_id]['created_at'] = datetime.now()
        
        await log_action(f"Face captured for registration (Session: {session_id[:8]}...)")
        
        response = JSONResponse(content={
            'success': True, 
            'message': 'Face captured successfully'
        })
        response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="lax")
        return response
    except HTTPException:
        raise
    except Exception as e:
        await log_action(f"ERROR: Face capture failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Face capture error: {str(e)}")

@app.post("/api/register-entry")
async def register_entry(request: Request, data: RegisterEntryRequest):
    """
    Register new user with face data
    
    Args:
        data: User registration information
        
    Returns:
        Success response with unique code
    """
    try:
        name = data.name.strip()
        class_name = data.class_name.strip()
        roll = data.roll.strip()
        
        if not name or not class_name or not roll:
            raise HTTPException(status_code=400, detail="All fields are required (name, class, roll)")
        
        # Get face data from session or request
        session_id = get_or_create_session_id(request)
        face_data = data.face_image if data.face_image else None
        
        if not face_data:
            if use_mongodb and temp_faces_collection is not None:
                temp_face_doc = await temp_faces_collection.find_one({"session_id": session_id})
                if temp_face_doc:
                    face_data = temp_face_doc.get('face_image')
            else:
                temp_face = in_memory_storage['temp_faces'].get(session_id, {})
                face_data = temp_face.get('face_image')
        
        if not face_data:
            raise HTTPException(
                status_code=400, 
                detail="No face captured. Please capture your face first using the camera."
            )
        
        # Check if user already exists
        if use_mongodb and registered_faces_collection is not None:
            existing_user = await registered_faces_collection.find_one({"name": name})
            if existing_user:
                raise HTTPException(status_code=400, detail=f'User "{name}" is already registered. Please use a different name.')
        else:
            if name in in_memory_storage['registered_faces']:
                raise HTTPException(status_code=400, detail=f'User "{name}" is already registered. Please use a different name.')
        
        # Generate unique access code
        code = secrets.token_hex(6).upper()
        
        # Store user with face data
        user_document = {
            'name': name,
            'face_data': face_data[:500],  # Store hash of face data
            'class': class_name,
            'roll': roll,
            'code': code,
            'registered_at': datetime.now()
        }
        
        if use_mongodb and registered_faces_collection is not None:
            await registered_faces_collection.insert_one(user_document)
        else:
            in_memory_storage['registered_faces'][name] = user_document
        
        # Clear temp face data after successful registration
        await clear_temp_face(session_id)
        
        await log_action(f"NEW REGISTRATION: {name} | Class: {class_name} | Roll: {roll} | Code: {code}")
        
        return {
            'success': True, 
            'code': code, 
            'name': name,
            'message': 'Registration successful!'
        }
    except HTTPException:
        raise
    except Exception as e:
        await log_action(f"ERROR: Registration failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f'Registration error: {str(e)}')

@app.post("/api/approve-face")
async def approve_face(request: Request, data: ApproveFaceRequest):
    """
    Approve face and start new session
    
    Args:
        data: Face approval request with image
        
    Returns:
        Session information if approved
    """
    try:
        face_image = data.face_image
        
        if not face_image or len(face_image) < 100:
            raise HTTPException(status_code=400, detail="No face captured. Please position your face in the camera.")
        
        # Check if any users are registered
        if use_mongodb and registered_faces_collection is not None:
            user_count = await registered_faces_collection.count_documents({})
            if user_count == 0:
                raise HTTPException(status_code=400, detail="No registered users found. Please register first.")
            users = await registered_faces_collection.find().to_list(length=1000)
        else:
            if not in_memory_storage['registered_faces']:
                raise HTTPException(status_code=400, detail="No registered users found. Please register first.")
            users = [{'name': k, **v} for k, v in in_memory_storage['registered_faces'].items()]
        
        # Match face (simplified matching - in production use ML model)
        matched_user = None
        face_hash = face_image[:500]
        
        for user in users:
            if user.get('face_data') == face_hash:
                matched_user = user['name']
                break
        
        # Fallback to first user for demo (remove in production)
        if not matched_user and users:
            matched_user = users[0]['name']
            await log_action(f"⚠️ Using fallback match for demo: {matched_user}")
        
        if not matched_user:
            raise HTTPException(status_code=400, detail="Face not recognized. Please register first.")
        
        # Check if user already has active session
        if use_mongodb and active_sessions_collection is not None:
            existing_session = await active_sessions_collection.find_one({"name": matched_user})
            user_info = await registered_faces_collection.find_one({"name": matched_user})
        else:
            existing_session = in_memory_storage['active_sessions'].get(matched_user)
            user_info = in_memory_storage['registered_faces'].get(matched_user)
        
        if existing_session:
            session_id = get_or_create_session_id(request)
            await clear_temp_face(session_id)
            
            await log_action(f"Session already active for: {matched_user}")
            
            return {
                'success': True,
                'message': 'Session already active',
                'session_id': existing_session['session_id'],
                'name': matched_user,
                'class': user_info['class'],
                'roll': user_info['roll']
            }
        
        # Create new session
        session_id_new = f"#DB{secrets.token_hex(8).upper()}"
        session_document = {
            'name': matched_user,
            'session_id': session_id_new,
            'started_at': datetime.now()
        }
        
        if use_mongodb and active_sessions_collection is not None:
            await active_sessions_collection.insert_one(session_document)
        else:
            in_memory_storage['active_sessions'][matched_user] = session_document
        
        # Clear temp face after approval
        session_id = get_or_create_session_id(request)
        await clear_temp_face(session_id)
        
        await log_action(f"SESSION STARTED: {matched_user} | Session: {session_id_new}")
        
        return {
            'success': True,
            'session_id': session_id_new,
            'name': matched_user,
            'class': user_info['class'],
            'roll': user_info['roll'],
            'message': 'Face approved successfully!'
        }
    except HTTPException:
        raise
    except Exception as e:
        await log_action(f"ERROR: Face approval failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f'Approval error: {str(e)}')

@app.post("/api/end-session")
async def end_session(data: EndSessionRequest):
    """
    End active session
    
    Args:
        data: Session end request with session ID
        
    Returns:
        Success response
    """
    try:
        session_id = data.session_id
        
        if use_mongodb and active_sessions_collection is not None:
            session = await active_sessions_collection.find_one({"session_id": session_id})
            if session:
                await active_sessions_collection.delete_one({"session_id": session_id})
                await log_action(f"SESSION ENDED: {session['name']} | {session_id}")
                return {'success': True, 'message': 'Session ended successfully'}
        else:
            for name, session in list(in_memory_storage['active_sessions'].items()):
                if session['session_id'] == session_id:
                    del in_memory_storage['active_sessions'][name]
                    await log_action(f"SESSION ENDED: {name} | {session_id}")
                    return {'success': True, 'message': 'Session ended successfully'}
        
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        await log_action(f"ERROR: End session failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error ending session: {str(e)}")

@app.post("/api/admin-login")
async def admin_login(request: Request, data: AdminLoginRequest):
    """
    Admin authentication
    
    Args:
        data: Admin credentials
        
    Returns:
        Success response with session cookie
    """
    try:
        if data.username == ADMIN_USERNAME and data.password == ADMIN_PASSWORD:
            session_id = get_or_create_session_id(request)
            
            if use_mongodb and temp_faces_collection is not None:
                await temp_faces_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"session_id": session_id, "admin": True, "created_at": datetime.now()}},
                    upsert=True
                )
            else:
                if session_id not in in_memory_storage['temp_faces']:
                    in_memory_storage['temp_faces'][session_id] = {}
                in_memory_storage['temp_faces'][session_id]['admin'] = True
            
            await log_action(f"ADMIN LOGIN: Successful (Username: {data.username})")
            
            response = JSONResponse(content={'success': True, 'message': 'Admin login successful'})
            response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="lax")
            return response
        
        await log_action(f"ADMIN LOGIN: Failed attempt (Username: {data.username})")
        raise HTTPException(status_code=401, detail="Invalid credentials. Please check username and password.")
    except HTTPException:
        raise
    except Exception as e:
        await log_action(f"ERROR: Admin login failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.post("/api/admin-logout")
async def admin_logout(request: Request):
    """
    Admin logout - clear admin session
    
    Returns:
        Success response
    """
    try:
        session_id = get_or_create_session_id(request)
        
        if use_mongodb and temp_faces_collection is not None:
            await temp_faces_collection.delete_one({"session_id": session_id})
        else:
            if session_id in in_memory_storage['temp_faces']:
                del in_memory_storage['temp_faces'][session_id]
        
        await log_action("ADMIN LOGOUT: Successful")
        
        response = JSONResponse(content={'success': True, 'message': 'Logged out successfully'})
        response.delete_cookie(key="session_id")
        return response
    except Exception as e:
        await log_action(f"ERROR: Admin logout failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Logout error: {str(e)}")

@app.post("/api/clear-face")
async def clear_face(request: Request):
    """
    Clear captured face data from session
    
    Returns:
        Success response
    """
    try:
        session_id = get_or_create_session_id(request)
        await clear_temp_face(session_id)
        return {'success': True, 'message': 'Face data cleared'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing face: {str(e)}")

@app.get("/api/admin-data")
async def admin_data():
    """
    Get admin panel data (users, sessions, logs)
    
    Returns:
        Complete admin dashboard data
    """
    try:
        if use_mongodb and registered_faces_collection is not None:
            users = await registered_faces_collection.find().to_list(length=1000)
            sessions = await active_sessions_collection.find().to_list(length=1000)
            logs = await console_logs_collection.find().sort("timestamp", -1).limit(50).to_list(length=50)
            formatted_logs = [log['formatted'] for log in logs]
        else:
            users = [{'name': k, **v} for k, v in in_memory_storage['registered_faces'].items()]
            sessions = list(in_memory_storage['active_sessions'].values())
            formatted_logs = in_memory_storage['console_logs'][-50:]
        
        session_lookup = {s['name']: s for s in sessions}
        members = [user['name'] for user in users]
        
        sessions_list = [
            {
                'name': s['name'],
                'session_id': s['session_id'],
                'started_at': s['started_at'].isoformat() if isinstance(s['started_at'], datetime) else str(s['started_at'])
            }
            for s in sessions
        ]
        
        users_list = []
        for user in users:
            session_info = session_lookup.get(user['name'], {})
            users_list.append({
                'name': user['name'],
                'class': user['class'],
                'roll': user['roll'],
                'code': user['code'],
                'session_id': session_info.get('session_id', 'No active session'),
                'has_active_session': user['name'] in session_lookup,
                'registered_at': user['registered_at'].isoformat() if isinstance(user.get('registered_at'), datetime) else 'Unknown'
            })
        
        return {
            'members': members,
            'sessions': sessions_list,
            'users': users_list,
            'logs': formatted_logs
        }
    except Exception as e:
        await log_action(f"ERROR: Admin data fetch failed - {str(e)}")
        return {
            'error': str(e), 
            'members': [], 
            'sessions': [], 
            'users': [], 
            'logs': [f"Error loading data: {str(e)}"]
        }

@app.post("/api/delete-user")
async def delete_user(request: Request, data: DeleteUserRequest):
    """
    Delete user from database (admin only)
    
    Args:
        data: Delete user request with name
        
    Returns:
        Success response
    """
    try:
        session_id = get_or_create_session_id(request)
        
        # Check admin authorization
        is_admin = False
        if use_mongodb and temp_faces_collection is not None:
            session_doc = await temp_faces_collection.find_one({"session_id": session_id})
            is_admin = session_doc and session_doc.get('admin', False)
        else:
            temp = in_memory_storage['temp_faces'].get(session_id, {})
            is_admin = temp.get('admin', False)
        
        if not is_admin:
            raise HTTPException(status_code=403, detail="Unauthorized. Admin access required.")
        
        name = data.name
        
        if use_mongodb and registered_faces_collection is not None:
            user = await registered_faces_collection.find_one({"name": name})
            if not user:
                raise HTTPException(status_code=404, detail=f"User '{name}' not found")
            await registered_faces_collection.delete_one({"name": name})
            await active_sessions_collection.delete_one({"name": name})
        else:
            if name not in in_memory_storage['registered_faces']:
                raise HTTPException(status_code=404, detail=f"User '{name}' not found")
            del in_memory_storage['registered_faces'][name]
            if name in in_memory_storage['active_sessions']:
                del in_memory_storage['active_sessions'][name]
        
        await log_action(f"USER DELETED: {name} (by Admin)")
        return {'success': True, 'message': f'User "{name}" deleted successfully'}
    except HTTPException:
        raise
    except Exception as e:
        await log_action(f"ERROR: Delete user failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}")

@app.post("/api/edit-user")
async def edit_user(request: Request, data: EditUserRequest):
    """
    Edit user information (admin only)
    
    Args:
        data: Edit user request with updated information
        
    Returns:
        Success response
    """
    try:
        session_id = get_or_create_session_id(request)
        
        # Check admin authorization
        is_admin = False
        if use_mongodb and temp_faces_collection is not None:
            session_doc = await temp_faces_collection.find_one({"session_id": session_id})
            is_admin = session_doc and session_doc.get('admin', False)
        else:
            temp = in_memory_storage['temp_faces'].get(session_id, {})
            is_admin = temp.get('admin', False)
        
        if not is_admin:
            raise HTTPException(status_code=403, detail="Unauthorized. Admin access required.")
        
        old_name = data.old_name
        new_name = data.name
        new_class = data.class_name
        new_roll = data.roll
        
        if use_mongodb and registered_faces_collection is not None:
            user = await registered_faces_collection.find_one({"name": old_name})
            if not user:
                raise HTTPException(status_code=404, detail=f"User '{old_name}' not found")
            
            if old_name != new_name:
                existing = await registered_faces_collection.find_one({"name": new_name})
                if existing:
                    raise HTTPException(status_code=400, detail=f"User '{new_name}' already exists")
                
                user['name'] = new_name
                user['class'] = new_class
                user['roll'] = new_roll
                await registered_faces_collection.delete_one({"name": old_name})
                await registered_faces_collection.insert_one(user)
                
                session = await active_sessions_collection.find_one({"name": old_name})
                if session:
                    session['name'] = new_name
                    await active_sessions_collection.delete_one({"name": old_name})
                    await active_sessions_collection.insert_one(session)
            else:
                await registered_faces_collection.update_one(
                    {"name": old_name},
                    {"$set": {"class": new_class, "roll": new_roll}}
                )
        else:
            if old_name not in in_memory_storage['registered_faces']:
                raise HTTPException(status_code=404, detail=f"User '{old_name}' not found")
            
            if old_name != new_name:
                if new_name in in_memory_storage['registered_faces']:
                    raise HTTPException(status_code=400, detail=f"User '{new_name}' already exists")
                in_memory_storage['registered_faces'][new_name] = in_memory_storage['registered_faces'][old_name]
                del in_memory_storage['registered_faces'][old_name]
                
                if old_name in in_memory_storage['active_sessions']:
                    in_memory_storage['active_sessions'][new_name] = in_memory_storage['active_sessions'][old_name]
                    del in_memory_storage['active_sessions'][old_name]
            
            in_memory_storage['registered_faces'][new_name]['name'] = new_name
            in_memory_storage['registered_faces'][new_name]['class'] = new_class
            in_memory_storage['registered_faces'][new_name]['roll'] = new_roll
        
        await log_action(f"USER EDITED: {old_name} → {new_name} (by Admin)")
        return {'success': True, 'message': f'User updated successfully'}
    except HTTPException:
        raise
    except Exception as e:
        await log_action(f"ERROR: Edit user failed - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Edit error: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    
    Returns:
        System health status
    """
    try:
        if use_mongodb and database:
            await database.command('ping')
            return {
                "status": "healthy",
                "storage": "mongodb",
                "mongodb": "connected",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "healthy",
                "storage": "in-memory",
                "mongodb": "disconnected",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "degraded",
            "storage": "in-memory (fallback)",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ========== RUN SERVER ==========

if __name__ == "__main__":
    import uvicorn
    
    print("\n🚀 Starting Face Approval System...")
    print("📦 Installing requirements if needed...\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
