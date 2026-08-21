import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxy: any request to /api/* from React gets forwarded to
// the Express server, so the frontend code can just call "/api/ask"
// without hardcoding a full URL (works the same in dev and prod builds
// as long as Express is reachable at this address).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
