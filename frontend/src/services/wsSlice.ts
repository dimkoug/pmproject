import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface WsEvent {
  event: string;
  data: any;
  timestamp: number;
}

interface WsState {
  connected: boolean;
  events: WsEvent[];
}

const initialState: WsState = {
  connected: false,
  events: [],
};

const wsSlice = createSlice({
  name: "ws",
  initialState,
  reducers: {
    wsConnected(state) {
      state.connected = true;
    },
    wsDisconnected(state) {
      state.connected = false;
    },
    wsEventReceived(state, action: PayloadAction<{ event: string; data: any }>) {
      state.events.push({
        ...action.payload,
        timestamp: Date.now(),
      });
      if (state.events.length > 50) {
        state.events = state.events.slice(-50);
      }
    },
    wsClearEvents(state) {
      state.events = [];
    },
  },
});

export const { wsConnected, wsDisconnected, wsEventReceived, wsClearEvents } =
  wsSlice.actions;
export default wsSlice.reducer;
