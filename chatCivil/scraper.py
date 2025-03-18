from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import time

# Configuración de Selenium para ignorar errores SSL
chrome_options = Options()
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--headless')  # Ejecuta sin abrir el navegador
chrome_options.add_argument('--disable-web-security')   
chrome_options.add_argument('--disable-gpu')  # Opcional para Windows
chrome_options.add_argument('--allow-running-insecure-content')
driver = webdriver.Chrome(options=chrome_options)

# Función para extraer productos de la página actual
def extraer_productos(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    
    productos = soup.find_all('div', class_='product')
    resultado = []
    for producto in productos:
        nombre = producto.get('data-name', 'N/A')
        precio = producto.get('data-best-price', 'N/A')
        enlace = producto.find('a', class_='prod-det-enlace')['href'] if producto.find('a', class_='prod-det-enlace') else 'N/A'
        sku = producto.get('data-sku', 'N/A')
        imagen = producto.find('img')['src'] if producto.find('img') else 'N/A'

        resultado.append({
            'nombre': nombre,
            'precio': precio,
            'enlace': f"https://www.promart.pe{enlace}" if enlace.startswith("/") else enlace,
            'sku': sku,
            'imagen': imagen,
            'fecha_adicion': datetime.now()  
        })
    return resultado


def buscar_en_primera_pagina(termino_busqueda):
    url = f"https://www.promart.pe/busca?ft={termino_busqueda}"
    driver.get(url)
    print(f"Buscando '{termino_busqueda}' en: {url}")
    productos = extraer_productos(driver)
    return productos

# Finalizar sesión de Selenium
def cerrar_navegador():
    driver.quit()
