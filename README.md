# Face Approval System

A secure web-based face recognition platform for member access management, built with Python (FastAPI), HTML, CSS, and JavaScript.

---

## 🚀 Features

- FastAPI backend with async MongoDB support
- Face registration & approval using the camera
- User management, admin panel, and action logs
- Modern responsive dashboard UI (HTML + CSS + JS)
- Compatible with Render, Heroku, Docker, Railway, and more

---

# 📂 Project Structure

```text
├── app.py # FastAPI backend
├── run.py # Local dev runner (optional)
├── requirements.txt
├── Procfile # Gunicorn for production platforms
├── Dockerfile # Docker build
├── health.py # Platform health checker
├── static/
│ ├── style.css
│ └── app.js
├── templates/
│ └── index.html
└── README.md
```

---

## Installation Methods

---

## 🛠️ Health & Troubleshooting

Check required files for target platform:
#### - Render
```python
python health.py --platform render
```

#### - Heroku
```python
python health.py --platform heroku
 ```

#### - Docker
```python
python health.py --platform docker
```

#### - Local Host
```python
python health.py --platform local
```

- For `"No face captured"` errors, confirm browser cookies and registration steps.
- Ensure your MongoDB is accessible from your server.

---

## 🧑‍💻 Customization

- Change theme in `static/style.css`
- Add API endpoints in `app.py`
- Extend functionality in `static/app.js`

---

## 📜 License

- [GNU/General Public License v3.0](https://github.com/real-ekansh/FaceApprovalSystem/blob/main/LICENSE)

---

## 🤝 Author

Made by [notrealekansh](https://github.com/real-ekansh)
