"""
🌊 DigitalOcean Infrastructure with Pulumi - SIMPLIFIED
Like CDK but works with ANY cloud (and accepts PayPal!)
"""

import pulumi
import pulumi_digitalocean as do

# Configuration
config = pulumi.Config()
region = config.get("region") or "nyc3"
environment = config.get("environment") or "dev"

# Create a VPC
vpc = do.Vpc("fi-vpc", region=region, ip_range="10.10.10.0/24")

# PostgreSQL Database (managed) - $15/month
postgres_cluster = do.DatabaseCluster(
    "fi-postgres",
    name=f"fi-postgres-{environment}",
    engine="pg",
    version="15",
    size="db-s-1vcpu-1gb",  # Valid size for DO
    region=region,
    node_count=1,
)

# Create database inside cluster
database = do.DatabaseDb("fi-db", cluster_id=postgres_cluster.id, name="free_intelligence")

# Spaces Bucket (S3-compatible) - $5/month
# NOTE: Spaces requires additional setup - commenting out for initial deploy
# audio_bucket = do.SpacesBucket("fi-audio",
#     name=f"fi-audio-{environment}",
#     region=region,
#     acl="private"
# )

# Simple Droplet (VPS) - $6/month
droplet = do.Droplet(
    "fi-backend",
    name=f"fi-backend-{environment}",
    region=region,
    size="s-1vcpu-1gb",
    image="docker-20-04",
    vpc_uuid=vpc.id,
    # Simple startup script
    user_data="""#!/bin/bash
        apt-get update
        apt-get install -y git

        # Clone your repo (update with your GitHub URL)
        git clone https://github.com/yourusername/free-intelligence.git /app
        cd /app

        # Create simple Python HTTP server for testing
        cat > server.py << 'EOF'
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "free-intelligence"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

httpd = HTTPServer(('0.0.0.0', 7001), Handler)
print("Server running on port 7001...")
httpd.serve_forever()
EOF

        # Run the test server
        python3 server.py &
    """,
)

# Firewall rules
firewall = do.Firewall(
    "fi-firewall",
    name=f"fi-firewall-{environment}",
    droplet_ids=[droplet.id],
    # Allow SSH, HTTP, HTTPS, and our app port
    inbound_rules=[
        do.FirewallInboundRuleArgs(protocol="tcp", port_range="22", source_addresses=["0.0.0.0/0"]),
        do.FirewallInboundRuleArgs(protocol="tcp", port_range="80", source_addresses=["0.0.0.0/0"]),
        do.FirewallInboundRuleArgs(
            protocol="tcp", port_range="443", source_addresses=["0.0.0.0/0"]
        ),
        do.FirewallInboundRuleArgs(
            protocol="tcp", port_range="7001", source_addresses=["0.0.0.0/0"]
        ),
    ],
    # Allow all outbound
    outbound_rules=[
        do.FirewallOutboundRuleArgs(
            protocol="tcp", port_range="1-65535", destination_addresses=["0.0.0.0/0"]
        ),
        do.FirewallOutboundRuleArgs(
            protocol="udp", port_range="1-65535", destination_addresses=["0.0.0.0/0"]
        ),
    ],
)

# Export important values
pulumi.export("droplet_ip", droplet.ipv4_address)
pulumi.export("database_uri", postgres_cluster.uri)
pulumi.export("database_host", postgres_cluster.host)
pulumi.export("database_port", postgres_cluster.port)
pulumi.export("spaces_bucket", "Spaces setup required separately")
pulumi.export("spaces_endpoint", f"https://{region}.digitaloceanspaces.com")
pulumi.export("backend_url", pulumi.Output.concat("http://", droplet.ipv4_address, ":7001"))

# Cost estimate
pulumi.export("estimated_monthly_cost", "$18/month (Droplet + Database + Spaces)")

# Instructions
pulumi.export(
    "next_steps",
    pulumi.Output.concat(
        "\n✅ Deploy complete! Your infrastructure is ready.\n",
        "\n🖥️  SSH to your server: ssh root@",
        droplet.ipv4_address,
        "\n",
        "🌐 Backend URL: http://",
        droplet.ipv4_address,
        ":7001/api/health\n",
        "📦 Spaces: Setup separately in DO console\n",
        "\n💡 Remember to:\n",
        "1. Update your GitHub repo URL in the user_data script\n",
        "2. Configure your app with the database credentials\n",
        "3. Set up your domain name (optional)\n",
    ),
)
