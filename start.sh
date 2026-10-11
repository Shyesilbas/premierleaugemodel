#!/usr/bin/env bash
# ==============================================================================
# Premier League Model Engine & Dashboard Başlatıcı
# Model Backend API (FastAPI) ve Web Dashboard (React/Vite) birlikte başlatır.
# ==============================================================================

set -e

# Projenin kök dizinine geç
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Renkler
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}====================================================${NC}"
echo -e "${BOLD}${CYAN}   ⚽ PREMIER LEAGUE MODEL & DASHBOARD LAUNCHER     ${NC}"
echo -e "${BOLD}${CYAN}====================================================${NC}"

# Python3 ve Node kontrolü
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[HATA] python3 bulunamadı. Lütfen Python 3.10+ kurulu olduğundan emin olun.${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}[HATA] npm bulunamadı. Lütfen Node.js kurulu olduğundan emin olun.${NC}"
    exit 1
fi

# Port çakışmasını engellemek için eski oturumları temizleme fonksiyonu
free_port() {
    local port=$1
    local pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}[TEMİZLİK] Port :$port üzerindeki önceki süreçler sonlandırılıyor (PID: $pids)...${NC}"
        kill -9 $pids 2>/dev/null || true
        sleep 0.5
    fi
}

free_port 8000
free_port 5173

# Frontend bağımlılık kontrolü
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}[BİLGİ] frontend/node_modules bulunamadı. Bağımlılıklar yükleniyor...${NC}"
    npm --prefix frontend install
fi

# Kapanış temizlik fonksiyonu (Ctrl+C yakalayıcı)
cleanup() {
    echo -e "\n${YELLOW}[KAPANIŞ] Servisler güvenle durduruluyor...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    echo -e "${GREEN}[OK] Tüm süreçler kapatıldı. İyi çalışmalar!${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Backend FastAPI Model API'yi başlat
echo -e "${GREEN}[1/2] Model Backend API başlatılıyor (FastAPI - Port: 8000)...${NC}"
python3 -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Backend'in ayağa kalkmasını kısa süre bekle
sleep 1.5

# 2. Frontend React / Vite Dashboard'u başlat
echo -e "${GREEN}[2/2] Web Arayüzü başlatılıyor (Vite - Port: 5173)...${NC}"
npm --prefix frontend run dev &
FRONTEND_PID=$!

echo -e ""
echo -e "${BOLD}${GREEN}✔ SİSTEM HAZIR VE AKTİF!${NC}"
echo -e "${CYAN}----------------------------------------------------${NC}"
echo -e " 🌐 ${BOLD}Web Dashboard:${NC}    ${CYAN}http://localhost:5173${NC}"
echo -e " ⚙️  ${BOLD}Model API:${NC}        ${CYAN}http://127.0.0.1:8000${NC}"
echo -e " 📖 ${BOLD}Swagger API Dokümantasyonu:${NC} ${CYAN}http://127.0.0.1:8000/docs${NC}"
echo -e "${CYAN}----------------------------------------------------${NC}"
echo -e "${YELLOW}Durdurmak için [CTRL + C] tuşlarına basın.${NC}\n"

# Süreçlerin arka planda devam etmesini bekle
wait
