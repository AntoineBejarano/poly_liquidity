"""
Alerting System - sistema de alertas para métricas.
"""
import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AlertLevel(str, Enum):
    """Niveles de alerta."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertingSystem:
    """
    Sistema de alertas.
    
    Envía alertas a múltiples canales (Slack, Discord, Email) cuando se detectan anomalías.
    """
    
    def __init__(self):
        """Inicializa el sistema de alertas."""
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.email_config = os.getenv("EMAIL_CONFIG")  # JSON config
        self._client: Optional[httpx.AsyncClient] = None
        self._alert_history: list = []  # Historial de alertas (últimas 100)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client
    
    async def send_alert(
        self,
        level: AlertLevel,
        message: str,
        metric: Optional[str] = None,
        value: Optional[float] = None,
        **kwargs
    ):
        """
        Envía alerta a todos los canales configurados.
        
        Args:
            level: Nivel de alerta (INFO, WARNING, CRITICAL)
            message: Mensaje de la alerta
            metric: Nombre de la métrica (opcional)
            value: Valor de la métrica (opcional)
            **kwargs: Datos adicionales
        """
        alert = {
            "level": level.value,
            "message": message,
            "metric": metric,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        # Guardar en historial
        self._alert_history.append(alert)
        if len(self._alert_history) > 100:
            self._alert_history.pop(0)
        
        # Enviar a Slack
        if self.slack_webhook:
            await self._send_to_slack(alert)
        
        # Enviar a Discord
        if self.discord_webhook:
            await self._send_to_discord(alert)
        
        # Enviar email (solo para CRITICAL)
        if self.email_config and level == AlertLevel.CRITICAL:
            await self._send_email(alert)
        
        # Logging persistente
        print(f"ALERT [{level.value}]: {message}")
    
    async def _send_to_slack(self, alert: Dict[str, Any]):
        """Envía alerta a Slack."""
        try:
            client = await self._get_client()
            payload = {
                "text": f"[{alert['level']}] {alert['message']}",
                "attachments": [
                    {
                        "color": "danger" if alert["level"] == "CRITICAL" else "warning" if alert["level"] == "WARNING" else "good",
                        "fields": [
                            {"title": "Metric", "value": alert.get("metric", "N/A"), "short": True},
                            {"title": "Value", "value": str(alert.get("value", "N/A")), "short": True},
                            {"title": "Timestamp", "value": alert["timestamp"], "short": False}
                        ]
                    }
                ]
            }
            
            await client.post(self.slack_webhook, json=payload)
        except Exception as e:
            print(f"ERROR: Failed to send Slack alert: {e}")
    
    async def _send_to_discord(self, alert: Dict[str, Any]):
        """Envía alerta a Discord."""
        try:
            client = await self._get_client()
            payload = {
                "content": f"[{alert['level']}] {alert['message']}",
                "embeds": [
                    {
                        "title": alert.get("metric", "Alert"),
                        "description": alert["message"],
                        "color": 15158332 if alert["level"] == "CRITICAL" else 16776960 if alert["level"] == "WARNING" else 3066993,
                        "fields": [
                            {"name": "Value", "value": str(alert.get("value", "N/A")), "inline": True},
                            {"name": "Timestamp", "value": alert["timestamp"], "inline": True}
                        ]
                    }
                ]
            }
            
            await client.post(self.discord_webhook, json=payload)
        except Exception as e:
            print(f"ERROR: Failed to send Discord alert: {e}")
    
    async def _send_email(self, alert: Dict[str, Any]):
        """Envía alerta por email (placeholder)."""
        # TODO: Implementar envío de email
        print(f"EMAIL ALERT [{alert['level']}]: {alert['message']}")
    
    def get_alert_history(self, limit: int = 50) -> list:
        """
        Obtiene historial de alertas.
        
        Args:
            limit: Número máximo de alertas a retornar
        
        Returns:
            Lista de alertas
        """
        return self._alert_history[-limit:]
    
    async def check_latency_alerts(self, latency_p95: float):
        """
        Verifica latencia y dispara alertas si es necesario.
        
        Args:
            latency_p95: Percentil 95 de latencia en ms
        """
        WARNING_THRESHOLD = 200  # ms
        CRITICAL_THRESHOLD = 500  # ms
        
        if latency_p95 > CRITICAL_THRESHOLD:
            await self.send_alert(
                level=AlertLevel.CRITICAL,
                message=f"Critical latency: {latency_p95:.2f}ms",
                metric="latency_p95",
                value=latency_p95
            )
        elif latency_p95 > WARNING_THRESHOLD:
            await self.send_alert(
                level=AlertLevel.WARNING,
                message=f"High latency: {latency_p95:.2f}ms",
                metric="latency_p95",
                value=latency_p95
            )
    
    async def check_trading_alerts(self, rejection_rate: float):
        """
        Verifica salud de trading y dispara alertas si es necesario.
        
        Args:
            rejection_rate: Ratio de rechazos (0.0 - 1.0)
        """
        REJECTION_RATE_THRESHOLD = 0.30
        
        if rejection_rate > REJECTION_RATE_THRESHOLD:
            await self.send_alert(
                level=AlertLevel.WARNING,
                message=f"High rejection rate: {rejection_rate * 100:.1f}%",
                metric="rejection_rate",
                value=rejection_rate
            )
    
    async def check_exposure_alerts(self, exposure: float, limit: float):
        """
        Verifica exposición y dispara alertas si es necesario.
        
        Args:
            exposure: Exposición actual
            limit: Límite de exposición
        """
        if exposure > limit:
            await self.send_alert(
                level=AlertLevel.CRITICAL,
                message=f"Exposure limit exceeded: {exposure:.2f} > {limit:.2f}",
                metric="exposure",
                value=exposure,
                limit=limit
            )
    
    async def check_watcher_alerts(self, failed_checkers: int, stale_events: int):
        """
        Verifica salud de watchers y dispara alertas si es necesario.
        
        Args:
            failed_checkers: Número de checkers fallidos
            stale_events: Número de eventos sin actualizar
        """
        MAX_FAILED_CHECKERS = 2
        MAX_STALE_EVENTS = 5
        
        if failed_checkers > MAX_FAILED_CHECKERS:
            await self.send_alert(
                level=AlertLevel.WARNING,
                message=f"Multiple checkers failed: {failed_checkers}",
                metric="failed_checkers",
                value=failed_checkers
            )
        
        if stale_events > MAX_STALE_EVENTS:
            await self.send_alert(
                level=AlertLevel.WARNING,
                message=f"Multiple stale events: {stale_events}",
                metric="stale_events",
                value=stale_events
            )
    
    async def on_runtime_mode_changed(self, from_mode: str, to_mode: str):
        """
        Alerta cuando cambia el modo runtime.
        
        Args:
            from_mode: Modo anterior
            to_mode: Modo nuevo
        """
        if to_mode == "RED":
            await self.send_alert(
                level=AlertLevel.CRITICAL,
                message=f"Runtime mode changed to RED",
                metric="runtime_mode",
                value=to_mode,
                from_mode=from_mode
            )
        elif to_mode == "YELLOW":
            await self.send_alert(
                level=AlertLevel.WARNING,
                message=f"Runtime mode changed to YELLOW",
                metric="runtime_mode",
                value=to_mode,
                from_mode=from_mode
            )
    
    async def close(self):
        """Cierra el cliente HTTP."""
        if self._client:
            await self._client.aclose()
            self._client = None

