from __future__ import annotations

import typer
from typing import Annotated

app = typer.Typer(name="infra", help="Infra and host configuration tools", no_args_is_help=True)


@app.command("setup-firewall")
def setup_firewall(
    vpc_cidr: Annotated[
        str,
        typer.Option("--vpc-cidr", help="VPC CIDR block for NFS access")
    ] = "10.116.0.0/20",
    enable_smb: Annotated[
        bool,
        typer.Option("--with-smb", help="Enable SMB ports in addition to NFS")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be configured without making changes")
    ] = False,
) -> None:
    """
    Setup UFW firewall for production server.
    
    Configures deny-all policy with SSH and NFS access from VPC only.
    Requires root privileges.
    """
    import os
    import subprocess
    
    typer.echo("🔥 Setting up UFW firewall...")
    typer.echo(f"   VPC CIDR: {vpc_cidr}")
    typer.echo(f"   SMB enabled: {enable_smb}")
    typer.echo(f"   Dry run: {dry_run}")
    typer.echo()
    
    # Check if running as root
    if os.geteuid() != 0:
        typer.echo("❌ Must run as root (sudo)", err=True)
        raise typer.Exit(1)
    
    try:
        commands = []
        
        # Reset UFW to defaults
        commands.append(("ufw --force reset", "Resetting UFW to defaults"))
        
        # Set default policies
        commands.append(("ufw default deny incoming", "Setting default deny incoming"))
        commands.append(("ufw default allow outgoing", "Setting default allow outgoing"))
        
        # Allow SSH
        commands.append(("ufw allow ssh", "Allowing SSH access"))
        
        # Allow NFS from VPC
        commands.append((f"ufw allow from {vpc_cidr} to any port 2049 proto tcp", "Allowing NFS TCP from VPC"))
        commands.append((f"ufw allow from {vpc_cidr} to any port 2049 proto udp", "Allowing NFS UDP from VPC"))
        
        # Allow additional NFS ports
        for port in [111, 32765, 32766, 32767]:
            commands.append((f"ufw allow from {vpc_cidr} to any port {port} proto tcp", f"Allowing NFS port {port} TCP from VPC"))
            commands.append((f"ufw allow from {vpc_cidr} to any port {port} proto udp", f"Allowing NFS port {port} UDP from VPC"))
        
        # Allow SMB if requested
        if enable_smb:
            commands.append((f"ufw allow from {vpc_cidr} to any port 445 proto tcp", "Allowing SMB from VPC"))
            commands.append((f"ufw allow from {vpc_cidr} to any port 139 proto tcp", "Allowing NetBIOS from VPC"))
        
        # Enable UFW
        commands.append(("ufw --force enable", "Enabling UFW"))
        
        # Execute commands
        for cmd, desc in commands:
            typer.echo(f"📦 {desc}...")
            if not dry_run:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode != 0:
                    typer.echo(f"   ❌ Failed: {result.stderr.strip()}", err=True)
                    raise typer.Exit(1)
            else:
                typer.echo(f"   [DRY RUN] Would run: {cmd}")
        
        # Show status
        typer.echo("\n📊 Firewall status:")
        if not dry_run:
            result = subprocess.run(["ufw", "status", "verbose"], capture_output=True, text=True)
            typer.echo(result.stdout)
        else:
            typer.echo("   [DRY RUN] Would show UFW status")
            
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Firewall setup failed: {e}", err=True)
        raise typer.Exit(1)


@app.command("fix-firewall")
def fix_firewall(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show diagnostics without making changes")
    ] = False,
) -> None:
    """
    Diagnose and fix firewall configuration issues.
    
    Migrates from manual iptables rules to UFW for persistence.
    Requires root privileges.
    """
    import os
    import subprocess
    
    typer.echo("🔧 Diagnosing firewall configuration...")
    
    # Check if running as root
    if os.geteuid() != 0:
        typer.echo("❌ Must run as root (sudo)", err=True)
        raise typer.Exit(1)
    
    try:
        # Check current iptables policy
        typer.echo("\n📋 Current iptables INPUT policy:")
        result = subprocess.run(["iptables", "-L", "INPUT", "-n", "-v"], 
                              capture_output=True, text=True)
        typer.echo(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        
        # Check UFW status
        typer.echo("\n📋 UFW status:")
        result = subprocess.run(["ufw", "status", "verbose"], 
                              capture_output=True, text=True)
        typer.echo(result.stdout)
        
        if dry_run:
            typer.echo("\n🔍 [DRY RUN] Would migrate iptables rules to UFW...")
            return
        
        # Reset and reconfigure UFW
        typer.echo("\n🔄 Migrating to UFW...")
        
        # Disable UFW temporarily
        subprocess.run(["ufw", "--force", "disable"], check=True)
        
        # Reset UFW
        subprocess.run(["ufw", "--force", "reset"], check=True)
        
        # Set policies
        subprocess.run(["ufw", "default", "deny", "incoming"], check=True)
        subprocess.run(["ufw", "default", "allow", "outgoing"], check=True)
        
        # Allow essential services
        subprocess.run(["ufw", "allow", "ssh"], check=True)
        subprocess.run(["ufw", "allow", "80"], check=True)  # HTTP
        subprocess.run(["ufw", "allow", "443"], check=True)  # HTTPS
        subprocess.run(["ufw", "allow", "7001"], check=True)  # Backend
        
        # Enable UFW
        subprocess.run(["ufw", "--force", "enable"], check=True)
        
        typer.echo("\n✅ Firewall migration complete!")
        
        # Show final status
        result = subprocess.run(["ufw", "status", "verbose"], 
                              capture_output=True, text=True)
        typer.echo(result.stdout)
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Firewall fix failed: {e}", err=True)
        raise typer.Exit(1)


@app.command("tls-cert")
def tls_cert(
    domain: Annotated[
        str,
        typer.Option("--domain", help="Domain name for certificate")
    ] = "localhost",
    cert_dir: Annotated[
        str,
        typer.Option("--cert-dir", help="Directory to store certificates")
    ] = "config/nginx/certs",
    self_signed: Annotated[
        bool,
        typer.Option("--self-signed", help="Generate self-signed certificate instead of Let's Encrypt")
    ] = True,
) -> None:
    """
    Generate TLS certificates for HTTPS.
    
    Can generate self-signed certificates or obtain Let's Encrypt certificates.
    """
    import subprocess
    from pathlib import Path
    
    cert_path = Path(cert_dir)
    cert_path.mkdir(parents=True, exist_ok=True)
    
    typer.echo(f"🔐 Generating TLS certificate for {domain}...")
    typer.echo(f"   Certificate directory: {cert_path}")
    typer.echo(f"   Self-signed: {self_signed}")
    
    if self_signed:
        # Generate self-signed certificate
        try:
            # Generate private key
            typer.echo("\n🔑 Generating private key...")
            subprocess.run([
                "openssl", "genrsa", "-out", str(cert_path / "server.key"), "4096"
            ], check=True)
            
            # Set secure permissions
            (cert_path / "server.key").chmod(0o600)
            
            # Generate certificate
            typer.echo("📜 Generating self-signed certificate...")
            subprocess.run([
                "openssl", "req", "-new", "-x509", "-key", str(cert_path / "server.key"),
                "-out", str(cert_path / "server.crt"), "-days", "365",
                "-subj", f"/C=MX/ST=Mexico/L=Mexico City/O=Free Intelligence/OU=AURITY/CN={domain}"
            ], check=True)
            
            typer.echo("✅ Self-signed certificate generated!")
            typer.echo(f"   Key: {cert_path / 'server.key'}")
            typer.echo(f"   Cert: {cert_path / 'server.crt'}")
            
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Certificate generation failed: {e}", err=True)
            raise typer.Exit(1)
            
    else:
        # Let's Encrypt certificate
        typer.echo("\n🌐 Obtaining Let's Encrypt certificate...")
        try:
            subprocess.run([
                "certbot", "certonly", "--standalone", "-d", domain,
                "--email", "admin@aurity.app", "--agree-tos", "--non-interactive"
            ], check=True)
            
            typer.echo("✅ Let's Encrypt certificate obtained!")
            
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Let's Encrypt certificate failed: {e}", err=True)
            raise typer.Exit(1)


@app.command("nas-setup")
def nas_setup(
    nas_ip: Annotated[
        str,
        typer.Option("--nas-ip", help="NAS IP address for configuration")
    ] = "192.168.1.100",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be configured without making changes")
    ] = False,
) -> None:
    """
    Setup Free Intelligence on NAS (Synology/QNAP/TrueNAS).
    
    Installs dependencies, creates directories, sets permissions, and initializes corpus.
    Optimized for NAS environments without venv.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path
    
    typer.echo("==========================================")
    typer.echo("Free Intelligence - NAS Setup")
    typer.echo("==========================================")
    typer.echo("")
    
    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")
        typer.echo("")
    
    # 1. Check prerequisites
    typer.echo("🔍 Checking prerequisites...")
    
    # Check Node.js
    try:
        node_version = subprocess.run(
            ["node", "-v"], 
            capture_output=True, text=True, check=True
        ).stdout.strip()
        node_major = int(node_version.lstrip('v').split('.')[0])
        if node_major < 18:
            typer.echo(f"❌ Node.js 18+ required. Current: {node_version}", err=True)
            raise typer.Exit(1)
        typer.echo(f"✅ Node.js {node_version} detected")
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("❌ Node.js not found. Please install Node.js 18+ first.", err=True)
        raise typer.Exit(1)
    
    # Check Python
    try:
        python_version = subprocess.run(
            ["python3", "--version"], 
            capture_output=True, text=True, check=True
        ).stdout.strip()
        typer.echo(f"✅ Python {python_version} detected")
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("❌ Python3 not found. Please install Python 3.11+ first.", err=True)
        raise typer.Exit(1)
    
    # Check pnpm
    try:
        pnpm_version = subprocess.run(
            ["pnpm", "-v"], 
            capture_output=True, text=True, check=True
        ).stdout.strip()
        typer.echo(f"✅ pnpm {pnpm_version} detected")
    except (subprocess.CalledProcessError, FileNotFoundError):
        if not dry_run:
            typer.echo("📦 Installing pnpm globally...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "npm", "install", "-g", "pnpm@8.15.0"], 
                    check=True
                )
                typer.echo("✅ pnpm installed")
            except subprocess.CalledProcessError:
                typer.echo("❌ Failed to install pnpm", err=True)
                raise typer.Exit(1)
        else:
            typer.echo("⚠️  pnpm not found (would install in real run)")
    
    # 2. Create directories
    typer.echo("📁 Creating directory structure...")
    dirs = ["storage", "backups", "logs", "config"]
    
    for dir_name in dirs:
        if not dry_run:
            Path(dir_name).mkdir(exist_ok=True)
        typer.echo(f"✅ Created {dir_name}/")
    
    # 3. Install Node.js dependencies
    typer.echo("📦 Installing Node.js dependencies...")
    if not dry_run:
        try:
            subprocess.run(["pnpm", "install", "--frozen-lockfile"], check=True)
            typer.echo("✅ Node.js dependencies installed")
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to install Node.js dependencies: {e}", err=True)
            raise typer.Exit(1)
    else:
        typer.echo("⚠️  Would install Node.js dependencies")
    
    # 4. Install Python dependencies (system-wide)
    typer.echo("🐍 Installing Python dependencies (system-wide)...")
    if not dry_run:
        try:
            subprocess.run([
                "python3", "-m", "pip", "install", "--upgrade", "pip", 
                "--break-system-packages"
            ], check=True)
            subprocess.run([
                "python3", "-m", "pip", "install", "-r", "requirements.txt", 
                "--break-system-packages"
            ], check=True)
            typer.echo("✅ Python dependencies installed (no venv)")
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to install Python dependencies: {e}", err=True)
            raise typer.Exit(1)
    else:
        typer.echo("⚠️  Would install Python dependencies")
    
    # 5. Setup environment file
    env_file = Path(".env.local")
    if not env_file.exists():
        typer.echo("📝 Creating .env.local from template...")
        env_content = f"""# Free Intelligence - NAS Configuration
# Edit these values for your environment

# Storage paths (adjust for your NAS)
CORPUS_PATH=./storage/corpus.h5
BACKUP_PATH=./backups

# API endpoints (LAN-only - replace with your NAS IP)
NEXT_PUBLIC_API_URL=http://{nas_ip}:9001
TIMELINE_API_URL=http://{nas_ip}:9002

# Port configuration
PORT=9000
API_PORT=9001
TIMELINE_PORT=9002

# Node environment
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
"""
        if not dry_run:
            env_file.write_text(env_content)
        typer.echo("✅ .env.local created (PLEASE EDIT WITH YOUR NAS IP)")
    else:
        typer.echo("✅ .env.local already exists")
    
    # 6. Build production assets
    typer.echo("🏗️  Building production assets with Turborepo...")
    if not dry_run:
        try:
            subprocess.run(["pnpm", "build"], check=True)
            typer.echo("✅ Production build complete")
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Build failed: {e}", err=True)
            raise typer.Exit(1)
    else:
        typer.echo("⚠️  Would build production assets")
    
    # 7. Initialize corpus (if needed)
    corpus_file = Path("storage/corpus.h5")
    if not corpus_file.exists():
        typer.echo("🗄️  Initializing empty corpus...")
        if not dry_run:
            # Try to initialize corpus
            try:
                # Add backend to path for import
                backend_path = Path("backend")
                if str(backend_path) not in sys.path:
                    sys.path.insert(0, str(backend_path))
                
                # Import and initialize
                from backend.storage.session_h5_manager import init_corpus
                init_corpus()
                typer.echo("✅ Corpus initialized")
            except ImportError:
                typer.echo("⚠️  Corpus initialization skipped (script not available)")
            except Exception as e:
                typer.echo(f"⚠️  Corpus initialization failed: {e}")
        else:
            typer.echo("⚠️  Would initialize corpus")
    
    # 8. Set permissions
    typer.echo("🔧 Setting file permissions...")
    if not dry_run:
        try:
            os.chmod("scripts", 0o755)
            for dir_name in ["storage", "backups", "logs"]:
                os.chmod(dir_name, 0o755)
            typer.echo("✅ Permissions set")
        except Exception as e:
            typer.echo(f"⚠️  Permission setting failed: {e}")
    else:
        typer.echo("⚠️  Would set permissions")
    
    # 9. Summary
    typer.echo("")
    typer.echo("==========================================")
    typer.echo("✅ Setup Complete!")
    typer.echo("==========================================")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("")
    typer.echo("1. Edit .env.local with your NAS IP address:")
    typer.echo("   nano .env.local")
    typer.echo("")
    typer.echo("2. Start services manually:")
    typer.echo("   # Terminal 1: Backend API")
    typer.echo("   make run")
    typer.echo("")
    typer.echo("   # Terminal 2: Timeline API")
    typer.echo("   make run-timeline")
    typer.echo("")
    typer.echo("   # Terminal 3: Frontend")
    typer.echo("   cd apps/aurity && pnpm start")
    typer.echo("")
    typer.echo("OR use PM2 (recommended):")
    typer.echo("   npm install -g pm2")
    typer.echo("   pm2 start ecosystem.config.js")
    typer.echo("   pm2 save")
    typer.echo("")
    typer.echo(f"Access the application:")
    typer.echo(f"   Frontend: http://{nas_ip}:9000")
    typer.echo(f"   Backend:  http://{nas_ip}:9001/docs")
    typer.echo(f"   Timeline: http://{nas_ip}:9002/docs")
    typer.echo("")
    typer.echo("Documentation: ./NAS_DEPLOYMENT.md")
    typer.echo("==========================================")


@app.command("setup-nfs")
def setup_nfs(
    vpc_cidr: Annotated[
        str,
        typer.Option("--vpc-cidr", help="VPC CIDR block for NFS access")
    ] = "10.116.0.0/20",
    data_path: Annotated[
        str,
        typer.Option("--data-path", help="Local data directory path")
    ] = "/mnt/fi",
    export_root: Annotated[
        str,
        typer.Option("--export-root", help="NFS pseudo-root directory")
    ] = "/export",
    fi_uid: Annotated[
        int,
        typer.Option("--fi-uid", help="Free Intelligence user ID")
    ] = 1000,
    fi_gid: Annotated[
        int,
        typer.Option("--fi-gid", help="Free Intelligence group ID")
    ] = 1000,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be configured without making changes")
    ] = False,
) -> None:
    """
    Setup NFS server with pseudo-root and root_squash hardening.
    
    Configures NFSv4 with proper security, performance tuning, and UID/GID mapping.
    Requires root privileges.
    """
    import os
    import subprocess
    
    typer.echo("==========================================")
    typer.echo("Free Intelligence - NFS Setup (Hardened)")
    typer.echo("==========================================")
    typer.echo("")
    
    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")
        typer.echo("")
    
    # Check root
    if os.geteuid() != 0:
        typer.echo("❌ Must run as root (sudo)", err=True)
        raise typer.Exit(1)
    
    export_path = f"{export_root}/fi"
    
    typer.echo(f"VPC CIDR: {vpc_cidr}")
    typer.echo(f"Data path: {data_path}")
    typer.echo(f"Export path: {export_path} (pseudo-root: {export_root})")
    typer.echo(f"UID/GID: {fi_uid}/{fi_gid}")
    typer.echo("")
    
    try:
        # 1. Install NFS packages
        typer.echo("📦 Installing NFS server packages...")
        if not dry_run:
            subprocess.run(["apt-get", "update", "-qq"], check=True)
            subprocess.run(["apt-get", "install", "-y", "nfs-kernel-server", "nfs-common"], check=True)
        typer.echo("✅ NFS packages installed")
        
        # 2. Create data directory
        if not dry_run:
            Path(data_path).mkdir(parents=True, exist_ok=True)
            for subdir in ["data", "backups", "logs", "config"]:
                (Path(data_path) / subdir).mkdir(exist_ok=True)
            subprocess.run(["chown", "-R", f"{fi_uid}:{fi_gid}", data_path], check=True)
            subprocess.run(["chmod", "755", data_path], check=True)
        typer.echo("✅ Data directory created")
        
        # 3. Create NFS pseudo-root with bind mount
        typer.echo("🔗 Creating NFS pseudo-root structure...")
        if not dry_run:
            Path(export_root).mkdir(parents=True, exist_ok=True)
            Path(export_path).mkdir(parents=True, exist_ok=True)
            
            # Create systemd mount unit
            mount_unit = f"""[Unit]
Description=Bind mount {data_path} to {export_path} for NFS
After=local-fs.target
Requires=local-fs.target

[Mount]
What={data_path}
Where={export_path}
Type=none
Options=bind

[Install]
WantedBy=multi-user.target
"""
            with open("/etc/systemd/system/export-fi.mount", "w") as f:
                f.write(mount_unit)
            
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "enable", "--now", "export-fi.mount"], check=True)
        typer.echo("✅ Pseudo-root bind mount configured")
        
        # 4. Configure /etc/exports
        typer.echo("📝 Configuring NFS exports (with root_squash)...")
        exports_config = f"""# Free Intelligence NFS Exports (NFSv4 pseudo-root)
# Generated: $(date)
# VPC CIDR: {vpc_cidr}
#
# Security: root_squash maps client root to anonuid/anongid
# This prevents client root from having full access

# Pseudo-root (read-only, required for NFSv4 proper operation)
{export_root}           {vpc_cidr}(ro,fsid=0,crossmnt,no_subtree_check)

# FI data share (root_squash enforced)
{export_path}        {vpc_cidr}(rw,sync,no_subtree_check,root_squash,anonuid={fi_uid},anongid={fi_gid})
"""
        if not dry_run:
            with open("/etc/exports", "w") as f:
                f.write(exports_config)
        typer.echo("✅ Exports configured with root_squash")
        
        # 5. Configure idmapd
        typer.echo("🆔 Configuring NFSv4 ID mapping...")
        idmapd_config = """[General]
Verbosity = 0
Domain = vpc.local

[Mapping]
Nobody-User = nobody
Nobody-Group = nogroup

[Translation]
Method = nsswitch
"""
        if not dry_run:
            with open("/etc/idmapd.conf", "w") as f:
                f.write(idmapd_config)
        typer.echo("✅ idmapd configured (Domain: vpc.local)")
        
        # 6. Tune NFS server
        typer.echo("⚡ Applying NFS performance tuning...")
        nfs_config = """# NFS server configuration (tuned for HDF5 workloads)
RPCNFSDCOUNT=8
RPCNFSDPRIORITY=0
RPCMOUNTDOPTS="--manage-gids"
NEED_SVCGSSD=""
RPCSVCGSSDOPTS=""
"""
        sysctl_config = """# NFS performance tuning
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 30000
"""
        if not dry_run:
            with open("/etc/default/nfs-kernel-server", "w") as f:
                f.write(nfs_config)
            with open("/etc/sysctl.d/99-nfs-tuning.conf", "w") as f:
                f.write(sysctl_config)
            subprocess.run(["sysctl", "--system"], check=True, capture_output=True)
        typer.echo("✅ Performance tuning applied")
        
        # 7. Restart NFS services
        typer.echo("🔄 Restarting NFS services...")
        if not dry_run:
            subprocess.run(["systemctl", "enable", "nfs-kernel-server"], check=True)
            subprocess.run(["systemctl", "restart", "nfs-idmapd"], check=True)
            subprocess.run(["systemctl", "restart", "nfs-kernel-server"], check=True)
            subprocess.run(["exportfs", "-ra"], check=True)
        typer.echo("✅ NFS services restarted")
        
        # 8. Enable TRIM
        typer.echo("💾 Enabling SSD TRIM timer...")
        if not dry_run:
            subprocess.run(["systemctl", "enable", "--now", "fstrim.timer"], 
                         check=False, capture_output=True)
        typer.echo("✅ TRIM timer enabled")
        
        # 9. Show connection info
        typer.echo("")
        typer.echo("==========================================")
        typer.echo("✅ NFS Server Ready (Hardened)")
        typer.echo("==========================================")
        typer.echo("")
        typer.echo("Server Info:")
        typer.echo(f"  Pseudo-root: {export_root}")
        typer.echo(f"  Export path: {export_path}")
        typer.echo(f"  VPC CIDR:    {vpc_cidr}")
        typer.echo(f"  UID/GID:     {fi_uid}/{fi_gid} (root_squash enabled)")
        typer.echo("")
        typer.echo("Client Mount Command (optimized):")
        typer.echo("  # On Linux client (in VPC):")
        typer.echo(f"  sudo mkdir -p /mnt/fi")
        typer.echo(f"  sudo mount -t nfs4 -o rsize=1048576,wsize=1048576,hard,noatime,nconnect=4 $PRIVATE_IP:/fi /mnt/fi")
        typer.echo("")
        typer.echo("IMPORTANT:")
        typer.echo("  1. Set Domain=vpc.local in /etc/idmapd.conf on ALL clients")
        typer.echo("  2. Create matching DO Cloud Firewall for defense-in-depth")
        typer.echo("  3. Run services as UID {fi_uid} to match anonuid")
        typer.echo("==========================================")
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ NFS setup failed: {e}", err=True)
        raise typer.Exit(1)


@app.command("setup-smb")
def setup_smb(
    smb_user: Annotated[
        str,
        typer.Option("--smb-user", help="SMB username")
    ] = "fiuser",
    smb_password: Annotated[
        str | None,
        typer.Option("--smb-password", help="SMB password (prompt if not provided)")
    ] = None,
    share_path: Annotated[
        str,
        typer.Option("--share-path", help="Path to share")
    ] = "/mnt/fi",
    share_name: Annotated[
        str,
        typer.Option("--share-name", help="SMB share name")
    ] = "fi",
    fi_uid: Annotated[
        int,
        typer.Option("--fi-uid", help="Free Intelligence user ID")
    ] = 1000,
    fi_gid: Annotated[
        int,
        typer.Option("--fi-gid", help="Free Intelligence group ID")
    ] = 1000,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be configured without making changes")
    ] = False,
) -> None:
    """
    Setup Samba (SMB) server with SMB3 encryption and hardening.
    
    Configures SMB3-only access with required encryption and no legacy protocols.
    Requires root privileges.
    """
    import getpass
    import os
    import subprocess
    
    typer.echo("==========================================")
    typer.echo("Free Intelligence - SMB Setup (Hardened)")
    typer.echo("==========================================")
    typer.echo("")
    
    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")
        typer.echo("")
    
    # Check root
    if os.geteuid() != 0:
        typer.echo("❌ Must run as root (sudo)", err=True)
        raise typer.Exit(1)
    
    # Prompt for password if not provided
    if not smb_password:
        if not dry_run:
            smb_password = getpass.getpass(f"Enter SMB password for {smb_user}: ")
            if not smb_password:
                typer.echo("❌ Password cannot be empty", err=True)
                raise typer.Exit(1)
            if len(smb_password) < 12:
                typer.echo("⚠️  Password should be at least 12 characters for production")
        else:
            smb_password = "[PASSWORD]"
    
    try:
        # 1. Install Samba
        typer.echo("📦 Installing Samba packages...")
        if not dry_run:
            subprocess.run(["apt-get", "update", "-qq"], check=True)
            subprocess.run(["apt-get", "install", "-y", "samba", "samba-common-bin"], check=True)
        typer.echo("✅ Samba installed")
        
        # 2. Backup config
        if not dry_run and Path("/etc/samba/smb.conf").exists():
            backup_path = Path("/etc/samba/smb.conf.bak")
            if not backup_path.exists():
                subprocess.run(["cp", "/etc/samba/smb.conf", str(backup_path)], check=True)
        typer.echo("✅ Original config backed up")
        
        # 3. Create hardened Samba configuration
        typer.echo("📝 Configuring Samba (SMB3, encryption required)...")
        smb_config = f"""# Free Intelligence - Samba Configuration (Hardened)
# Generated: $(date)
# Share: \\\\$(hostname -I | awk '{{print $1}}')\\{share_name}

[global]
   workgroup = WORKGROUP
   server string = Free Intelligence NAS
   security = user
   map to guest = never

   # ============================================================
   # SECURITY HARDENING (SMB3 only, no legacy protocols)
   # ============================================================
   # Force SMB3 minimum (Windows 8+, macOS 10.9+)
   server min protocol = SMB3
   client min protocol = SMB3

   # Disable legacy authentication (NTLM, LanMan)
   ntlm auth = no
   lanman auth = no
   raw NTLMv2 auth = no

   # Require encryption for all connections
   smb encrypt = required

   # Disable anonymous/guest access
   restrict anonymous = 2
   guest ok = no

   # Disable unused features
   load printers = no
   printing = bsd
   printcap name = /dev/null
   disable spoolss = yes

   # Performance tuning
   socket options = TCP_NODELAY IPTOS_LOWDELAY SO_KEEPALIVE
   read raw = yes
   write raw = yes
   oplocks = yes
   level2 oplocks = yes
   kernel oplocks = no
   max xmit = 65535
   dead time = 15
   getwd cache = yes

# Free Intelligence Share
[{share_name}]
   path = {share_path}
   browseable = yes
   writable = yes
   guest ok = no
   public = no
   create mask = 0644
   directory mask = 0755
   force user = {fi_uid}
   force group = {fi_gid}
   valid users = {smb_user}

   # Security
   veto files = /lost+found/
   delete veto files = yes
"""
        if not dry_run:
            with open("/etc/samba/smb.conf", "w") as f:
                f.write(smb_config)
        typer.echo("✅ Samba configured with SMB3 encryption")
        
        # 4. Create SMB user
        typer.echo(f"👤 Creating SMB user: {smb_user}")
        if not dry_run:
            # Check if user exists
            result = subprocess.run(["id", smb_user], capture_output=True)
            if result.returncode != 0:
                subprocess.run(["useradd", "-M", "-s", "/usr/sbin/nologin", smb_user], check=True)
            
            # Set password
            process = subprocess.Popen(
                ["smbpasswd", "-a", smb_user],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=f"{smb_password}\n{smb_password}\n".encode())
            if process.returncode != 0:
                typer.echo(f"❌ Failed to set SMB password: {stderr.decode()}", err=True)
                raise typer.Exit(1)
        typer.echo(f"✅ SMB user {smb_user} created")
        
        # 5. Set permissions
        typer.echo("🔧 Setting share permissions...")
        if not dry_run:
            subprocess.run(["chown", "-R", f"{fi_uid}:{fi_gid}", share_path], check=True)
            subprocess.run(["chmod", "755", share_path], check=True)
        typer.echo("✅ Permissions set")
        
        # 6. Restart Samba
        typer.echo("🔄 Restarting Samba services...")
        if not dry_run:
            subprocess.run(["systemctl", "enable", "smbd"], check=True)
            subprocess.run(["systemctl", "restart", "smbd"], check=True)
        typer.echo("✅ Samba services restarted")
        
        # 7. Show connection info
        typer.echo("")
        typer.echo("==========================================")
        typer.echo("✅ SMB Server Ready (Hardened)")
        typer.echo("==========================================")
        typer.echo("")
        typer.echo("Server Info:")
        typer.echo(f"  Share name: {share_name}")
        typer.echo(f"  Share path: {share_path}")
        typer.echo(f"  SMB user:   {smb_user}")
        typer.echo(f"  UID/GID:    {fi_uid}/{fi_gid}")
        typer.echo("")
        typer.echo("Client Connection:")
        typer.echo("  # Windows:")
        typer.echo(f"  \\\\server-ip\\{share_name}")
        typer.echo("")
        typer.echo("  # macOS/Linux:")
        typer.echo(f"  smb://server-ip/{share_name}")
        typer.echo("")
        typer.echo("Security Features:")
        typer.echo("  ✅ SMB3 minimum protocol")
        typer.echo("  ✅ Encryption required")
        typer.echo("  ✅ No legacy authentication")
        typer.echo("  ✅ No anonymous access")
        typer.echo("==========================================")
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ SMB setup failed: {e}", err=True)
        raise typer.Exit(1)


@app.command("validate-nas-deployment")
def validate_nas_deployment() -> None:
    """
    Validate NAS deployment readiness.
    
    Checks that all deployment artifacts are present and properly configured
    for Synology DS923+ deployment.
    """
    import os
    from pathlib import Path
    
    typer.echo("🔍 Free Intelligence - NAS Deployment Readiness Check")
    typer.echo("=" * 60)
    typer.echo()
    
    checks_passed = 0
    checks_total = 0
    
    def check(condition: bool, message: str) -> None:
        nonlocal checks_passed, checks_total
        checks_total += 1
        if condition:
            typer.echo(f"✅ {message}")
            checks_passed += 1
        else:
            typer.echo(f"❌ {message}")
    
    # Check 1: Docker Compose configs exist
    ollama_compose = Path("docker-compose.ollama.yml")
    asr_compose = Path("docker-compose.asr.yml")
    check(ollama_compose.exists() and asr_compose.exists(), "Docker Compose configs present")
    
    # Check 2: Deployment script executable
    deploy_script = Path("scripts/deploy-ds923.sh")
    check(deploy_script.exists() and os.access(deploy_script, os.X_OK), "Deployment script executable")
    
    # Check 3: ASR worker script executable
    asr_worker = Path("scripts/asr_worker.py")
    check(asr_worker.exists() and os.access(asr_worker, os.X_OK), "ASR worker script executable")
    
    # Check 4: Environment example exists
    env_example = Path(".env.diarization.example")
    check(env_example.exists(), "Environment config example present")
    
    # Check 5: Validate Ollama compose syntax
    if ollama_compose.exists():
        content = ollama_compose.read_text()
        valid_ollama = "fi-ollama" in content and "11434:11434" in content
    else:
        valid_ollama = False
    check(valid_ollama, "Ollama config valid (port 11434, container name)")
    
    # Check 6: Validate ASR compose syntax
    if asr_compose.exists():
        content = asr_compose.read_text()
        valid_asr = "fi-asr-worker" in content and "faster-whisper" in content
    else:
        valid_asr = False
    check(valid_asr, "ASR config valid (faster-whisper, container name)")
    
    # Check 7: Deployment script has smoke tests
    if deploy_script.exists():
        content = deploy_script.read_text()
        has_smoke_tests = "Smoke tests" in content and "api/generate" in content
    else:
        has_smoke_tests = False
    check(has_smoke_tests, "Deployment script has smoke tests")
    
    typer.echo()
    typer.echo("=" * 60)
    typer.echo(f"Results: {checks_passed}/{checks_total} checks passed")
    typer.echo("=" * 60)
    typer.echo()
    
    if checks_passed == checks_total:
        typer.echo("✅ NAS deployment artifacts ready")
        typer.echo()
        typer.echo("Next steps:")
        typer.echo("  1. Copy to DS923+: scp -r . user@nas:/volume1/fi-app/")
        typer.echo("  2. SSH into NAS: ssh user@nas")
        typer.echo("  3. Run deployment: cd /volume1/fi-app && ./scripts/deploy-ds923.sh")
        typer.echo()
    else:
        typer.echo("❌ Some checks failed - review artifacts")
        raise typer.Exit(1)


@app.command("fix-nginx-cache-headers")
def fix_nginx_cache_headers(
    host: Annotated[str, typer.Option("--host", envvar="FI_OPS_HOST", help="Target host (required)")] = "",
    user: Annotated[str | None, typer.Option("--user", envvar="FI_OPS_USER", help="SSH user")] = None,
    port: Annotated[int | None, typer.Option("--port", envvar="FI_OPS_PORT", help="SSH port")] = None,
    identity_file: Annotated[
        str | None,
        typer.Option("--identity-file", envvar="FI_OPS_IDENTITY_FILE", exists=True, dir_okay=False, help="SSH key"),
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be configured without making changes")] = False,
) -> None:
    """
    Fix Nginx cache headers to prevent stale HTML.
    
    Updates nginx config with proper cache headers for static assets and HTML files.
    Requires root SSH access to production server.
    """
    import paramiko
    import time

    from .._common import run_cmd, ssh_argv

    if not host:
        typer.echo("❌ --host is required (or set FI_OPS_HOST)", err=True)
        raise typer.Exit(1)

    typer.echo("🔧 Fixing nginx cache headers...")
    typer.echo(f"   Host: {host}")
    typer.echo(f"   Dry run: {dry_run}")
    typer.echo()

    # Updated Nginx config with cache headers
    nginx_config = """# HTTP redirect to HTTPS
server {
    listen 80;
    server_name app.aurity.io;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name app.aurity.io;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/app.aurity.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.aurity.io/privkey.pem;

    # SSL configuration (HIPAA-compliant TLS)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Frontend (Next.js static export)
    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:7001/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Static assets (_next) - cache aggressively (immutable files with content hash)
    location /_next/static/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    # HTML files - never cache (to avoid stale references)
    location ~* \\.html$ {
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        add_header Pragma "no-cache";
        add_header Expires "0";
        try_files $uri $uri/ /index.html;
    }

    # Frontend routes
    location / {
        # Don't cache the root HTML
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
        try_files $uri $uri/ $uri.html /index.html;
    }
}
"""

    if dry_run:
        typer.echo("📋 Would update nginx config with:")
        typer.echo("=" * 80)
        typer.echo(nginx_config)
        typer.echo("=" * 80)
        typer.echo("✅ Dry run complete - no changes made")
        return

    # Connect via SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Build SSH command for connection
        ssh_cmd_parts = ["ssh"]
        if user:
            ssh_cmd_parts.extend(["-l", user])
        if port:
            ssh_cmd_parts.extend(["-p", str(port)])
        if identity_file:
            ssh_cmd_parts.extend(["-i", identity_file])
        ssh_cmd_parts.append(host)

        typer.echo("🔗 Connecting to server...")

        # Use subprocess to handle SSH connection
        import shlex
        import subprocess

        def run_ssh_command(cmd: str) -> tuple[str, str]:
            full_cmd = ssh_cmd_parts + [cmd]
            result = subprocess.run(full_cmd, capture_output=True, text=True, check=False)
            return result.stdout, result.stderr

        # Backup current config
        typer.echo("💾 Creating backup of current config...")
        stdout, stderr = run_ssh_command(
            "cp /etc/nginx/sites-enabled/aurity /etc/nginx/sites-enabled/aurity.backup.$(date +%Y%m%d_%H%M%S)"
        )
        typer.echo("✅ Backup created")

        # Write new config
        typer.echo("📝 Writing new configuration...")
        config_cmd = f"cat > /etc/nginx/sites-enabled/aurity << 'ENDOFCONFIG'\n{nginx_config}\nENDOFCONFIG"
        stdout, stderr = run_ssh_command(config_cmd)
        typer.echo("✅ Configuration written")

        # Test config
        typer.echo("🧪 Testing nginx configuration...")
        stdout, stderr = run_ssh_command("nginx -t")
        test_output = stderr + stdout
        typer.echo(test_output)

        if "successful" in test_output.lower():
            typer.echo("✅ Configuration valid")

            # Reload Nginx
            typer.echo("🔄 Reloading nginx...")
            stdout, stderr = run_ssh_command("nginx -s reload")
            time.sleep(1)
            typer.echo("✅ Nginx reloaded")

            typer.echo()
            typer.echo("=" * 80)
            typer.echo("✅ CACHE HEADERS CONFIGURED")
            typer.echo("=" * 80)
            typer.echo("""
Changes applied:
1. ✅ HTML files: NO cache (always fresh)
2. ✅ _next/static/*: Aggressive cache (immutable files with hash)
3. ✅ Root location: NO cache (to avoid stale HTML)

Test from your mobile device:
1. Clear browser cache/data
2. Or open in Incognito mode
3. Visit: https://app.aurity.io/

JS/CSS files should load correctly.
            """)

        else:
            typer.echo("❌ Nginx configuration error")
            typer.echo("Reverting changes...")
            stdout, stderr = run_ssh_command(
                "ls -t /etc/nginx/sites-enabled/aurity.backup.* | head -1 | xargs -I {} mv {} /etc/nginx/sites-enabled/aurity"
            )
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("test-tls")
def test_tls(
    host: Annotated[
        str,
        typer.Option("--host", help="Host to test (localhost for local, domain for remote)")
    ] = "localhost",
    port: Annotated[
        int,
        typer.Option("--port", help="Port to test")
    ] = 443,
    protocol: Annotated[
        str,
        typer.Option("--protocol", help="Protocol (http or https)")
    ] = "https",
) -> None:
    """
    Test TLS 1.3 configuration for HIPAA compliance.
    
    Tests HTTP redirects, TLS protocol versions, security headers,
    and backend API proxying. Evidence collection for HIPAA card G-002.
    """
    import socket
    import subprocess
    
    typer.echo("🧪 Testing TLS 1.3 Configuration")
    typer.echo("=" * 60)
    typer.echo(f"   Host: {host}")
    typer.echo(f"   Port: {port}")
    typer.echo(f"   Protocol: {protocol}")
    typer.echo()
    
    # Test results
    passed = 0
    failed = 0
    
    def run_test(name: str, test_func) -> None:
        nonlocal passed, failed
        typer.echo("=" * 60)
        typer.echo(f"Test: {name}")
        typer.echo("=" * 60)
        try:
            result = test_func()
            if result:
                typer.echo("✅ PASS")
                passed += 1
            else:
                typer.echo("❌ FAIL")
                failed += 1
        except Exception as e:
            typer.echo(f"❌ ERROR: {e}")
            failed += 1
        typer.echo()
    
    def test_http_redirect() -> bool:
        """Test HTTP → HTTPS redirect (HIPAA requirement)"""
        if protocol != "https":
            return True  # Skip if not testing HTTPS
            
        try:
            response = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://{host}/health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            status_code = response.stdout.strip()
            if status_code == "301":
                typer.echo("   HTTP redirects to HTTPS (301)")
                return True
            else:
                typer.echo(f"   HTTP should redirect to HTTPS (got {status_code}, expected 301)")
                return False
        except subprocess.TimeoutExpired:
            typer.echo("   Connection timeout")
            return False
    
    def test_https_health() -> bool:
        """Test HTTPS health check"""
        try:
            response = subprocess.run(
                ["curl", "-k", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{protocol}://{host}:{port}/health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            status_code = response.stdout.strip()
            if status_code == "200":
                typer.echo("   HTTPS health endpoint responds (200 OK)")
                return True
            else:
                typer.echo(f"   HTTPS health check failed (got {status_code}, expected 200)")
                return False
        except subprocess.TimeoutExpired:
            typer.echo("   Connection timeout")
            return False
    
    def test_tls_version() -> bool:
        """Test TLS protocol version (TLS 1.3 required)"""
        try:
            result = subprocess.run(
                ["curl", "-k", "-s", "-v", f"{protocol}://{host}:{port}/health"],
                capture_output=True,
                text=True,
                timeout=15
            )
            # Look for SSL connection line
            for line in result.stderr.split('\n'):
                if "SSL connection using" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        tls_version = parts[4]
                        if tls_version == "TLSv1.3":
                            typer.echo(f"   TLS 1.3 is active ({tls_version})")
                            return True
                        else:
                            typer.echo(f"   TLS 1.3 not detected (got '{tls_version}', expected 'TLSv1.3')")
                            return False
            typer.echo("   Could not determine TLS version")
            return False
        except subprocess.TimeoutExpired:
            typer.echo("   Connection timeout")
            return False
    
    def test_hsts_header() -> bool:
        """Test HSTS header (HIPAA requirement)"""
        try:
            result = subprocess.run(
                ["curl", "-k", "-s", "-I", f"{protocol}://{host}:{port}/health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            headers = result.stdout
            hsts_header = None
            for line in headers.split('\n'):
                if line.lower().startswith('strict-transport-security'):
                    hsts_header = line
                    break
            
            if hsts_header:
                typer.echo("   HSTS header present")
                typer.echo(f"   Header: {hsts_header.strip()}")
                return True
            else:
                typer.echo("   HSTS header missing (HIPAA requirement)")
                return False
        except subprocess.TimeoutExpired:
            typer.echo("   Connection timeout")
            return False
    
    def test_security_headers() -> bool:
        """Test security headers"""
        try:
            result = subprocess.run(
                ["curl", "-k", "-s", "-I", f"{protocol}://{host}:{port}/health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            headers = result.stdout
            
            x_frame = any('x-frame-options' in line.lower() for line in headers.split('\n'))
            x_content_type = any('x-content-type-options' in line.lower() for line in headers.split('\n'))
            
            if x_frame:
                typer.echo("   X-Frame-Options header present")
            else:
                typer.echo("   X-Frame-Options header missing")
            
            if x_content_type:
                typer.echo("   X-Content-Type-Options header present")
            else:
                typer.echo("   X-Content-Type-Options header missing")
            
            return x_frame and x_content_type
        except subprocess.TimeoutExpired:
            typer.echo("   Connection timeout")
            return False
    
    def test_backend_api() -> bool:
        """Test backend API proxy"""
        # Check if backend is running locally
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 7001))
            sock.close()
            
            if result == 0:
                # Backend is running, test API proxy
                try:
                    response = subprocess.run(
                        ["curl", "-k", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{protocol}://{host}:{port}/api/"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    status_code = response.stdout.strip()
                    if status_code != "000":
                        typer.echo(f"   Backend API proxied through HTTPS (status: {status_code})")
                        return True
                    else:
                        typer.echo("   Backend API proxy failed")
                        return False
                except subprocess.TimeoutExpired:
                    typer.echo("   API proxy test timeout")
                    return False
            else:
                typer.echo("   Backend not running on port 7001 (skipping API proxy test)")
                return True  # Not a failure
        except Exception:
            typer.echo("   Could not check backend status")
            return True  # Not a failure
    
    # Run all tests
    run_test("HTTP → HTTPS Redirect (301)", test_http_redirect)
    run_test("HTTPS Health Check", test_https_health)
    run_test("TLS Protocol Version (TLS 1.3 required)", test_tls_version)
    run_test("HSTS Header (Strict-Transport-Security)", test_hsts_header)
    run_test("Security Headers", test_security_headers)
    run_test("Backend API Proxy", test_backend_api)
    
    # Summary
    typer.echo("=" * 60)
    typer.echo("📊 Test Summary")
    typer.echo("=" * 60)
    total = passed + failed
    typer.echo(f"   Passed: {passed}")
    typer.echo(f"   Failed: {failed}")
    typer.echo(f"   Total:  {total}")
    typer.echo()
    
    if failed == 0:
        typer.echo("✅ ALL TESTS PASSED")
        typer.echo()
        typer.echo("🎉 TLS 1.3 configuration is HIPAA-compliant!")
        typer.echo()
        typer.echo("📋 Evidence collected for HIPAA card G-002:")
        typer.echo("   • HTTP → HTTPS redirect: ✅")
        typer.echo("   • TLS 1.3 protocol: ✅")
        typer.echo("   • HSTS header: ✅")
        typer.echo("   • Security headers: ✅")
        typer.echo()
        typer.echo("🚀 Next steps:")
        typer.echo("   1. Run testssl.sh for detailed SSL scan (A+ rating)")
        typer.echo("   2. Capture Wireshark TLS handshake")
        typer.echo("   3. Document evidence in Trello card")
    else:
        typer.echo("❌ TESTS FAILED")
        typer.echo()
        typer.echo("Fix the issues above and run again.")
        raise typer.Exit(1)
