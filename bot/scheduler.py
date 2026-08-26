import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import obtener_todos_los_usuarios, obtener_usuario
from moodle import obtener_tareas_pendientes

def iniciar_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone="America/Mexico_City")

    # Función que evaluará las tareas de todos los usuarios
    async def verificar_alertas_automaticas():
        logging.info("🤖 Ejecutando revisión automática de tareas en segundo plano...")
        usuarios = obtener_todos_los_usuarios()
        
        if not usuarios:
            return

        ahora_utc = datetime.now(timezone.utc)
        zona_mexico = ZoneInfo("America/Mexico_City")

        for telegram_id in usuarios:
            enlace = obtener_usuario(telegram_id)
            if not enlace:
                continue

            tareas = obtener_tareas_pendientes(enlace, telegram_id)
            if not tareas:
                continue

            urgentes_por_avisar = []

            for tarea in tareas:
                if tarea['tipo_evento'] == "abre":
                    continue

                fecha_obj = datetime.fromisoformat(tarea['fecha'])
                diferencia_horas = (fecha_obj - ahora_utc).total_seconds() / 3600

                # Si falta entre 22 y 24 horas para vencer
                if 22 <= diferencia_horas <= 24:
                    urgentes_por_avisar.append((tarea, fecha_obj.astimezone(zona_mexico)))

            if urgentes_por_avisar:
                mensaje = "⚠️ **¡Alerta de Cierre Próximo!**\nTe quedan aproximadamente 24 horas para entregar lo siguiente:\n\n"
                for tarea, fecha_local in urgentes_por_avisar:
                    mensaje += f"🔹 *{tarea['materia']}*\n"
                    mensaje += f"📝 {tarea['titulo']}\n"
                    mensaje += f"🔴 Límite: {fecha_local.strftime('%d/%m/%Y a las %H:%M')}\n\n"
                
                try:
                    await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode="Markdown")
                    logging.info(f"Alerta enviada con éxito al usuario {telegram_id}")
                except Exception as e:
                    logging.error(f"No se pudo enviar alerta al usuario {telegram_id}: {e}")

    # Registramos el trabajo usando add_job correctamente cada 6 horas
    scheduler.add_job(verificar_alertas_automaticas, 'interval', hours=6)
    
    scheduler.start()
    logging.info("⏱️ Motor de automatización (APScheduler) iniciado correctamente.")
