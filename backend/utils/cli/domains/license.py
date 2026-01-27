"""
License CLI Commands for Aurity Desktop

Commands for managing software licenses:
- fi license init-keys       Generate Ed25519 keypair
- fi license generate        Create a new license key
- fi license verify          Verify a license key
- fi license info            Show license key details
- fi license export-pubkey   Export public key for embedding

Usage examples:
    # First-time setup: generate keypair
    fi license init-keys

    # Generate a license (clinics are created AFTER activation)
    fi license generate \
        --max-clinics=3 \
        --holder="Hospital Central" \
        --features=soap,timeline,prescriptions \
        --expires=2026-01-01 \
        --auth0-domain=dev-xxx.us.auth0.com \
        --auth0-client-id=HBevb9... \
        --auth0-audience=https://app.aurity.io

    # Verify a license key
    fi license verify AURITY-XXXX-XXXX-XXXX-...

    # Export public key for Tauri
    fi license export-pubkey --format=rust
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from typing import Annotated

import typer

app = typer.Typer(
    name="license",
    help="License key management for Aurity Desktop",
    no_args_is_help=True,
)


@app.command("init-keys")
def init_keys(
    force: Annotated[
        bool,
        typer.Option(
            "--force", help="Overwrite existing keypair (DANGER: invalidates all licenses!)"
        ),
    ] = False,
) -> None:
    """
    Generate a new Ed25519 keypair for license signing.

    The private key is stored in ~/.aurity-admin/license.key (NEVER share this!)
    The public key is stored in ~/.aurity-admin/license.pub (embed in desktop app)
    """
    from backend.api.license import generate_keypair

    typer.echo("🔐 Generating Ed25519 keypair for license signing...")

    if force:
        typer.echo("⚠️  WARNING: --force flag will overwrite existing keys!")
        typer.echo("   This will INVALIDATE all previously generated licenses!")
        if not typer.confirm("Are you absolutely sure?"):
            raise typer.Exit(0)

    try:
        _private_pem, _public_pem = generate_keypair(force=force)

        typer.echo("")
        typer.echo("✅ Keypair generated successfully!")
        typer.echo("")
        typer.echo("📁 Key locations:")
        typer.echo("   Private key: ~/.aurity-admin/license.key (KEEP SECRET!)")
        typer.echo("   Public key:  ~/.aurity-admin/license.pub")
        typer.echo("")
        typer.echo("📝 Next steps:")
        typer.echo("   1. Keep private key secure (never commit to git!)")
        typer.echo("   2. Export public key for Tauri: fi license export-pubkey --format=rust")
        typer.echo("   3. Generate licenses: fi license generate --help")

    except FileExistsError as e:
        typer.echo(f"❌ {e}", err=True)
        typer.echo("   Use --force to overwrite (DANGER: invalidates all licenses!)")
        raise typer.Exit(1)


@app.command("generate")
def generate(
    max_clinics: Annotated[
        int, typer.Option("--max-clinics", help="Maximum number of clinics allowed (default: 1)")
    ] = 1,
    license_holder: Annotated[
        str, typer.Option("--holder", help="License holder name (e.g., 'Dr. García' or 'Hospital Central')")
    ] = "",
    auth0_domain: Annotated[
        str, typer.Option("--auth0-domain", help="Auth0 tenant domain (e.g., dev-xxx.us.auth0.com)")
    ] = "",
    auth0_client_id: Annotated[
        str, typer.Option("--auth0-client-id", help="Auth0 application client ID")
    ] = "",
    auth0_audience: Annotated[
        str, typer.Option("--auth0-audience", help="Auth0 API audience")
    ] = "https://app.aurity.io",
    features: Annotated[
        str,
        typer.Option(
            "--features", help="Comma-separated feature flags (e.g., soap,timeline,prescriptions)"
        ),
    ] = "soap,timeline,prescriptions",
    expires: Annotated[
        str, typer.Option("--expires", help="Expiration date (YYYY-MM-DD) or 'never' for perpetual")
    ] = "",
    days: Annotated[
        int, typer.Option("--days", help="Days until expiration (alternative to --expires)")
    ] = 365,
) -> None:
    """
    Generate a new signed license key.

    The license key encodes Auth0 credentials, features, max clinics, and expiration.
    Clinics are created AFTER activation by the admin (up to max_clinics limit).
    """
    from datetime import timedelta

    from backend.api.license import LicensePayload, format_license_key_display, generate_license_key

    typer.echo("🔑 Generating new license key...")

    # Validate required fields
    if not auth0_domain:
        typer.echo("❌ --auth0-domain is required", err=True)
        raise typer.Exit(1)

    if not auth0_client_id:
        typer.echo("❌ --auth0-client-id is required", err=True)
        raise typer.Exit(1)

    if max_clinics < 1:
        typer.echo("❌ --max-clinics must be at least 1", err=True)
        raise typer.Exit(1)

    # Parse features
    feature_list = [f.strip() for f in features.split(",") if f.strip()]

    # Calculate expiration
    if expires == "never":
        expires_at = ""
    elif expires:
        try:
            expires_dt = datetime.strptime(expires, "%Y-%m-%d").replace(tzinfo=UTC)
            expires_at = expires_dt.isoformat()
        except ValueError:
            typer.echo(f"❌ Invalid date format: {expires}. Use YYYY-MM-DD", err=True)
            raise typer.Exit(1)
    else:
        expires_dt = datetime.now(UTC) + timedelta(days=days)
        expires_at = expires_dt.isoformat()

    # Create payload
    payload = LicensePayload(
        auth0_domain=auth0_domain,
        auth0_client_id=auth0_client_id,
        auth0_audience=auth0_audience,
        max_clinics=max_clinics,
        license_holder=license_holder,
        features=feature_list,
        expires_at=expires_at,
    )

    try:
        license_key = generate_license_key(payload)

        typer.echo("")
        typer.echo("✅ License key generated successfully!")
        typer.echo("")
        typer.echo("═" * 60)
        typer.echo("📋 LICENSE KEY:")
        typer.echo("═" * 60)
        typer.echo("")
        typer.echo(format_license_key_display(license_key))
        typer.echo("")
        typer.echo("═" * 60)
        typer.echo("")
        typer.echo("📝 License Details:")
        typer.echo(f"   License ID:   {payload.license_id}")
        typer.echo(f"   Holder:       {license_holder or '(not specified)'}")
        typer.echo(f"   Max Clinics:  {max_clinics}")
        typer.echo(f"   Features:     {', '.join(feature_list)}")
        if expires_at:
            typer.echo(f"   Expires:      {expires_at}")
        else:
            typer.echo("   Expires:      Never (perpetual)")
        typer.echo(f"   Auth0:        {auth0_domain}")
        typer.echo("")
        typer.echo("📤 Send this key to the customer for activation.")

    except FileNotFoundError as e:
        typer.echo(f"❌ {e}", err=True)
        typer.echo("   Run 'fi license init-keys' first to generate a keypair.")
        raise typer.Exit(1)


@app.command("verify")
def verify(
    license_key: Annotated[
        str, typer.Argument(help="The license key to verify (AURITY-XXXX-XXXX-...)")
    ],
) -> None:
    """
    Verify a license key's signature and validity.

    Checks:
    - Signature validity (Ed25519)
    - Expiration status
    - Format correctness
    """
    from backend.api.license import LicenseStatus, validate_license

    typer.echo("🔍 Verifying license key...")

    result = validate_license(license_key)

    typer.echo("")

    if result.status == LicenseStatus.VALID:
        typer.echo("✅ LICENSE VALID")
        typer.echo("")
        typer.echo("📝 License Details:")
        if result.payload:
            typer.echo(f"   License ID:   {result.payload.license_id}")
            typer.echo(f"   Holder:       {result.payload.license_holder or '(not specified)'}")
            typer.echo(f"   Max Clinics:  {result.payload.max_clinics}")
            typer.echo(f"   Features:     {', '.join(result.payload.features)}")
            typer.echo(f"   Issued:       {result.payload.issued_at}")
            if result.payload.expires_at:
                typer.echo(f"   Expires:      {result.payload.expires_at}")
                if result.days_remaining is not None:
                    if result.days_remaining > 30:
                        typer.echo(f"   Remaining:    {result.days_remaining} days")
                    else:
                        typer.echo(f"   ⚠️  Remaining: {result.days_remaining} days (expires soon!)")
            else:
                typer.echo("   Expires:      Never (perpetual)")

    elif result.status == LicenseStatus.EXPIRED:
        typer.echo("❌ LICENSE EXPIRED")
        typer.echo("")
        typer.echo(f"   {result.message}")
        if result.payload:
            typer.echo(f"   Expired on: {result.payload.expires_at}")
        raise typer.Exit(1)

    elif result.status == LicenseStatus.INVALID_SIGNATURE:
        typer.echo("❌ INVALID SIGNATURE")
        typer.echo("")
        typer.echo("   The license key signature could not be verified.")
        typer.echo("   This license may be tampered with or generated with a different key.")
        raise typer.Exit(1)

    elif result.status == LicenseStatus.INVALID_FORMAT:
        typer.echo("❌ INVALID FORMAT")
        typer.echo("")
        typer.echo(f"   {result.message}")
        raise typer.Exit(1)

    else:
        typer.echo(f"❌ {result.status.value.upper()}")
        typer.echo(f"   {result.message}")
        raise typer.Exit(1)


@app.command("info")
def info(
    license_key: Annotated[
        str, typer.Argument(help="The license key to inspect (AURITY-XXXX-XXXX-...)")
    ],
    show_auth0: Annotated[
        bool, typer.Option("--show-auth0", help="Show full Auth0 credentials (normally masked)")
    ] = False,
) -> None:
    """
    Display detailed information about a license key.

    Note: This decodes the key WITHOUT validating the signature.
    Use 'verify' to check signature validity.
    """
    from backend.api.license import decode_license_key

    typer.echo("📋 Decoding license key...")

    try:
        payload, _signature = decode_license_key(license_key)

        typer.echo("")
        typer.echo("═" * 50)
        typer.echo("LICENSE INFORMATION")
        typer.echo("═" * 50)
        typer.echo("")
        typer.echo(f"License ID:    {payload.license_id}")
        typer.echo(f"Version:       {payload.version}")
        typer.echo("")
        typer.echo("Capacity:")
        typer.echo(f"  Holder:      {payload.license_holder or '(not specified)'}")
        typer.echo(f"  Max Clinics: {payload.max_clinics}")
        typer.echo("")
        typer.echo("Features:")
        for feature in payload.features:
            typer.echo(f"  ✓ {feature}")
        typer.echo("")
        typer.echo("Validity:")
        typer.echo(f"  Issued:      {payload.issued_at}")
        if payload.expires_at:
            typer.echo(f"  Expires:     {payload.expires_at}")
            if payload.is_expired():
                typer.echo("  Status:      ❌ EXPIRED")
            else:
                typer.echo("  Status:      ✅ Active")
        else:
            typer.echo("  Expires:     Never")
            typer.echo("  Status:      ✅ Perpetual")
        typer.echo("")
        typer.echo("Auth0 Configuration:")
        typer.echo(f"  Domain:      {payload.auth0_domain}")
        if show_auth0:
            typer.echo(f"  Client ID:   {payload.auth0_client_id}")
        else:
            masked = payload.auth0_client_id[:4] + "*" * (len(payload.auth0_client_id) - 4)
            typer.echo(f"  Client ID:   {masked}")
        typer.echo(f"  Audience:    {payload.auth0_audience}")
        typer.echo("")
        typer.echo("═" * 50)

    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)


@app.command("export-pubkey")
def export_pubkey(
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: pem, base64, rust, typescript"),
    ] = "pem",
    output: Annotated[
        str, typer.Option("--output", "-o", help="Output file path (default: stdout)")
    ] = "",
) -> None:
    """
    Export the public key for embedding in the desktop app.

    Formats:
    - pem: Standard PEM format
    - base64: Base64-encoded PEM
    - rust: Rust const for Tauri
    - typescript: TypeScript const for frontend
    """
    from backend.api.license import get_public_key_for_embedding
    from backend.api.license.generator import PUBLIC_KEY_PATH

    typer.echo("📤 Exporting public key...")

    try:
        # Get raw PEM
        pem_bytes = PUBLIC_KEY_PATH.read_bytes()
        pem_str = pem_bytes.decode("utf-8").strip()

        if output_format == "pem":
            content = pem_str
        elif output_format == "base64":
            content = get_public_key_for_embedding()
        elif output_format == "rust":
            b64 = get_public_key_for_embedding()
            content = f"""// Auto-generated by: fi license export-pubkey --format=rust
// DO NOT EDIT MANUALLY

/// Ed25519 public key for license verification (base64-encoded PEM)
pub const LICENSE_PUBLIC_KEY: &str = "{b64}";
"""
        elif output_format == "typescript":
            b64 = get_public_key_for_embedding()
            content = f"""// Auto-generated by: fi license export-pubkey --format=typescript
// DO NOT EDIT MANUALLY

/** Ed25519 public key for license verification (base64-encoded PEM) */
export const LICENSE_PUBLIC_KEY = "{b64}";
"""
        else:
            typer.echo(f"❌ Unknown format: {output_format}", err=True)
            typer.echo("   Valid formats: pem, base64, rust, typescript")
            raise typer.Exit(1)

        if output:
            with open(output, "w") as f:
                f.write(content)
            typer.echo(f"✅ Public key exported to: {output}")
        else:
            typer.echo("")
            typer.echo(content)

    except FileNotFoundError:
        typer.echo("❌ Public key not found!", err=True)
        typer.echo("   Run 'fi license init-keys' first to generate a keypair.")
        raise typer.Exit(1)


@app.command("list")
def list_licenses() -> None:
    """
    List all generated licenses (placeholder for future database).

    Note: Currently not implemented. Licenses are stateless.
    Consider storing generated licenses in a database for tracking.
    """
    typer.echo("📋 License tracking not yet implemented.")
    typer.echo("")
    typer.echo("   Generated licenses are currently stateless.")
    typer.echo("   Consider storing them in a database for:")
    typer.echo("   - Tracking active licenses")
    typer.echo("   - Revocation management")
    typer.echo("   - Renewal reminders")
    typer.echo("")
    typer.echo("   For now, verify individual licenses with:")
    typer.echo("   fi license verify AURITY-XXXX-...")
