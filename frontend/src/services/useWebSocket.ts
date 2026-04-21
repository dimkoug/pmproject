import { useEffect, useRef, useCallback } from "react";
import { useAppDispatch } from "../app/hooks";
import { wsConnected, wsDisconnected, wsEventReceived } from "./wsSlice";
import { apiSlice } from "./api";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export function useProjectWebSocket(projectId: string | undefined) {
  const dispatch = useAppDispatch();
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!projectId) return;

    const ws = new WebSocket(`${WS_URL}/ws/${projectId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      dispatch(wsConnected());
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        dispatch(wsEventReceived(msg));
        // Invalidate relevant cache on any change event
        dispatch(apiSlice.util.invalidateTags(["Dashboard"]));
        if (msg.event.includes("task")) dispatch(apiSlice.util.invalidateTags(["Task"]));
        if (msg.event.includes("risk")) dispatch(apiSlice.util.invalidateTags(["Risk"]));
        if (msg.event.includes("stakeholder")) dispatch(apiSlice.util.invalidateTags(["Stakeholder"]));
        if (msg.event.includes("team_member")) dispatch(apiSlice.util.invalidateTags(["TeamMember"]));
        if (msg.event.includes("deliverable")) dispatch(apiSlice.util.invalidateTags(["Deliverable"]));
        if (msg.event.includes("measurement")) dispatch(apiSlice.util.invalidateTags(["Measurement"]));
        if (msg.event.includes("change_request")) dispatch(apiSlice.util.invalidateTags(["ChangeRequest"]));
        if (msg.event.includes("project")) dispatch(apiSlice.util.invalidateTags(["Project"]));
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      dispatch(wsDisconnected());
      // Reconnect after 3 seconds
      setTimeout(() => connect(), 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [projectId, dispatch]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
