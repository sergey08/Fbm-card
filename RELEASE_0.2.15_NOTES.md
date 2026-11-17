# FBM Card v0.2.15

## English

- Initial competition statistics download in consecutive batches of up to five players, with two seconds between batches and the existing half-second pause between queried players.
- Start automatically once rosters are available after following a competition or restarting the integration. Resume from a separately persisted initial-download cursor.
- Share the player-request lock with maintenance. Back off from ten seconds up to five minutes on errors and retry each failed batch once before advancing. Incomplete records remain pending for scheduled retries.
- Replace decompiled excerpts in the protocol and followed-group documentation with independently written API descriptions, following the HACS maintainer's recommendation.

The beta passed Python and JavaScript regression tests and isolated Home Assistant startup, restart and upgrade checks. On the user's installation, RICOPIA reached 116/116 evaluable players with zero pending records and zero recorded errors. Coverage percentages describe the archive criteria documented by the integration.

Update through HACS and restart Home Assistant. Previously followed competitions with pending statistics can resume their initial pass. The update preserves the existing archive and identity.

## Español

- Descarga inicial de estadísticas de la competición con lotes consecutivos de hasta cinco jugadores, dos segundos entre lotes y la pausa existente de medio segundo entre jugadores consultados.
- Inicio automático cuando están disponibles las plantillas tras seguir una competición o reiniciar la integración. Reanudación mediante un cursor inicial guardado por separado.
- Bloqueo compartido con el mantenimiento para las peticiones de jugadores. Esperas desde diez segundos hasta cinco minutos ante errores y un reintento por lote fallido antes de avanzar. Los registros incompletos quedan pendientes para las pasadas programadas.
- Sustitución de extractos descompilados en la documentación de protocolo y grupos seguidos por descripciones propias de la API, según la recomendación del responsable de HACS.

La beta superó regresiones Python y JavaScript y pruebas de arranque, reinicio y actualización en Home Assistant aislado. En la instalación del usuario, RICOPIA llegó a 116/116 jugadores evaluables, con cero pendientes y cero errores registrados. Los porcentajes de cobertura corresponden al criterio de archivo documentado por la integración.

Actualiza desde HACS y reinicia Home Assistant. Las competiciones ya seguidas con estadísticas pendientes pueden retomar su primer recorrido. La actualización conserva el archivo y la identidad existentes.
