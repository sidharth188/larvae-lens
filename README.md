# 🦟 Larvae Lens

AI-Based Mosquito Breeding Detection & Municipal Reporting System

---

## 📌 Project Overview

Larvae Lens is an AI-powered smart surveillance platform designed to detect mosquito breeding hotspots using stagnant water images.

The platform allows:

* Users to upload stagnant water images
* AI-based risk classification (HIGH / MEDIUM / LOW)
* Municipality dashboard for monitoring complaints
* WhatsApp alerts for high-risk zones
* GPS-based location tracking
* Priority escalation system using Razorpay
* IBM Watson Assistant chatbot integration
* Cloud-based data storage using IBM Cloudant

---

# 🚀 Technologies Used

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript

## Backend

* Python
* Flask
* Flask-CORS

## Database

* IBM Cloudant NoSQL Database

## Cloud Services

* IBM Cloud
* IBM Watson Assistant
* IBM App ID

## APIs & Integrations

* Twilio WhatsApp API
* Razorpay Payment Gateway
* Geolocation API

---

# ✨ Features

## 👤 User Dashboard

* User Signup/Login
* Personalized Welcome Message
* Upload Mosquito Breeding Reports
* GPS Location Tracking
* Complaint History
* Priority Municipal Escalation
* WhatsApp Emergency Alerts

## 🏢 Municipality Dashboard

* Real-time complaint monitoring
* Risk level tracking
* Complaint completion system
* Priority report identification
* Dynamic database updates

## 🤖 AI Features

* Stagnant water risk classification
* Automated HIGH-risk alerting
* Smart municipal reporting

---

# 📂 Project Structure

```bash
LarveLens/
│
├── backend/
│   ├── app.py
│   ├── ai_model/
│   ├── database/
│   ├── notification/
│   ├── uploads/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── userdashboard.html
│   ├── admindashboard.html
│   ├── css/
│   ├── js/
│   └── images/
│
└── README.md
```

---

# ⚙️ Installation Guide

## 1️⃣ Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/larvae-lens.git
```

---

## 2️⃣ Open Project

```bash
cd larvae-lens
```

---

## 3️⃣ Create Virtual Environment

```bash
python -m venv venv
```

---

## 4️⃣ Activate Environment

### Windows

```bash
venv\Scripts\activate
```

### Mac/Linux

```bash
source venv/bin/activate
```

---

## 5️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Create a `.env` file inside backend folder.

```env
CLOUDANT_USERNAME=your_username
CLOUDANT_PASSWORD=your_password
CLOUDANT_URL=your_cloudant_url

TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
YOUR_WHATSAPP_NUMBER=whatsapp:+91xxxxxxxxxx
```

---

# ▶️ Running Backend

Inside backend folder:

```bash
python app.py
```

Backend will run on:

```bash
http://127.0.0.1:5000
```

---

# ▶️ Running Frontend

Use VS Code Live Server.

Open:

```text
index.html
```

Frontend runs on:

```text
http://127.0.0.1:5500
```

---

# ☁️ IBM Cloud Setup

## IBM Cloudant

* Create Cloudant service
* Generate credentials
* Configure `.env`

## IBM App ID

* Create App ID service
* Configure authentication
* Enable login flow

## IBM Watson Assistant

* Create assistant
* Add web chat integration
* Paste integration script into frontend

---

# 📲 Twilio WhatsApp Setup

* Create Twilio account
* Activate Sandbox
* Add WhatsApp credentials to `.env`
* High-risk complaints trigger automatic alerts

---

# 💳 Razorpay Integration

Users can submit:

* Normal reports
* Priority Municipal Reports

Priority reports use Razorpay payment gateway.

---

# 🌐 Deployment Guide

# Frontend Deployment (GitHub Pages)

## Push Project to GitHub

```bash
git init
git add .
git commit -m "Initial Commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/larvae-lens.git
git push -u origin main
```

---

## Enable GitHub Pages

Go to:

```text
Repository → Settings → Pages
```

Select:

```text
Deploy from branch
```

Branch:

```text
main
```

Folder:

```text
/ root
```

Your frontend will deploy at:

```text
https://YOUR_USERNAME.github.io/larvae-lens
```

---

# Backend Deployment (Render)

## Create requirements.txt

```bash
pip freeze > requirements.txt
```

---

## Deploy on Render

Go to:

```text
https://render.com
```

Create:

```text
New Web Service
```

Connect GitHub repository.

---

## Build Command

```bash
pip install -r requirements.txt
```

---

## Start Command

```bash
gunicorn app:app
```

---

# 🔥 Important Deployment Fix

Replace all:

```javascript
http://127.0.0.1:5000
```

with:

```javascript
https://YOUR_RENDER_APP.onrender.com
```

inside frontend JS files.

---

# 🛡️ Security Notes

Add `.gitignore`

```text
venv/
.env
uploads/
__pycache__/
```

Never upload:

* API keys
* passwords
* .env file

---

# 📸 Screenshots

## Landing Page

* Dark-themed AI surveillance homepage

## User Dashboard

* Upload system
* Complaint history
* Priority reporting

## Municipality Dashboard

* Complaint monitoring
* Risk management

---

# 📈 Future Enhancements

* Real AI model training
* Mobile application
* Live map visualization
* SMS notifications
* Heatmap analytics
* IoT sensor integration
* Drone surveillance

---

# 👨‍💻 Developer

## Siddharth Sagar

MCA Student | AI & IoT Enthusiast

---

# 📄 License

This project is developed for educational and research purposes.

---

# ⭐ Larvae Lens

Smart AI Surveillance for Safer Cities.
