import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Ports come from the repo-root .env (AXIS_FRONTEND_PORT / AXIS_BACKEND_PORT)
  // so each git worktree can run its own dev stack without colliding.
  const rootEnv = loadEnv(mode, resolve(process.cwd(), '..'), '')
  const frontendPort = Number(process.env.AXIS_FRONTEND_PORT || rootEnv.AXIS_FRONTEND_PORT || 4000)
  const backendPort = Number(process.env.AXIS_BACKEND_PORT || rootEnv.AXIS_BACKEND_PORT || 5000)

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: frontendPort,
      warmup: {
        clientFiles: ['./src/App.tsx', './src/components/CreateWorkflow.tsx'],
      },
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        }
      }
    }
  }
})
