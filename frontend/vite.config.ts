import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/emails": "http://127.0.0.1:8080",
      "/attachments": "http://127.0.0.1:8080",
      "/submit": "http://127.0.0.1:8080",
      "/health": "http://127.0.0.1:8080"
    }
  }
});
