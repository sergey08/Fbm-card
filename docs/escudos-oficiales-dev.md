# Escudos oficiales de clubes (DEV)

FBM TV muestra los escudos de [Pintobasket y Villa de Valdemoro](https://fbmtv.fbm.es/es/partido-241576/pintobasket-vs-discesur-cb-villa-de-valdemoro). El selector de clubes de FBM TV identifica sus clubes como PINTOBASKET E.C.B. (6419) y VILLA DE VALDEMORO C.B. (6892); esos nombres coinciden exactamente con los mostrados por las dos tarjetas DEV en Home Assistant.

La tarjeta usa una correspondencia explícita solo para estos dos nombres oficiales, sin interpretar el identificador opaco del equipo ni efectuar búsquedas por coincidencia parcial. Se conservan las URLs de imágenes en FBM TV, sin distribuir copias. Si la imagen falla o el club es desconocido, muestra el símbolo neutro. Una URL oficial proporcionada por `logo_equipo` tiene prioridad. El uso de nombres exactos puede dejar de reconocer un club si FBM cambia su denominación; no es una solución general para todos los clubes.

Para ampliar cobertura, validar por cada club la correspondencia oficial con el catálogo y su imagen, o identificar una fuente oficial estable que relacione IDs de equipo y club; comprobar las condiciones de uso y añadir pruebas de ambigüedad y fallos. La coincidencia de los dos IDs con los nombres de archivo no demuestra que sea universal. La instalación de esta versión en DEV no equivale a una release.
