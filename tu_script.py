import requests
from bs4 import BeautifulSoup
import random
from urllib.parse import quote_plus, unquote
import hashlib
import datetime
import re
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import time  # Añadido para el sleep
from functools import lru_cache  # Añadido para el caché

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/122.0.6261.140 DuckDuckGo/5 Safari/537.36"
]

PLATFORMS = {
    "Facebook": ["facebook.com", "fb.com"],
    "YouTube": ["youtube.com", "youtu.be"],
    "Instagram": ["instagram.com"],
    "TikTok": ["tiktok.com"],
    "GitHub": ["github.com"],
    "Telegram": ["t.me", "telegram.org"],
    "Twitter": ["twitter.com", "x.com"],
    "Reddit": ["reddit.com"],
    "LinkedIn": ["linkedin.com"],
    "Pinterest": ["pinterest.com"],
    "Snapchat": ["snapchat.com"],
    "Twitch": ["twitch.tv"],
    "Steam": ["steamcommunity.com", "steampowered.com"],
    "DeviantArt": ["deviantart.com"],
    "Medium": ["medium.com"],
    "Flickr": ["flickr.com"]
}

TIMEOUT = 15
MAX_RESULTS = 30

# Versión con caché de la función buscar_ip
@lru_cache(maxsize=100)
def buscar_ip_cached(ip):
    return buscar_ip(ip)

def buscar(usuario):
    variations = generate_username_variations(usuario)
    all_results = []

    for variation in variations:
        results = search_duckduckgo(variation)
        all_results.extend(results)

    classified = classify_results(all_results)
    classified = remove_duplicates(classified)

    return {
        "username": usuario,
        "date": datetime.datetime.now().isoformat(),
        "variations": variations,
        "results": classified
    }

def generate_username_variations(username):
    variations = {
        username,
        username.replace(' ', ''),
        username.replace(' ', '_'),
        username.replace(' ', '.'),
        username.replace(' ', '-'),
        f"{username}_",
        f"{username}-",
        f"{username}.",
        f"{username}1",
        f"{username}123",
        f"{username}2023",
        f"{username}2024",
        username.replace('a', '4').replace('e', '3').replace('i', '1').replace('o', '0'),
        username.lower(),
        username.upper(),
        username.title(),
        username[::-1],
        f"real{username}",
        f"official{username}",
        f"the{username}",
        f"{username}official"
    }
    return [v for v in variations if v and len(v) <= 30]

def search_duckduckgo(query):
    session = requests.Session()
    session.headers.update({'User-Agent': random.choice(USER_AGENTS)})

    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        for result in soup.find_all('div', class_='result', limit=MAX_RESULTS):
            title = result.find('a', class_='result__a').get_text(strip=True)
            link = parse_ddg_link(result.find('a', class_='result__a')['href'])

            if link and not link.startswith('https://duckduckgo.com'):
                results.append({
                    "title": title,
                    "url": link,
                    "variation": query,
                    "hash": create_result_hash(title, link)
                })

        return results
    except Exception as e:
        print(f"Error searching for {query}: {str(e)}")
        return []

def parse_ddg_link(link):
    if link.startswith('//'):
        link = 'https:' + link

    if link.startswith('/l/?uddg='):
        match = re.search(r'/l/\?uddg=(.*?)(?:&|$)', link)
        if match:
            link = unquote(match.group(1))
        else:
            return None

    clean_link = re.sub(r'(&|\?)utm_[^&]+', '', link)
    clean_link = re.sub(r'(&|\?)fbclid=[^&]+', '', clean_link)
    clean_link = re.sub(r'(&|\?)ref=[^&]+', '', clean_link)

    return clean_link.split('&')[0].split('?')[0]

def classify_results(results):
    classification = {platform: [] for platform in PLATFORMS}
    classification["Others"] = []

    for result in results:
        url = result["url"].lower()
        found = False

        for platform, domains in PLATFORMS.items():
            if any(domain.lower() in url for domain in domains):
                classification[platform].append(result)
                found = True
                break

        if not found:
            classification["Others"].append(result)

    return classification

def remove_duplicates(classified_results):
    unique_results = {platform: [] for platform in classified_results}
    seen_hashes = set()

    for platform, results in classified_results.items():
        for result in results:
            if result["hash"] not in seen_hashes:
                unique_results[platform].append(result)
                seen_hashes.add(result["hash"])

    return unique_results

def create_result_hash(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()

def buscar_ip(ip):
    """Obtiene información detallada de una dirección IP con caché, límite de solicitudes y API de respaldo"""
    try:
        # 1. Validación mejorada de la IP
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return {"error": "Formato de IP inválido"}
        
        # 2. Configuración de headers
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json',
            'Accept-Language': 'es-ES,es;q=0.9'
        }
        
        # 3. Pequeña pausa para evitar saturación (1 solicitud/segundo)
        time.sleep(1)
        
        # 4. Intentar primero con ipapi.co (API principal)
        try:
            res = requests.get(f"https://ipapi.co/{ip}/json/", headers=headers, timeout=TIMEOUT)
            
            # Manejo específico del error 429
            if res.status_code == 429:
                return {
                    "error": "Límite de solicitudes alcanzado",
                    "solucion": "Espere 60 segundos o regístrese en ipapi.co para una clave API",
                    "detalles": "Plan gratuito permite 1,000 solicitudes/día (30/min)"
                }
            
            res.raise_for_status()
            ip_data = res.json()
            
            # Si hay error en la respuesta de la API
            if ip_data.get("error"):
                return {
                    "error": ip_data.get("reason", "Error en la API"),
                    "codigo_error": ip_data.get("code")
                }
            
            # 5. Construir respuesta completa con todos los campos posibles
            response = {
                "ip": ip_data.get("ip"),
                "network": ip_data.get("network"),
                "version": ip_data.get("version"),
                "city": ip_data.get("city"),
                "region": ip_data.get("region"),
                "region_code": ip_data.get("region_code"),
                "country": ip_data.get("country"),
                "country_name": ip_data.get("country_name"),
                "country_code": ip_data.get("country_code"),
                "country_code_iso3": ip_data.get("country_code_iso3"),
                "country_capital": ip_data.get("country_capital"),
                "country_tld": ip_data.get("country_tld"),
                "continent_code": ip_data.get("continent_code"),
                "in_eu": ip_data.get("in_eu"),
                "postal": ip_data.get("postal"),
                "latitude": ip_data.get("latitude"),
                "longitude": ip_data.get("longitude"),
                "timezone": ip_data.get("timezone"),
                "utc_offset": ip_data.get("utc_offset"),
                "country_calling_code": ip_data.get("country_calling_code"),
                "currency": ip_data.get("currency"),
                "currency_name": ip_data.get("currency_name"),
                "languages": ip_data.get("languages"),
                "country_area": ip_data.get("country_area"),
                "country_population": ip_data.get("country_population"),
                "asn": ip_data.get("asn"),
                "org": ip_data.get("org"),
                "fecha_consulta": datetime.datetime.now().isoformat(),
                "fuente": "ipapi.co",
                "cache": False
            }
            
            # Eliminar campos nulos/vacíos
            return {k: v for k, v in response.items() if v not in (None, "", {})}
            
        except requests.exceptions.RequestException as e:
            # 6. Si falla ipapi.co, intentar con API de respaldo (ip-api.com)
            try:
                res_backup = requests.get(f"http://ip-api.com/json/{ip}", headers=headers, timeout=TIMEOUT)
                res_backup.raise_for_status()
                backup_data = res_backup.json()
                
                if backup_data.get("status") == "success":
                    return {
                        "ip": ip,
                        "pais": backup_data.get("country"),
                        "codigo_pais": backup_data.get("countryCode"),
                        "region": backup_data.get("regionName"),
                        "codigo_region": backup_data.get("region"),
                        "ciudad": backup_data.get("city"),
                        "codigo_postal": backup_data.get("zip"),
                        "latitud": backup_data.get("lat"),
                        "longitud": backup_data.get("lon"),
                        "zona_horaria": backup_data.get("timezone"),
                        "isp": backup_data.get("isp"),
                        "org": backup_data.get("org"),
                        "asn": backup_data.get("as"),
                        "proveedor": backup_data.get("org"),
                        "fecha_consulta": datetime.datetime.now().isoformat(),
                        "fuente": "ip-api.com (respaldo)",
                        "cache": False,
                        "aviso": "Respuesta de respaldo con menos campos"
                    }
                else:
                    return {
                        "error": backup_data.get("message", "Error en API de respaldo"),
                        "fuente": "ip-api.com"
                    }
                    
            except requests.exceptions.RequestException as e_backup:
                return {
                    "error": "Todas las APIs fallaron",
                    "detalles": {
                        "ipapi.co": str(e),
                        "ip-api.com": str(e_backup)
                    }
                }
    
    except Exception as e:
        return {
            "error": "Error inesperado al procesar la IP",
            "detalle": str(e),
            "ip_consultada": ip
        }

def buscar_numero(numero):
    """Obtiene información de un número de teléfono sin usar APIs externas"""
    try:
        # Parsear y validar el número
        parsed_number = phonenumbers.parse(numero, None)
        
        if not phonenumbers.is_valid_number(parsed_number):
            return {"error": "Número de teléfono inválido"}
        
        # Mapear tipos de números a descripciones legibles
        tipo_numero = phonenumbers.number_type(parsed_number)
        tipo_desc = {
            0: "Fijo",
            1: "Móvil",
            2: "Fijo",
            3: "Móvil",
            4: "Toll Free",
            5: "Premium",
            6: "Compartido",
            7: "VoIP",
            8: "Personal",
            9: "Pager",
            10: "UAN",
            27: "Voicemail"
        }.get(tipo_numero, "Desconocido")
        
        # Obtener información básica
        info = {
            "numero": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "valido": True,
            "tipo": tipo_desc,
            "operadora": carrier.name_for_number(parsed_number, "es") or "Desconocida",
            "pais": geocoder.description_for_number(parsed_number, "es") or "Desconocido",
            "codigo_pais": parsed_number.country_code,
            "codigo_nacional": parsed_number.national_number,
            "zona_horaria": timezone.time_zones_for_number(parsed_number) or ["Desconocida"],
            "formato_e164": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164),
            "formato_nacional": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL),
            "formato_internacional": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "fecha_consulta": datetime.datetime.now().isoformat(),
        }
        
        return info
    
    except phonenumbers.phonenumberutil.NumberParseException as e:
        return {"error": f"Error en el formato del número: {str(e)}"}
    except Exception as e:
        return {"error": f"Error al analizar el número: {str(e)}"}
