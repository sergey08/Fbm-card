# FBM Card v0.2.7 — Release candidate notes

## English

- Set up guest access when adding the first team through **Settings → Devices & services → FBM Card → Configure → Find team to follow competition**. Registration requires confirmation and uses a locally generated identity.
- Recover a pending registration with the same identity after confirmation. Reuse a saved device profile to reconnect on demand after an outage or session expiry. Failed automatic reconnects wait 30 seconds before another attempt.
- Retry competition verification after a network error and display the verified group before asking to follow it.
- Keep the existing entity IDs, Lovelace configuration, competition history and incremental sync settings.

**Home Assistant acceptance test.** Use an isolated HA instance. Install the candidate, add the integration, open Configure, enable guest access and follow the first competition. Check search results, fixtures, standings and rosters. Restart HA and compare the entity ID, configuration entry and followed group before and after the restart. With network access interrupted, check that the archive remains readable, then restore connectivity and verify that queries resume and the next differential sync retains existing history. Confirm there is one FBM integration entry, one competition summary sensor and one Lovelace resource. Repeat the upgrade path from v0.2.6 with existing cards and followed groups. The automated smoke uses a simulated FBM transport. The live guest registration remains part of acceptance testing.

## Español

- Configuración del acceso de invitado al añadir el primer equipo desde **Ajustes → Dispositivos y servicios → FBM Card → Configurar → Buscar equipo para seguir su competición**. El alta requiere confirmación y utiliza una identidad generada localmente.
- Recuperación de un registro pendiente con la misma identidad tras confirmar. Se reutiliza el perfil guardado para reconectar cuando se necesita tras un corte de red o una sesión caducada. Si la reconexión automática falla, el siguiente intento espera 30 segundos.
- La verificación de la competición puede reintentarse tras un error de red. Se muestra el grupo verificado antes de confirmar el seguimiento.
- Se conservan los identificadores de entidad, la configuración de Lovelace, el histórico de competiciones y los ajustes de sincronización incremental.

**Prueba de aceptación en Home Assistant.** En una instancia aislada, instala la candidata, añade la integración, abre Configurar, autoriza el acceso de invitado y sigue la primera competición. Comprueba búsqueda, calendario, clasificación y plantillas. Reinicia HA y compara el ID de la entidad, la entrada de configuración y el grupo seguido. Interrumpe la conexión y comprueba que el archivo sigue accesible. Restaura la conexión y comprueba que se recuperan las consultas y que la siguiente sincronización diferencial conserva el histórico. Verifica que hay una sola entrada FBM, un solo sensor resumen y un solo recurso Lovelace. Repite actualizando desde v0.2.6 con tarjetas y grupos existentes. El smoke automatizado simula el servicio FBM. El alta real de invitado forma parte de la prueba de aceptación.
