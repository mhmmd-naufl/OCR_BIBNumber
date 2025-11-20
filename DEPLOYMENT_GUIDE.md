# GitHub Deployment Guide

Panduan lengkap untuk mengupload project ke GitHub dengan benar.

## Step 1: Persiapan Local Repository

### Verifikasi `.gitignore`
Pastikan `.gitignore` sudah dibuat (seharusnya sudah ada):

```bash
git status
```

Output yang diharapkan (file yg akan di-ignore tercantum):
```
On branch main
nothing to commit, working tree clean
```

Jika melihat file yg seharusnya di-ignore, lakukan:
```bash
git rm -r --cached .  # Reset cache
git add .
git commit -m "Apply .gitignore"
```

### Verifikasi Files untuk Di-push

```bash
git status --short
```

**Seharusnya mencakup:**
- ✅ `ocr/*.py` (semua module code)
- ✅ `run.py`, `ocr_bib.py`
- ✅ `analyze_csv.py`
- ✅ `requirements.txt`
- ✅ `README.md`
- ✅ `CSV_LOGGING_GUIDE.md`
- ✅ `DEPLOYMENT_GUIDE.md`
- ✅ `.gitignore`
- ✅ `LICENSE` (jika ada)

**Seharusnya TIDAK mencakup:**
- ❌ `venv/` atau `env/`
- ❌ `__pycache__/`
- ❌ `videos/video_input.mp4`
- ❌ `tracking_results.csv`
- ❌ `*.pt` (model files)

## Step 2: Buat Repository di GitHub

1. Login ke https://github.com
2. Klik **"New"** (atau **"+" → "New repository"**)
3. Isi form:
   - **Repository name**: `ocr-bib-detection` (atau pilih sendiri)
   - **Description**: "Real-time BIB detection, tracking, and OCR system using YOLOv8 and ensemble OCR"
   - **Visibility**: Public (atau Private)
   - **Add .gitignore**: Pilih **Python** (tapi kita sudah punya custom)
   - **Add a README**: ❌ No (sudah kita buat)
   - **Add License**: Opsional (MIT, Apache 2.0, dll)
4. Klik **"Create repository"**

## Step 3: Push Local Repository ke GitHub

Setelah create repo, GitHub akan menunjukkan perintah. Ikuti salah satu:

### Opsi A: Fresh Push (Jika local blum ada git history)

```bash
cd "d:\Kuliah\MKI\Project\Test OCR"

# Inisialisasi git (jika belum ada)
git init

# Add semua files
git add .

# Commit pertama
git commit -m "Initial commit: OCR BIB detection system

- YOLOv8 person detection
- SimpleTracker for tracking
- EasyOCR + Tesseract ensemble
- Comprehensive CSV logging
- Performance optimized pipeline"

# Tambah remote GitHub
git remote add origin https://github.com/<USERNAME>/<REPO>.git

# Push ke main branch
git branch -M main
git push -u origin main
```

**Replace:**
- `<USERNAME>` dengan GitHub username
- `<REPO>` dengan repository name (contoh: `ocr-bib-detection`)

### Opsi B: Jika sudah ada local git

```bash
cd "d:\Kuliah\MKI\Project\Test OCR"

# Check remote
git remote -v

# Jika belum ada, add:
git remote add origin https://github.com/<USERNAME>/<REPO>.git

# Push
git push -u origin main
```

### Opsi C: Menggunakan Personal Access Token (lebih secure)

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate token dengan scope: `repo`
3. Copy token
4. Push dengan:

```bash
git push -u origin main
# Saat diminta username: gunakan username GitHub
# Saat diminta password: paste token (bukan password GitHub)
```

## Step 4: Verifikasi Upload

1. Buka https://github.com/<USERNAME>/<REPO>
2. Verifikasi:
   - ✅ Semua `.py` files terlihat
   - ✅ `README.md` tampil otomatis
   - ✅ Bukan file besar/tertutup (videos/, models/)
   - ✅ `requirements.txt` jelas

## Step 5: Setup GitHub untuk Kolaborasi (Optional)

### Add Topics
Klik **"About" → "Add topics"**:
- `yolov8`
- `ocr`
- `computer-vision`
- `tracking`
- `python`

### Enable Discussions (Optional)
Settings → Features → Enable **Discussions**

### Setup CI/CD (Optional - Untuk Advanced)

Buat `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Lint with flake8
      run: flake8 ocr/ --count --select=E9,F63,F7,F82 --show-source
```

## Step 6: Maintenance Going Forward

### Update Setelah Perubahan

```bash
cd "d:\Kuliah\MKI\Project\Test OCR"

# Edit files...

# Stage changes
git add .

# Commit dengan pesan deskriptif
git commit -m "Improve OCR accuracy with better preprocessing"

# Push
git push origin main
```

### Branch untuk Feature Baru

```bash
# Buat branch
git checkout -b feature/improve-tracking

# Edit & commit...
git add .
git commit -m "Improve tracker with faster IOU calculation"

# Push branch
git push origin feature/improve-tracking

# Di GitHub: Buat Pull Request untuk merge ke main
```

## Troubleshooting

### Error: "Repository not found"
**Penyebab**: URL salah atau token expired
**Solusi**: 
```bash
git remote -v  # Cek URL
git remote set-url origin https://github.com/<USERNAME>/<REPO>.git
```

### Error: "Authentication failed"
**Solusi 1 (Windows)**: Credential Manager sudah menyimpan credentials lama
- Settings → Credential Manager → Windows Credentials → Hapus GitHub entry
- Push lagi, masukkan username & token baru

**Solusi 2**: Setup SSH (lebih secure):
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add ke GitHub → Settings → SSH and GPG keys
# Push dengan SSH URL:
git remote set-url origin git@github.com:<USERNAME>/<REPO>.git
```

### File Besar Terdeteksi
**Error**: "File too large" saat push
**Solusi**:
```bash
# Check file besar
git ls-files --size | sort -rn | head

# Remove dari git history (jika sudah commit)
git filter-branch --tree-filter 'rm -f <LARGE_FILE>' HEAD

# Pastikan di .gitignore
echo "*.mp4" >> .gitignore
git add .gitignore
git commit -m "Add large files to gitignore"
```

## Quick Command Reference

```bash
# Setup awal
git init
git add .
git commit -m "Initial commit"
git remote add origin <URL>
git push -u origin main

# Update routine
git add .
git commit -m "Message"
git push

# Check status
git status
git log --oneline -10

# Branch operations
git checkout -b <BRANCH>
git merge <BRANCH>
git branch -d <BRANCH>
```

## Project Files Checklist untuk GitHub

**Harus Ada:**
- [ ] `ocr/` package (7 modules)
- [ ] `run.py` (main entry point)
- [ ] `requirements.txt` (dependencies)
- [ ] `README.md` (dokumentasi)
- [ ] `.gitignore` (exclude unnecessary files)

**Sangat Recommended:**
- [ ] `CSV_LOGGING_GUIDE.md` (logging schema)
- [ ] `DEPLOYMENT_GUIDE.md` (deployment instructions)
- [ ] `LICENSE` (jika public - MIT atau Apache 2.0)
- [ ] `.github/workflows/` (CI/CD - optional)

**Jangan Ada:**
- [ ] `venv/` atau virtual environment
- [ ] `videos/` atau media input besar
- [ ] `*.csv` output files
- [ ] `__pycache__/` atau `.pyc` files
- [ ] Model `.pt` files (auto-download)

---

## Next Steps After Deploy

1. **Announce**: Share di social media, forums, portfolio
2. **Showcase**: Buat demo video atau GIF di README
3. **Engage**: Monitor GitHub Issues & discussions
4. **Iterate**: Fix bugs, accept PRs, release versions

Selamat! Project sudah siap untuk GitHub! 🎉
