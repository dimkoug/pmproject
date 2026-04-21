import { configureStore } from "@reduxjs/toolkit";
import { apiSlice } from "../services/api";
import authReducer from "../services/authSlice";
import wsReducer from "../services/wsSlice";

export const store = configureStore({
  reducer: {
    [apiSlice.reducerPath]: apiSlice.reducer,
    auth: authReducer,
    ws: wsReducer,
  },
  middleware: (getDefault) => getDefault().concat(apiSlice.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
