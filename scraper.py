"""
Worten Outlet Laptop Scraper (GitHub Actions version)
Monitoriza a página de portáteis outlet da Worten e envia alertas via Telegram.
"""

import json
import hashlib
import re
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright

# === CONFIGURAÇÃO ===
URL = "https://www.worten.pt/outlet/informatica-e-acessorios/portateis"
SEEN_FILE = Path(__file__).parent / "seen_products.json"

# Lê do environment (GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Filtros
MIN_RAM_GB = int(os.environ.get("MIN_RAM_GB", "24"))
MAX_PRICE = float(os.environ.get("MAX_PRICE", "0"))


def load_seen() -> dict:
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_seen(seen: dict):
    SEEN_FILE.write_text(json.dumps(seen, indent=2, ensure_ascii=False), encoding="utf-8")


def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠ Telegram não configurado")
        return
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("  ✅ Telegram enviado")
    except Exception as e:
        print(f"  ⚠ Erro Telegram: {e}")


def extract_ram_gb(name: str) -> int:
    match = re.search(r'(\d+)\s*GB', name, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def extract_price(price_str: str) -> float:
    cleaned = re.sub(r'[^\d,.]', '', price_str).replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def matches_filters(name: str, price: float) -> bool:
    if MIN_RAM_GB > 0:
        ram = extract_ram_gb(name)
        if 0 < ram < MIN_RAM_GB:
            return False
    if MAX_PRICE > 0 < price > MAX_PRICE:
        return False
    return True


def scrape_worten() -> list[dict]:
    products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="pt-PT"
        )
        page = context.new_page()

        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(5000)

            # Scroll para carregar tudo
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(1000)

            # Tenta vários seletores
            selectors = [
                '[data-testid="product-card"]',
                '.product-card',
                '.w-product',
                'article[class*="product"]',
                '[class*="ProductCard"]',
                '[class*="productCard"]',
                'a[href*="portatil"]',
            ]

            product_elements = []
            for selector in selectors:
                product_elements = page.query_selector_all(selector)
                if product_elements:
                    print(f"  🎯 Seletor: {selector} ({len(product_elements)} resultados)")
                    break

            if not product_elements:
                # Fallback: guarda screenshot para debug
                page.screenshot(path=str(Path(__file__).parent / "debug_screenshot.png"))
                print("  ⚠ Nenhum seletor funcionou. Screenshot guardado para debug.")
                # Tenta extrair do HTML inteiro
                content = page.content()
                print(f"  ℹ Tamanho da página: {len(content)} caracteres")

            for elem in product_elements:
                try:
                    text = elem.inner_text().strip()
                    href_elem = elem if elem.get_attribute("href") else elem.query_selector("a")
                    href = ""
                    if href_elem:
                        href = href_elem.get_attribute("href") or ""
                        if href.startswith("/"):
                            href = f"https://www.worten.pt{href}"

                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    name = lines[0] if lines else text[:100]

                    price_str = ""
                    for line in lines:
                        price_match = re.search(r'(\d+[.,]\d{2})\s*€?', line)
                        if price_match:
                            price_str = price_match.group(1)
                            break

                    price = extract_price(price_str) if price_str else 0.0
                    product_id = hashlib.md5(f"{name}{href}".encode()).hexdigest()[:12]

                    products.append({
                        "id": product_id,
                        "name": name,
                        "price": price,
                        "price_str": f"{price_str}€" if price_str else "N/A",
                        "url": href,
                        "found_at": datetime.now().isoformat()
                    })
                except Exception:
                    continue

        except Exception as e:
            print(f"  ⚠ Erro: {e}")
        finally:
            browser.close()

    return products


def main():
    timestamp = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    print(f"\n🔍 [{timestamp}] A verificar Worten Outlet...")

    products = scrape_worten()
    seen = load_seen()

    if not products:
        print("  ℹ Nenhum produto encontrado")
        # Envia alerta se a página estiver vazia por muito tempo
        save_seen(seen)
        return

    print(f"  📦 {len(products)} produto(s) encontrado(s)")

    new_products = []
    for product in products:
        if product["id"] not in seen:
            if not matches_filters(product["name"], product["price"]):
                seen[product["id"]] = product
                continue

            new_products.append(product)
            seen[product["id"]] = product
            print(f"\n  🆕 {product['name']} — {product['price_str']}")

    if new_products:
        # Envia uma mensagem com todos os novos produtos
        msg = f"🆕 <b>{len(new_products)} novo(s) portátil(eis) no Outlet!</b>\n"
        for p in new_products:
            msg += f"\n📌 {p['name']}\n💰 {p['price_str']}\n"
            if p["url"]:
                msg += f"🔗 <a href=\"{p['url']}\">Ver produto</a>\n"
        send_telegram(msg)
    else:
        print("  ✅ Sem produtos novos")

    save_seen(seen)

    # Limpa produtos com mais de 7 dias (provavelmente já vendidos)
    cutoff = datetime.now().timestamp() - 7 * 24 * 3600
    cleaned = {}
    for pid, pdata in seen.items():
        try:
            found = datetime.fromisoformat(pdata.get("found_at", "")).timestamp()
            if found > cutoff:
                cleaned[pid] = pdata
            else:
                cleaned[pid] = pdata  # mantém mas podia limpar
        except (ValueError, TypeError):
            cleaned[pid] = pdata
    save_seen(cleaned)


if __name__ == "__main__":
    main()
