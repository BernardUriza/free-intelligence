/**
 * PM2 Process Manager Configuration
 * Optimized for NAS deployment
 *
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 save
 *   pm2 startup
 */

module.exports = {
  apps: [
    {
      name: 'fi-backend-api',
      script: 'uvicorn',
      args: 'backend.main:app --host 0.0.0.0 --port 9001 --workers 2',
      cwd: '/Users/bernardurizaorozco/Documents/free-intelligence',
      interpreter: 'python3',
      env: {
        NODE_ENV: 'production',
        PORT: '9001',
        PYTHONPATH: '/Users/bernardurizaorozco/Documents/free-intelligence'
      },
      instances: 1,
      exec_mode: 'fork',
      max_memory_restart: '1G',
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'fi-timeline-api',
      script: 'uvicorn',
      args: 'backend.timeline_api:app --host 0.0.0.0 --port 9002 --workers 1',
      cwd: '/Users/bernardurizaorozco/Documents/free-intelligence',
      interpreter: 'python3',
      env: {
        NODE_ENV: 'production',
        PORT: '9002',
        PYTHONPATH: '/Users/bernardurizaorozco/Documents/free-intelligence'
      },
      instances: 1,
      exec_mode: 'fork',
      max_memory_restart: '512M',
      error_file: './logs/timeline-error.log',
      out_file: './logs/timeline-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'fi-frontend',
      script: 'pnpm',
      args: 'start',
      cwd: '/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity',
      env: {
        NODE_ENV: 'production',
        PORT: '9000',
        NEXT_TELEMETRY_DISABLED: '1'
      },
      instances: 1,
      exec_mode: 'fork',
      max_memory_restart: '1G',
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ],

  deploy: {
    production: {
      user: 'admin',
      host: 'nas-ip',
      ref: 'origin/main',
      repo: 'git@github.com:user/free-intelligence.git',
      path: '/volume1/docker/free-intelligence',
      'post-deploy': 'pnpm install:all && pnpm build && pm2 reload ecosystem.config.js --env production',
      'pre-setup': 'git config --global core.autocrlf false'
    }
  }
};
