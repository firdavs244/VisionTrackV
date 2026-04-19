# VisionTrack

> Sanoat detallarining seriya raqamlarini kameralar orqali avtomatik aniqlash, tasdiqlash va kuzatish tizimi.

**Stack:** FastAPI · SQLAlchemy 2 (async) · PostgreSQL/SQLite · EasyOCR + Claude Vision · Vanilla JS frontend

---

## Xususiyatlar

- 🔐 **JWT auth** — access + refresh tokens, bcrypt parollar, role-based (`admin`/`operator`)
- 📷 **Hybrid OCR** — Claude Vision (sifat) + EasyOCR (tezlik) auto-fallback bilan
- 📊 **Statistika va analitika** — kunlik/haftalik trend, kameralar bo'yicha taqsimot
- 🔍 **Qidiruv va filtrlash** — sana, status, kamera, seriya bo'yicha
- 📝 **Audit log** — barcha amallar yozib boriladi
- 📤 **CSV eksport** — bir tugma bilan
- 🐳 **Docker-ready** — bitta `docker compose up` bilan ishga tushadi

---

## Tezkor boshlanish — SQLite (lokal)

> Eng tez yo'l: PostgreSQL kerak emas, faqat Python 3.11+

```powershell
# 1. Repo
git clone <repo-url> visiontrack
cd visiontrack

# 2. Virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Bog'liqliklar
pip install -r requirements.txt

# 4. .env (avtomatik yaratiladi: SQLite + EasyOCR)
copy .env.example .env

# 5. Migratsiya + boshlang'ich foydalanuvchilar
alembic upgrade head
python scripts/seed.py

# 6. Server
uvicorn backend.main:app --reload --port 8000
```

Brauzerda oching:

- Frontend: <http://localhost:8000/>
- API docs (Swagger): <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

**Demo akkauntlar:**

- `admin` / `admin123` (admin)
- `operator1` / `op123` (operator)

---

## Production — Docker Compose (PostgreSQL)

```bash
# 1. .env tayyorlang (kamida JWT_SECRET ni o'zgartiring)
cp .env.example .env

# 2. Build + run
docker compose up -d --build

# Birinchi marta — migratsiya va seed avtomatik bajariladi
docker compose logs -f app
```

---

## Konfiguratsiya (`.env`)

| O'zgaruvchi         | Default                                | Tavsif                                    |
| ------------------- | -------------------------------------- | ----------------------------------------- |
| `DATABASE_URL`      | `sqlite+aiosqlite:///./visiontrack.db` | SQLite yoki `postgresql+asyncpg://...`    |
| `JWT_SECRET`        | _kerak_                                | Kamida 32 belgi, prodda almashtiring      |
| `JWT_ACCESS_TTL`    | `900` (15 daq)                         | Access token muddati (sekund)             |
| `JWT_REFRESH_TTL`   | `604800` (7 kun)                       | Refresh token muddati                     |
| `OCR_BACKEND`       | `auto`                                 | `auto` / `groq` / `easyocr`              |
| `GROQ_API_KEY`      | _bo'sh_                                | Groq Vision uchun (yo'q bo'lsa EasyOCR)  |
| `MIN_CONFIDENCE`    | `70`                                   | Tasdiqlash uchun min ishonch %            |
| `MAX_UPLOAD_MB`     | `10`                                   | Maks rasm hajmi (MB)                      |
| `ALLOWED_ORIGINS`   | `["http://localhost:8000"]`            | CORS uchun                                |
| `LOG_LEVEL`         | `INFO`                                 | `DEBUG`/`INFO`/`WARNING`/`ERROR`          |

### OCR rejimini tanlash

| Rejim     | Qachon ishlatish                                            |
| --------- | ----------------------------------------------------------- |
| `auto`    | API key bor → Groq; yo'q → EasyOCR (tavsiya etiladi)      |
| `groq`    | Faqat Groq Vision (bepul, tez, internet kerak)              |
| `easyocr` | Faqat lokal (offline, bepul, lekin sekinroq + xotira ko'p)  |

---

## API yo'nalishlari

Barcha endpointlar `/api/v1/` prefiksi bilan.

### Auth

- `POST /auth/login` — login (form-data: username, password)
- `POST /auth/refresh` — access tokenni yangilash
- `POST /auth/logout` — chiqish
- `GET  /auth/me` — joriy foydalanuvchi

### Parts

- `GET    /parts/?page=1&limit=20&search=&status=&camera_id=&from_date=&to_date=`
- `GET    /parts/{id}`
- `PUT    /parts/{id}` — seriya tahrirlash
- `DELETE /parts/{id}`
- `POST   /parts/{id}/verify` — tasdiqlash
- `GET    /parts/export/csv`

### Scan

- `POST /scan/upload` — multipart: image + camera_id (+ min_confidence)
- `POST /scan/manual` — qo'lda yozuv

### Stats

- `GET /stats/overview`
- `GET /stats/weekly`
- `GET /stats/cameras`
- `GET /stats/activity`

### Cameras

- `GET    /cameras/`
- `GET    /cameras/{id}`
- `POST   /cameras/` (admin)
- `PUT    /cameras/{id}` (admin)
- `DELETE /cameras/{id}` (admin)

To'liq schema: <http://localhost:8000/docs>

---

## Testlar

```powershell
pip install -r requirements-dev.txt
pytest -v
```

---

## Loyiha tuzilishi

```
backend/
  main.py              # FastAPI app
  config.py            # pydantic-settings
  database.py          # async engine + get_db
  models/              # SQLAlchemy 2 ORM (User, Camera, Part, ActivityLog)
  schemas/             # Pydantic v2 schemas
  routers/             # auth, parts, scan, stats, cameras, health
  services/            # auth, parts, stats, activity, ocr/
  middleware/          # JWT auth, security headers
  utils/               # serial_validator, image_processor, file_validation
alembic/               # DB migratsiyalar
scripts/seed.py        # Boshlang'ich foydalanuvchilar va kameralar
frontend/index.html    # Single-page UI (vanilla JS)
tests/                 # pytest
uploads/               # Yuklangan rasmlar (gitignored)
```

---

## Xavfsizlik

- ✅ Bcrypt parollar (12 rounds)
- ✅ JWT access + refresh, qisqa muddat
- ✅ Rate limiting (slowapi) — login 10/min
- ✅ CORS allow-list (env orqali)
- ✅ Security headers (CSP, X-Frame-Options, HSTS, etc)
- ✅ File type + magic-bytes validatsiya
- ✅ SQL injection — parametrlangan querylar (SQLAlchemy)
- ✅ Path traversal himoyasi (uploads)

---

## Litsenziya

MIT
