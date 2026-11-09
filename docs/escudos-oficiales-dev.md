# Escudos dinámicos: candidato DEV

La tarjeta consulta al backend el catálogo público de clubes de FBM TV y busca el nombre completo, sin coincidencias parciales. Los identificadores numéricos producen una URL de imagen en FBM TV; esa convención se observó en nueve clubes, pero no es una API documentada y puede cambiar. Una imagen ausente o un catálogo inaccesible deja un símbolo neutro. El catálogo se conserva en memoria 24 horas y los fallos se reintentan tras cinco minutos. Una URL oficial configurada explícitamente tiene prioridad.

El backend y el frontend deben instalarse juntos: el backend anterior no reconoce `fbm/club/logo`. No desplegar únicamente el JavaScript. La disponibilidad desde Home Assistant y las condiciones de uso de FBM están pendientes de verificar; no se considera probado en HA ni apto para publicación. Los tests utilizan respuestas sintéticas. Los identificadores deportivos opacos y la identidad no se alteran. El catálogo puede omitir clubes que no tengan vídeos en FBM TV; no se promete cobertura completa.

## Nueva investigación APK Afición FBM 5.0.42

El análisis estático de `classes2.dex` muestra el modelo `EquipoBuscadoDto` con los campos `Escudo` (cadena) e `IdClub`, y el modelo de clasificación también contiene `Escudo`. La función `LR4/o;->s` referencia tanto `https://appaficionfbm.gesdeportiva.es/imagenes.ashx` como `?tipo=escudo&id=`. El adaptador de búsqueda actual descarta el campo `Escudo` al normalizar la respuesta.

Esto proporciona una alternativa preferente a consultar FBM TV. Los modelos y constantes son evidencia del APK, pero no prueban aún el valor real del campo, el enlace exacto entre el campo y la función, ni la respuesta de red. Hay que verificar una respuesta real sanitizada con la sesión ya existente, sin imprimir ni persistir credenciales, identificar la transformación exacta, validar origen de URL y probar fallos. No se debe desplegar ni presentar la solución de catálogo FBM TV como definitiva.
