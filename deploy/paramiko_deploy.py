#!/usr/bin/env python3
"""
Automated deployment script using Paramiko
CI/CD deployment to DigitalOcean
"""

import paramiko
import os
import sys
import time
from datetime import datetime

# Configuration
DROPLET_IP = os.getenv('DROPLET_IP', '104.131.175.65')
SSH_USER = 'root'
SSH_KEY_PATH = os.path.expanduser('~/.ssh/id_ed25519_do')

def deploy():
    """Deploy Free Intelligence to DigitalOcean"""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"🚀 Starting deployment to {DROPLET_IP}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Connect using SSH key
        client.connect(
            hostname=DROPLET_IP,
            username=SSH_USER,
            key_filename=SSH_KEY_PATH,
            timeout=10
        )
        print("✅ Connected to server")

        # Deployment commands
        commands = [
            ("📥 Pulling latest code", "cd /opt/free-intelligence && git pull origin main"),
            ("🐳 Building Docker image", "cd /opt/free-intelligence && docker build -t fi-backend:latest ."),
            ("🛑 Stopping old container", "docker stop fi-backend 2>/dev/null || true && docker rm fi-backend 2>/dev/null || true"),
            ("🚀 Starting new container", """docker run -d \
                --name fi-backend \
                --restart unless-stopped \
                -p 7001:7001 \
                --env-file /opt/free-intelligence/.env \
                -v /opt/free-intelligence/storage:/app/storage \
                fi-backend:latest"""),
            ("⏳ Waiting for startup", "sleep 5"),
            ("✅ Health check", "curl -s http://localhost:7001/api/health | python3 -m json.tool")
        ]

        # Execute deployment
        for description, command in commands:
            print(f"\n{description}...")
            stdin, stdout, stderr = client.exec_command(command)

            # Wait for command to complete
            exit_status = stdout.channel.recv_exit_status()

            # Get output
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if output:
                print(f"   {output[:200]}")

            if exit_status != 0 and error and 'No such container' not in error:
                print(f"   ⚠️  Warning: {error[:200]}")

        # Final verification
        print("\n📊 Deployment Summary:")
        stdin, stdout, stderr = client.exec_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep fi-backend")
        print(stdout.read().decode())

        print("\n✅ Deployment completed successfully!")
        print(f"🌐 Backend available at: http://{DROPLET_IP}:7001")

    except paramiko.AuthenticationException:
        print("❌ Authentication failed! Check SSH key.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    deploy()