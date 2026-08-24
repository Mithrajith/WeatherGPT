import logging
from typing import Dict, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # Maps active WebSocket connections to their subscribed district (optional, None means all districts)
        self.active_connections: Dict[WebSocket, Optional[str]] = {}

    async def connect(self, websocket: WebSocket, district: Optional[str] = None):
        await websocket.accept()
        normalized_district = district.strip().lower() if district else None
        self.active_connections[websocket] = normalized_district
        logger.info(f"WebSocket client connected. Subscribed district filter: {normalized_district}")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            logger.info("WebSocket client disconnected.")

    async def broadcast(self, alert_data: dict):
        """
        Broadcasts an alert payload to all connected clients whose subscription matches.
        Clients subscribed to None receive all broadcasts.
        """
        alert_district = str(alert_data.get("district", "")).strip().lower()
        
        for connection, sub_district in list(self.active_connections.items()):
            if sub_district is None or sub_district == alert_district:
                try:
                    await connection.send_json(alert_data)
                except Exception as e:
                    logger.error(f"Failed to send to client. Disconnecting: {e}")
                    await self.disconnect(connection)

# Singleton instance for imports
websocket_manager = WebSocketManager()
