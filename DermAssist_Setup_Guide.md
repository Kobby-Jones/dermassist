# DermAssist — Backend Setup & Flutter Integration Guide

> Run locally without Docker · Connect Flutter frontend · Deploy to AWS

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Set Up the PostgreSQL Database](#3-set-up-the-postgresql-database)
4. [Run the Backend Locally](#4-run-the-backend-locally)
5. [Connect Flutter to the Backend](#5-connect-flutter-to-the-backend)
6. [API Endpoint Reference](#6-api-endpoint-reference)
7. [Troubleshooting](#7-troubleshooting)
8. [Quick-Start Checklist](#8-quick-start-checklist)

---

## 1. Overview

DermAssist uses a Python/FastAPI backend with the OpenAI CLIP model (ViT-B/32) for zero-shot skin condition analysis. The Flutter mobile app communicates with the backend over HTTP.

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · CLIP ViT-B/32 · PostgreSQL |
| Frontend | Flutter / Dart · `http` · `flutter_secure_storage` |
| AI Model | OpenAI CLIP ViT-B/32 — zero-shot, no custom training needed |

---

## 2. Prerequisites

Install all of these before starting.

### Python 3.11
Download from https://www.python.org/downloads/ — tick **Add to PATH** during install.

```bash
# Verify
python --version    # should print Python 3.11.x
pip --version       # should print pip 23.x or higher
```

### PostgreSQL 16
Download from https://www.postgresql.org/download/ (use the graphical installer for Windows/macOS).

- During install, set a password for the `postgres` superuser — remember it, you'll need it later.
- Keep the default port `5432` unchanged.
- **pgAdmin 4** is installed alongside PostgreSQL — use it to manage the database visually.

### Git
Download from https://git-scm.com — required to install the CLIP library directly from GitHub.

### Flutter SDK
Download from https://docs.flutter.dev/get-started/install and follow the guide for your OS.

```bash
flutter doctor    # run this to check everything is configured
```

---

## 3. Set Up the PostgreSQL Database

You only need to do this once.

### Step 1 — Open pgAdmin 4
Launch pgAdmin from your Start Menu / Applications folder and connect to the local PostgreSQL server using the password you set during install.

### Step 2 — Create the database
Right-click **Databases → Create → Database**, enter the name `dermassist_db`, and click Save.

> The tables (`users`, `analysis_records`) are created automatically the first time you start the backend — you don't need to run any SQL for that.

### Step 3 — Create a dedicated database user (recommended)
Open the Query Tool (**Tools → Query Tool**) and run:

```sql
CREATE USER dermassist WITH PASSWORD 'dermassistpass';
GRANT ALL PRIVILEGES ON DATABASE dermassist_db TO dermassist;
```

You can use any username/password you like — just match them in the `.env` file below.

---

## 4. Run the Backend Locally

### 4.1 Open the project folder

Place the `dermassist_backend/` folder anywhere on your computer, then open a terminal inside it:

```bash
cd path/to/dermassist_backend
```

### 4.2 Create a virtual environment

```bash
# Create
python -m venv venv

# Activate — Windows:
venv\Scripts\activate

# Activate — macOS / Linux:
source venv/bin/activate
```

Your terminal prompt will now show `(venv)` to confirm it's active.

### 4.3 Install dependencies

> **Note:** The CLIP library is cloned directly from GitHub, so Git must be installed.

```bash
pip install -r requirements.txt
```

This installs FastAPI, PyTorch, CLIP, SQLAlchemy, passlib, python-jose, and all other dependencies. It may take a few minutes on first run because PyTorch is large (~200 MB).

### 4.4 Create the `.env` file

Copy `.env.example` to `.env` in the same folder and fill in your values:

```env
# .env

DATABASE_URL=postgresql://dermassist:dermassistpass@localhost:5432/dermassist_db

# Generate a strong secret by running:
#   python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=paste_your_generated_secret_here

JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_ENV=development
ALLOWED_ORIGINS=*
```

> Make sure the `DATABASE_URL` username, password, and database name match what you created in Section 3.

### 4.5 Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see output like this:

```
INFO:     Started server process
INFO:     Waiting for application startup.
[CLIP] Loading ViT-B/32 on cpu ...
[CLIP] Model ready.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> **First startup only:** The CLIP model weights (~350 MB) are downloaded and cached in `~/.cache/clip/`. Subsequent startups are fast.

### 4.6 Verify it's working

Open your browser and visit:

```
http://localhost:8000/docs
```

You'll see the interactive Swagger UI listing all API endpoints. You can test register, login, and analyze directly from the browser.

---

## 5. Connect Flutter to the Backend

### 5.1 Add Flutter packages

Open `pubspec.yaml` in your Flutter project and ensure these dependencies are present:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
  flutter_secure_storage: ^9.0.0
```

Then run:

```bash
flutter pub get
```

### 5.2 Copy the files into your project

Copy these files from the downloaded outputs into your Flutter project:

| File | Destination |
|------|-------------|
| `services/api_service.dart` | `lib/services/api_service.dart` |
| `login_screen.dart` | `lib/screens/login_screen.dart` |
| `register_screen.dart` | `lib/screens/register_screen.dart` |
| `processing_screen.dart` | `lib/screens/processing_screen.dart` |
| `result_screen.dart` | `lib/screens/result_screen.dart` |
| `history_screen.dart` | `lib/screens/history_screen.dart` |

> Create the `lib/services/` folder first if it doesn't already exist.

### 5.3 Set the backend URL

Open `lib/services/api_service.dart` and find `kBaseUrl` near the top:

```dart
const String kBaseUrl = 'http://10.0.2.2:8000';  // ← change this
```

Use the correct URL for your setup:

| Running Flutter on | Set `kBaseUrl` to |
|--------------------|-------------------|
| Android Emulator | `'http://10.0.2.2:8000'` |
| iOS Simulator | `'http://localhost:8000'` |
| Physical Android phone | `'http://YOUR_PC_IP:8000'` (e.g. `192.168.1.10`) |
| Physical iPhone | `'http://YOUR_PC_IP:8000'` (e.g. `192.168.1.10`) |
| Production (AWS EC2) | `'https://your-elastic-ip-or-domain'` |

**Finding your PC's local IP:**

```bash
# Windows (run in Command Prompt):
ipconfig
# Look for IPv4 Address under your Wi-Fi adapter

# macOS / Linux:
ifconfig | grep 'inet '
```

> Your phone and PC must be on the **same Wi-Fi network** for a physical device to reach the local backend.

### 5.4 Allow cleartext HTTP on Android

Android blocks unencrypted HTTP by default. Open `android/app/src/main/AndroidManifest.xml` and add `android:usesCleartextTraffic="true"` to the `<application>` tag:

```xml
<application
    android:label="dermassist"
    android:usesCleartextTraffic="true"
    android:icon="@mipmap/ic_launcher">
    ...
```

> This is fine for local development. For production, use HTTPS and remove this line.

### 5.5 Run the app

```bash
flutter run
```

---

## 6. API Endpoint Reference

All endpoints are available interactively at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/auth/register` | Register new user — body: `{username, email, password}` |
| `POST` | `/auth/login` | Login — body: `{username, password}` — returns JWT token |
| `POST` | `/api/analyze` | Upload skin image — returns CLIP classification results |
| `GET` | `/api/history` | Get the current user's past analysis records |

The `/api/analyze` and `/api/history` endpoints require a valid JWT token in the `Authorization: Bearer <token>` header. The Flutter app handles this automatically via `api_service.dart`.

---

## 7. Troubleshooting

### Flutter can't reach the backend

- **Android emulator:** use `10.0.2.2`, not `localhost` or `127.0.0.1`
- **Physical device:** use your PC's local IP (`ipconfig` / `ifconfig`), not `localhost`
- **Firewall:** allow inbound connections on port `8000`
- **Same network:** your phone and PC must be on the same Wi-Fi
- **Android HTTP blocked:** add `android:usesCleartextTraffic="true"` (see Section 5.4)

### Database connection error on startup

- Check that PostgreSQL is running (pgAdmin shows the server status)
- Verify `DATABASE_URL` in `.env` matches your username, password, and database name exactly
- Make sure port `5432` is not blocked

### CLIP model not downloading

- Requires an internet connection on first startup (~350 MB)
- Model is cached in `~/.cache/clip/` after the first download
- If the download fails midway, delete the partial file in that cache folder and restart

### `pip install` fails

- Make sure the virtual environment is activated — you should see `(venv)` in the prompt
- Upgrade pip first: `python -m pip install --upgrade pip`
- If CLIP install fails, make sure Git is installed (it clones from GitHub)

### `MissingPluginException` for `flutter_secure_storage`

```bash
flutter clean && flutter pub get
flutter run
```

---

## 8. Quick-Start Checklist

### Backend
- [ ] PostgreSQL is running and `dermassist_db` database exists
- [ ] Virtual environment is activated (`(venv)` in terminal prompt)
- [ ] `.env` file has correct `DATABASE_URL` and a real `JWT_SECRET_KEY`
- [ ] `pip install -r requirements.txt` completed without errors
- [ ] `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` is running
- [ ] `http://localhost:8000/docs` loads in the browser

### Flutter
- [ ] `flutter pub get` run after adding `http` and `flutter_secure_storage` to `pubspec.yaml`
- [ ] `kBaseUrl` in `api_service.dart` set correctly for your device/emulator
- [ ] `android:usesCleartextTraffic="true"` added to `AndroidManifest.xml` (Android only)
- [ ] All 6 Dart files copied to the correct locations under `lib/`
- [ ] `flutter run` launches the app without compile errors
- [ ] Register a new account and upload a test image successfully

---

*DermAssist — University of Energy and Natural Resources, Group 3B*
*For educational use only. Not a medical diagnostic device.*
