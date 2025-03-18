import requests
from deep_translator import GoogleTranslator
from django.shortcuts import render
from decouple import config
from .models import Producto
from django.shortcuts import redirect
from django.http import JsonResponse
from .scraper import buscar_en_primera_pagina
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from io import BytesIO
from django.http import HttpResponse
from sqlalchemy import create_engine
from django.views.decorators.csrf import csrf_exempt
from plantuml import PlantUML
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Producto
from .serializers import ProductoSerializer
from plantuml import PlantUML
import os
from django.conf import settings
from django.http import JsonResponse
from decimal import Decimal
from django.utils.timezone import now
import re

matplotlib.use('Agg')
# Configuración de la base de datos
DB_HOST = config('DB_HOST', default='localhost')
DB_PORT = config('DB_PORT', default='5432')
DB_USER = config('DB_USER', default='postgres')
DB_PASSWORD = config('DB_PASSWORD', default='kysha1234')
DB_NAME = config('DB_NAME', default='ferreteriaTOOLS')

# Crear la conexión con SQLAlchemy
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


# Configuración de la API de Hugging Face
API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-Coder-32B-Instruct"
HEADERS = {"Authorization": f"Bearer {config('HUGGINGFACE_API_KEY')}"}

@csrf_exempt
def scrape_material(request):
    """
    Realiza scraping, guarda resultados en la base de datos y genera un gráfico.
    """
    if request.method == 'POST':
        material = request.POST.get('material', '').strip()

        if not material:
            return JsonResponse({"error": "No se proporcionó un material."}, status=400)

        try:
            # 1. Realizar scraping
            productos_scrapeados = buscar_en_primera_pagina(material)

            # 2. Guardar en la base de datos
            for producto in productos_scrapeados:              
                Producto.objects.create(
                    nombre=producto['nombre'],
                    precio=producto['precio'],
                    enlace=producto['enlace'],
                    sku=producto['sku'],
                    imagen=producto['imagen'],
                    fecha_adicion=producto['fecha_adicion']
                )

            # 3. Generar gráfico
            query = 'SELECT * FROM public."chatCivil_producto"'
            data = pd.read_sql(query, engine)
            filtered_data = data[data['nombre'].str.contains(material, case=False, na=False)]

            if filtered_data.empty:
                return JsonResponse({"error": f"No se encontraron productos para '{material}'."}, status=404)

            top_5 = filtered_data.head(6)
            top_5['fecha_adicion'] = pd.to_datetime(top_5['fecha_adicion'], errors='coerce')

            plt.figure(figsize=(12, 8))
            for _, row in top_5.iterrows():
                product_data = data[data['enlace'] == row['enlace']].sort_values(by='fecha_adicion')
                plt.plot(product_data['fecha_adicion'], product_data['precio'], marker='o', label=row['nombre'])

            plt.title(f"Precios vs Tiempo para '{material}'")
            plt.xlabel("Tiempo")
            plt.ylabel("Precio")
            plt.legend(loc='best')
            plt.grid(True)
            plt.tight_layout()

            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()
            buffer.seek(0)

            return JsonResponse({"graph": buffer.getvalue().decode('latin1')}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"Error al procesar: {str(e)}"}, status=500)

    return redirect('index')

@csrf_exempt
def limpiar_precio(precio_str):
    """
    Limpia y convierte una cadena de texto que representa un precio a un número decimal.
    
    :param precio_str: Cadena de texto del precio (por ejemplo, "S/ 1,000.00").
    :return: Precio como Decimal, o genera una excepción si el formato es inválido.
    """
    if not precio_str:
        return Decimal(0)

    # Eliminar el prefijo 'S/ ' y cualquier espacio adicional
    precio_str = precio_str.replace('S/ ', '').strip()

    # Manejar precios con formato especial como "S/ 1<sup>.30"
    if "<sup>" in precio_str or "</sup>" in precio_str:
        raise ValueError(f"Formato de precio inválido: {precio_str}")

    # Eliminar comas si existen (por ejemplo, "1,000.00")
    precio_str = precio_str.replace(',', '')

    # Convertir el precio a Decimal
    try:
        return Decimal(precio_str)
    except (ValueError):
        return Decimal(0)  # Si no es válido, retornar 0


@csrf_exempt
def obtener_precios(request):
    """
    Obtiene los precios de los productos relacionados con el material proporcionado,
    ordena por precio y devuelve los tres productos más baratos, considerando solo
    los productos con fecha de hoy y nombres diferentes.

    :param request: Solicitud HTTP con el material proporcionado en POST.
    :return: Respuesta JSON con los productos más baratos o un mensaje de error.
    """
    # Recibimos el material seleccionado del frontend
    material = request.POST.get('material', None)

    if material:
        # Filtrar productos relacionados con el material y fecha de hoy
        hoy = now().date()
        productos = Producto.objects.filter(nombre__icontains=material, fecha_adicion__date=hoy)

        # Limpiar y convertir los precios, agregando información relevante
        productos_con_precio = []
        for producto in productos:
            try:
                precio_decimal = limpiar_precio(producto.precio)
                productos_con_precio.append({
                    'nombre': producto.nombre,
                    'precio': float(precio_decimal),  # Convertimos Decimal a float para facilidad de uso
                    'precio_str': producto.precio,   # Guardamos el precio original
                    'url': producto.enlace
                })
            except ValueError as e:
                print(f"Error procesando producto: {producto.nombre}, mensaje: {e}")

        # Ordenar los productos por precio
        productos_ordenados = sorted(productos_con_precio, key=lambda x: x['precio'])

        # Limitar a los 3 productos más baratos con nombres diferentes
        nombres_unicos = set()
        productos_mas_baratos = []
        for producto in productos_ordenados:
            if producto['nombre'] not in nombres_unicos:
                productos_mas_baratos.append(producto)
                nombres_unicos.add(producto['nombre'])
            if len(productos_mas_baratos) == 3:
                break

        # Crear la respuesta con los productos más baratos
        precios = [{'nombre': p['nombre'], 'precio': p['precio_str'], 'url': p['url']} for p in productos_mas_baratos]

        # Si no hay productos, devolver un mensaje de error
        if not precios:
            return JsonResponse({'error': 'No se encontraron productos para el material proporcionado'}, status=404)

        return JsonResponse({'productos': precios})

    # Si no se proporciona material, devolver un error
    return JsonResponse({'error': 'Material no encontrado'}, status=400)

@csrf_exempt
def index(request):
    """
    Vista principal que genera la lista de materiales y procesa el input del usuario.
    """
    context = {}
    if request.method == 'POST':
        # Captura el texto ingresado por el usuario
        input_text = request.POST.get('input_text', '')

        if input_text:
            translated_input_text = GoogleTranslator(source='es', target='en').translate(input_text)
            # Configura el prompt para la API
            prompt = (
                f"Provide only a clean, numbered list of the 6 most important materials required to build a {translated_input_text} . "
                "Do not include any explanations, introductions, or extra text, only a word for item and each word should be a singular noun."
            )
            payload = {"inputs": prompt}

            try:
                # Llamada a la API de Hugging Face
                response = requests.post(API_URL, headers=HEADERS, json=payload)

                if response.status_code == 200:
                    # Procesar la respuesta de la API
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get("generated_text", "")
                        materials = [line.strip().split('. ', 1)[-1] for line in generated_text.split("\n") if line.strip() and line[0].isdigit()]

                        # Traducir los materiales al español usando deep-translator
                        translated_materials = [
                            GoogleTranslator(source='en', target='es').translate(item)
                            for item in materials
                        ]
                        context['materials'] = translated_materials
                    else:
                        context['error'] = "No se pudo procesar la respuesta de la API."
                else:
                    context['error'] = f"Error {response.status_code}: {response.json()}"

            except Exception as e:
                context['error'] = f"Error al conectar con la API: {str(e)}"

    return render(request, 'index.html', context)
@csrf_exempt
def generar_calendarizacion(request):
    # Código PlantUML para la construcción (casa en este caso)
    codigo_plantuml = """
    @startuml
    |Inicio|
    start
    :Recopilar requisitos de construcción [2 días];
    :Analizar el terreno [3 días];
    :Definir presupuesto y tiempo de ejecución [5 días];
    :Obtener permisos de construcción [7 días];

    |Fase de Excavación|
    split
      :Excavar los cimientos [4 días];
      :Colocar las bases de los cimientos [3 días];
    split again
      :Verificar calidad de cimientos [2 días];
      :Revisar aprobación de ingeniero [1 día];
    end split

    |Fase de Levantamiento de Paredes|
    split
      :Levantar paredes exteriores [5 días];
      :Instalar columnas y soportes [4 días];
    split again
      :Colocar ventanas y puertas exteriores [4 días];
    end split

    |Fase de Colocación de Techo|
    split
      :Instalar estructura del techo [5 días];
      :Colocar tejas o material elegido [5 días];
    split again
      :Verificar estanqueidad del techo [2 días];
    end split

    |Fase de Instalaciones|
    split
      :Instalar sistemas eléctricos y de fontanería [7 días];
      :Instalar sistemas de calefacción y ventilación [5 días];
    split again
      :Verificar sistemas de seguridad [2 días];
      :Revisar instalaciones de gas y agua [3 días];
    end split

    |Fase de Acabados|
    split
      :Colocar revestimiento de paredes [4 días];
      :Instalar pisos y acabados interiores [6 días];
    split again
      :Instalar puertas y ventanas interiores [3 días];
      :Realizar pintura y acabados finales [4 días];
    end split

    :Inspeccionar obra [2 días];
    :Entregar obra al propietario [1 día];
    :Recibir pago final [1 día];

    stop
    @enduml
    """

    # Guardar el archivo PlantUML en el directorio temporal
    puml_path = os.path.join(settings.MEDIA_ROOT, 'diagrama_con_duracion.puml')
    with open(puml_path, 'w') as archivo:
        archivo.write(codigo_plantuml)

    # Usar PlantUML para generar la imagen .png
    try:
        plantuml = PlantUML(url='http://www.plantuml.com/plantuml/img/')
        png_path = os.path.join(settings.MEDIA_ROOT, 'diagrama_con_duracion.png')

        # Procesa el archivo .puml y genera la imagen .png
        plantuml.processes_file(puml_path)

        # Verificar que el archivo .png se haya generado
        if os.path.exists(png_path):
            # Devuelve la URL de la imagen generada
            return JsonResponse({"graph": f"/media/{os.path.basename(png_path)}"}, status=200)
        else:
            return JsonResponse({"error": "No se pudo generar la imagen."}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Error al generar el diagrama: {str(e)}"}, status=500)
    


