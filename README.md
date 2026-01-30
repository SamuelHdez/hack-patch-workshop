# hack-patch-workshop

Sitio web satírico de estilo “boletín oficial” con interfaz en Tailwind y backend en Python.

## Requisitos
- Docker
- Docker Compose

## Cómo ejecutar
1. Levanta los servicios:
	- `docker-compose up`
2. Abre el navegador en la URL indicada por el contenedor (por defecto suele ser http://localhost:5000).

## Estructura
- templates/: páginas HTML
- static/: estilos y assets
- ticketweb.py: aplicación backend

## Notas
- La interfaz usa Tailwind vía CDN.
- Si el puerto está ocupado, edítalo en docker-compose.yml.