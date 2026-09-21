import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/emails": "http://127.0.0.1:8000",
      "/attachments": "http://127.0.0.1:8000",
      "/submit": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000"
      ,"/classifications": "http://127.0.0.1:8000",
      "/tests": "http://127.0.0.1:8000"
    }
  }
});
