from __future__ import annotations

import typer
from typing import Annotated

from .._common import redact_text

app = typer.Typer(name="auth", help="Auth0 and RBAC maintenance", no_args_is_help=True)

@app.command("assign-superadmin")
def assign_superadmin(
	email: Annotated[str, typer.Argument(help="User email (input only; not printed)")],
) -> None:
	"""Assign FI-superadmin role to user identified by email."""
	from backend.src.fi_auth.services.auth0_management import get_auth0_service

	service = get_auth0_service()

	response = service.list_users(search=f'email:"{email}"', per_page=1)
	users = response.get("users", [])
	if not users:
		typer.echo("❌ User not found")
		raise typer.Exit(code=1)

	user_id = users[0].get("user_id")
	if not user_id:
		typer.echo("❌ User record missing user_id")
		raise typer.Exit(code=1)

	all_roles = service.list_roles()
	superadmin_role: dict[str, object] | None = None
	for role in all_roles:
		if role.get("name") == "FI-superadmin":
			superadmin_role = role
			break

	if not superadmin_role:
		superadmin_role = service.create_role(  # type: ignore[attr-defined]
			name="FI-superadmin",
			description=(
				"Free Intelligence Superadmin - Full system access for user management and configuration"
			),
		)

	role_id = superadmin_role.get("id")
	if not isinstance(role_id, str) or not role_id:
		typer.echo("❌ Could not resolve role id")
		raise typer.Exit(code=1)

	current_roles = service.get_user_roles(user_id)
	current_names = {r.get("name") for r in current_roles if isinstance(r, dict)}
	if "FI-superadmin" in current_names:
		typer.echo("⚠️  User already has FI-superadmin")
		typer.echo(f"user_id={redact_text(user_id)}")
		return

	service.assign_roles(user_id, [role_id])
	typer.echo("✅ Role assigned")
	typer.echo(f"user_id={redact_text(user_id)}")
	typer.echo("Next: user must logout/login to refresh JWT")


@app.command("link-accounts")
def link_accounts(
	primary_user_id: Annotated[str, typer.Option("--primary", help="Primary Auth0 user_id (kept)")],
	secondary_user_id: Annotated[
		str, typer.Option("--secondary", help="Secondary Auth0 user_id (linked into primary)")
	],
) -> None:
	"""
	Link two Auth0 user accounts (merge identities securely).
	- The secondary account will be linked into the primary.
	- Roles and metadata are preserved in the primary.
	- This operation is irreversible.
	"""
	from .._common import redact_text
	typer.echo("=" * 60)
	typer.echo("🔗 VINCULAR CUENTAS DE AUTH0")
	typer.echo("=" * 60)
	typer.echo("")
	typer.echo("⚠️  ADVERTENCIA: Esta operación es IRREVERSIBLE")
	typer.echo("")
	typer.echo(f"Cuenta principal (se mantiene): {redact_text(primary_user_id)}")
	typer.echo(f"Cuenta secundaria (se vincula): {redact_text(secondary_user_id)}")
	typer.echo("")
	confirm = typer.prompt("Escribe 'VINCULAR' para confirmar", default="")
	if confirm != "VINCULAR":
		typer.echo("❌ Operación cancelada")
		raise typer.Exit(code=0)

	typer.echo("")
	typer.echo("🔧 Procesando...")
	typer.echo("")
	try:
		from backend.src.fi_auth.services.auth0_management import get_auth0_service
		service = get_auth0_service()
		service.link_user_account(primary_user_id=primary_user_id, secondary_user_id=secondary_user_id)
		typer.echo("=" * 60)
		typer.echo("✅ CUENTAS VINCULADAS EXITOSAMENTE")
		typer.echo("=" * 60)
		typer.echo("")
		typer.echo("🎯 Ahora puedes hacer login con ambos métodos vinculados a la misma cuenta.")
		typer.echo("📝 Nota: En User Management verás solo 1 cuenta con identidades vinculadas.")
	except Exception as e:
		typer.echo(f"\n❌ Error: {redact_text(str(e))}", err=True)
		import traceback
		typer.echo(redact_text(traceback.format_exc()), err=True)
		raise typer.Exit(code=1)


@app.command("setup-auth0-action")
def setup_auth0_action() -> None:
	"""
	Setup Auth0 Action for JWT Custom Claims (Roles).
	
	Creates an Auth0 Action to add roles to JWT tokens, deploys it,
	and binds it to the Login flow (post-login trigger).
	
	The Action adds roles to both ID token (frontend) and Access token (backend)
	using the custom claim namespace: https://aurity.app/roles
	"""
	import os
	import requests
	from typing import Optional
	
	# Action configuration
	ACTION_NAME = "Add Roles to Token"
	ACTION_CODE = """
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://aurity.app';

  if (event.authorization) {
    // Add roles to ID token (frontend)
    api.idToken.setCustomClaim(
      `${namespace}/roles`,
      event.authorization.roles
    );

    // Add roles to access token (backend)
    api.accessToken.setCustomClaim(
      `${namespace}/roles`,
      event.authorization.roles
    );
  }
};
""".strip()

	TRIGGER_ID = "post-login"  # Login flow trigger
	
	class Auth0ActionsManager:
		"""Manage Auth0 Actions via Management API"""

		def __init__(self, domain: str, client_id: str, client_secret: str):
			self.domain = domain
			self.base_url = f"https://{domain}/api/v2"
			self.client_id = client_id
			self.client_secret = client_secret
			self.token: Optional[str] = None

		def get_token(self):
			"""Get Management API access token"""
			typer.echo("🔑 Getting access token...")

			url = f"https://{self.domain}/oauth/token"
			payload = {
				"client_id": self.client_id,
				"client_secret": self.client_secret,
				"audience": f"https://{self.domain}/api/v2/",
				"grant_type": "client_credentials",
			}

			response = requests.post(url, json=payload)
			response.raise_for_status()

			self.token = response.json()["access_token"]
			typer.echo("✅ Token obtained")

		def _headers(self):
			"""Get auth headers for API requests"""
			return {
				"Authorization": f"Bearer {self.token}",
				"Content-Type": "application/json",
			}

		def list_actions(self, trigger_id=None):
			"""List all actions, optionally filtered by trigger"""
			url = f"{self.base_url}/actions/actions"
			if trigger_id:
				url += f"?triggerId={trigger_id}"

			response = requests.get(url, headers=self._headers())
			response.raise_for_status()
			return response.json()

		def get_action_by_name(self, name):
			"""Find action by name"""
			actions = self.list_actions()
			for action in actions.get("actions", []):
				if action["name"] == name:
					return action
			return None

		def create_action(self, name, code, trigger_id):
			"""Create a new action"""
			typer.echo(f"📝 Creating Action: {name}...")

			url = f"{self.base_url}/actions/actions"
			payload = {
				"name": name,
				"supported_triggers": [{"id": trigger_id, "version": "v3"}],
				"code": code,
				"runtime": "node18",
			}

			response = requests.post(url, headers=self._headers(), json=payload)
			response.raise_for_status()

			action = response.json()
			typer.echo(f"✅ Action created: {redact_text(action['id'])}")
			return action

		def deploy_action(self, action_id):
			"""Deploy an action"""
			typer.echo(f"🚀 Deploying Action {redact_text(action_id)}...")

			url = f"{self.base_url}/actions/actions/{action_id}/deploy"
			response = requests.post(url, headers=self._headers())
			response.raise_for_status()

			typer.echo("✅ Action deployed")
			return response.json()

		def get_trigger_bindings(self, trigger_id):
			"""Get current bindings for a trigger (Login flow)"""
			url = f"{self.base_url}/actions/triggers/{trigger_id}/bindings"
			response = requests.get(url, headers=self._headers())
			response.raise_for_status()
			return response.json()

		def update_trigger_bindings(self, trigger_id, action_id):
			"""Update trigger bindings to include our action"""
			# Get current bindings
			current = self.get_trigger_bindings(trigger_id)
			bindings = current.get("bindings", [])

			# Check if our action is already bound
			action_bound = any(b.get("action", {}).get("id") == action_id for b in bindings)

			if action_bound:
				typer.echo(f"✅ Action {redact_text(action_id)} already bound to {trigger_id}")
				return current

			# Add our action to bindings
			bindings.append({
				"action": {"id": action_id},
				"display_name": ACTION_NAME,
			})

			# Update bindings
			url = f"{self.base_url}/actions/triggers/{trigger_id}/bindings"
			payload = {"bindings": bindings}
			response = requests.patch(url, headers=self._headers(), json=payload)
			response.raise_for_status()

			typer.echo(f"✅ Action {redact_text(action_id)} bound to {trigger_id}")
			return response.json()

	# Get credentials from environment (same as auth0_management service)
	from backend.src.fi_auth.services.auth0_management import get_auth0_service
	service = get_auth0_service()
	
	# Extract domain and credentials from service
	domain = service.client.domain
	# We need to get the client_id and client_secret from the service
	# Since the service uses auth0-python, let's access the underlying client
	client_id = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
	client_secret = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")
	
	if not client_id or not client_secret:
		typer.echo("❌ Missing AUTH0_MANAGEMENT_CLIENT_ID or AUTH0_MANAGEMENT_CLIENT_SECRET environment variables")
		typer.echo("   These are required for Auth0 Actions management")
		raise typer.Exit(1)

	manager = Auth0ActionsManager(domain, client_id, client_secret)
	manager.get_token()

	# Check if action already exists
	existing = manager.get_action_by_name(ACTION_NAME)
	if existing:
		typer.echo(f"✅ Action already exists: {redact_text(existing['id'])}")
		typer.echo(f"   Status: {existing.get('status', 'unknown')}")
		action = existing

		# Check if already deployed
		if existing.get("status") != "built":
			typer.echo("   Deploying existing version...")
			manager.deploy_action(action["id"])
	else:
		# Create new action
		action = manager.create_action(ACTION_NAME, ACTION_CODE, TRIGGER_ID)

		# Deploy it
		manager.deploy_action(action["id"])

	typer.echo()

	# Bind to Login flow
	typer.echo("🔗 Configuring Login flow...")
	bindings = manager.update_trigger_bindings(TRIGGER_ID, action["id"])

	typer.echo()
	typer.echo("=" * 70)
	typer.echo("✅ CONFIGURATION COMPLETED")
	typer.echo("=" * 70)
	typer.echo()
	typer.echo(f"Action ID: {redact_text(action['id'])}")
	typer.echo(f"Trigger: {TRIGGER_ID}")
	typer.echo(f"Flow bindings: {len(bindings.get('bindings', []))} actions")
	typer.echo()
	typer.echo("🎯 Next steps:")
	typer.echo("   1. Go to Auth0 Dashboard → Actions → Flows → Login")
	typer.echo("   2. Verify that 'Add Roles to Token' appears in the flow")
	typer.echo("   3. Login to AURITY and verify the JWT at jwt.io")
	typer.echo("   4. Look for the claim: 'https://aurity.app/roles'")


@app.command("migrate-roles")
def migrate_roles(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be migrated without making changes")
    ] = False,
) -> None:
	"""
	Migrate Auth0 roles from FM-* (FerboliMovil) to FI-* (Free Intelligence).
	
	Maps FM-* roles to FI-* equivalents and migrates all users.
	Assigns FI-superadmin to specified superadmin email.
	"""
	import structlog
	
	logger = structlog.get_logger(__name__)

	# Role mapping: FM-* → FI-*
	ROLE_MAPPING = {
		"FM-Admin": "FI-admin",
		"FM-Doctor": "FI-doctor",
		"FM-Nurse": "FI-nurse",
		"FM-Staff": "FI-staff",
	}

	# Superadmin email
	SUPERADMIN_EMAIL = "bernarduriza@gmail.com"

	from backend.src.fi_auth.services.auth0_management import get_auth0_service
	service = get_auth0_service()

	typer.echo("=" * 70)
	typer.echo("🔄 ROLE MIGRATION: FM-* → FI-*")
	typer.echo("=" * 70)
	typer.echo()

	if dry_run:
		typer.echo("🔍 DRY RUN MODE - No changes will be made")
		typer.echo()

	# Step 1: Get all available roles
	typer.echo("📋 Getting available roles...")
	all_roles = service.list_roles()
	role_name_to_id = {r["name"]: r["id"] for r in all_roles}

	typer.echo(f"✅ Found {len(all_roles)} total roles")
	typer.echo(f"   FI-* roles: {[r for r in role_name_to_id if r.startswith('FI-')]}")
	typer.echo(f"   FM-* roles: {[r for r in role_name_to_id if r.startswith('FM-')]}")
	typer.echo()

	# Verify all FI-* roles exist
	missing_roles = []
	for fi_role in ROLE_MAPPING.values():
		if fi_role not in role_name_to_id:
			missing_roles.append(fi_role)

	if missing_roles:
		typer.echo("❌ ERROR: Missing FI-* roles in Auth0:")
		for role in missing_roles:
			typer.echo(f"   - {role}")
		typer.echo()
		typer.echo("⚠️  You must create these roles in Auth0 Dashboard first:")
		typer.echo("   Auth0 Dashboard → User Management → Roles → Create Role")
		raise typer.Exit(1)

	# Step 2: Get all users
	typer.echo("👥 Getting users...")
	response = service.list_users(per_page=100)
	users = response.get("users", [])
	typer.echo(f"✅ Found {len(users)} users")
	typer.echo()

	# Step 3: Migrate each user
	migrated_count = 0
	skipped_count = 0
	superadmin_assigned = False

	for user in users:
		user_id = user["user_id"]
		email = user["email"]

		# Get current roles
		current_roles = service.get_user_roles(user_id)
		current_role_names = [r["name"] for r in current_roles]

		# Check if user has FM-* roles
		fm_roles = [r for r in current_role_names if r.startswith("FM-")]

		if not fm_roles and email != SUPERADMIN_EMAIL:
			skipped_count += 1
			continue

		typer.echo(f"🔄 Migrating user: {redact_text(email)}")

		# Calculate new roles
		new_roles = []
		roles_to_remove = []

		# Map FM-* to FI-*
		for fm_role in fm_roles:
			if fm_role in ROLE_MAPPING:
				fi_role = ROLE_MAPPING[fm_role]
				new_roles.append(fi_role)
				roles_to_remove.append(fm_role)
				typer.echo(f"   {fm_role} → {fi_role}")

		# Assign superadmin if this is the superadmin email
		if email == SUPERADMIN_EMAIL:
			if "FI-superadmin" not in current_role_names:
				new_roles.append("FI-superadmin")
				typer.echo("   + FI-superadmin (superadmin email)")
				superadmin_assigned = True

		# Execute migration
		if not dry_run:
			try:
				# Remove old FM-* roles
				if roles_to_remove:
					role_ids_to_remove = [role_name_to_id[r] for r in roles_to_remove if r in role_name_to_id]
					if role_ids_to_remove:
						service.remove_roles(user_id, role_ids_to_remove)

				# Assign new FI-* roles
				if new_roles:
					role_ids_to_add = [role_name_to_id[r] for r in new_roles if r in role_name_to_id]
					if role_ids_to_add:
						service.assign_roles(user_id, role_ids_to_add)

				typer.echo("   ✅ Migration completed")
			except Exception as e:
				typer.echo(f"   ❌ Migration failed: {redact_text(str(e))}")
				continue
		else:
			typer.echo("   (dry run - no changes made)")

		migrated_count += 1
		typer.echo()

	# Summary
	typer.echo("=" * 70)
	typer.echo("📊 MIGRATION SUMMARY")
	typer.echo("=" * 70)
	typer.echo(f"✅ Migrated users: {migrated_count}")
	typer.echo(f"⏭️  Skipped users:  {skipped_count}")
	typer.echo(f"👑 Superadmin assigned: {'✅' if superadmin_assigned else '❌'}")
	typer.echo()

	if dry_run:
		typer.echo("🔍 This was a dry run - no changes were made")
		typer.echo("   Run without --dry-run to execute the migration")
	else:
		typer.echo("🎉 Role migration completed!")
		typer.echo("   Users should logout and login again to refresh their JWT tokens")


@app.command("setup-auth0-action")
def setup_auth0_action(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be configured without making changes")
    ] = False,
) -> None:
    """
    Setup Auth0 Action for JWT Custom Claims (Roles).
    
    Creates and deploys an Auth0 Action to add roles to JWT tokens,
    then binds it to the Login flow post-login trigger.
    
    The Action adds roles to both ID token (frontend) and Access token (backend)
    using the custom claim namespace: https://aurity.app/roles
    """
    import os
    import sys
    from pathlib import Path
    
    # Action configuration
    ACTION_NAME = "Add Roles to Token"
    ACTION_CODE = """
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://aurity.app';

  if (event.authorization) {
    // Add roles to ID token (frontend)
    api.idToken.setCustomClaim(
      `${namespace}/roles`,
      event.authorization.roles
    );

    // Add roles to access token (backend)
    api.accessToken.setCustomClaim(
      `${namespace}/roles`,
      event.authorization.roles
    );
  }
};
""".strip()
    
    TRIGGER_ID = "post-login"  # Login flow trigger
    
    typer.echo("=" * 70)
    typer.echo("🔧 CONFIGURACIÓN DE AUTH0 ACTION - JWT CUSTOM CLAIMS")
    typer.echo("=" * 70)
    typer.echo()
    
    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")
        typer.echo()
    
    try:
        # Lazy import to avoid module-level errors
        import requests
        from dotenv import load_dotenv
        
        # Load credentials from .claude/auth0_actions.env
        env_path = Path(__file__).parent.parent.parent.parent / ".claude" / "auth0_actions.env"
        load_dotenv(env_path)
        
        DOMAIN = os.getenv("AUTH0_DOMAIN")
        CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
        CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")
        
        if not all([DOMAIN, CLIENT_ID, CLIENT_SECRET]):
            typer.echo("❌ ERROR: Missing Auth0 credentials in .claude/auth0_actions.env")
            typer.echo("   Required: AUTH0_DOMAIN, AUTH0_MANAGEMENT_CLIENT_ID, AUTH0_MANAGEMENT_CLIENT_SECRET")
            raise typer.Exit(1)
        
        class Auth0ActionsManager:
            """Manage Auth0 Actions via Management API"""
            
            def __init__(self):
                self.domain = DOMAIN
                self.base_url = f"https://{DOMAIN}/api/v2"
                self.token = None
            
            def get_token(self):
                """Get Management API access token"""
                if dry_run:
                    typer.echo("🔑 Would obtain Management API access token...")
                    return
                
                typer.echo("🔑 Obtaining Management API access token...")
                
                url = f"https://{self.domain}/oauth/token"
                payload = {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "audience": f"https://{self.domain}/api/v2/",
                    "grant_type": "client_credentials",
                }
                
                response = requests.post(url, json=payload)
                response.raise_for_status()
                
                self.token = response.json()["access_token"]
                typer.echo("✅ Token obtained")
            
            def _headers(self):
                """Get auth headers for API requests"""
                return {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                }
            
            def list_actions(self, trigger_id=None):
                """List all actions, optionally filtered by trigger"""
                if dry_run:
                    return {"actions": []}
                
                url = f"{self.base_url}/actions/actions"
                if trigger_id:
                    url += f"?triggerId={trigger_id}"
                
                response = requests.get(url, headers=self._headers())
                response.raise_for_status()
                return response.json()
            
            def get_action_by_name(self, name):
                """Find action by name"""
                actions = self.list_actions()
                for action in actions.get("actions", []):
                    if action["name"] == name:
                        return action
                return None
            
            def create_action(self, name, code, trigger_id):
                """Create a new action"""
                typer.echo(f"📝 {'Would create' if dry_run else 'Creating'} Action: {name}...")
                
                if dry_run:
                    return {"id": "dry-run-action-id", "name": name}
                
                url = f"{self.base_url}/actions/actions"
                payload = {
                    "name": name,
                    "supported_triggers": [{"id": trigger_id, "version": "v3"}],
                    "code": code,
                    "runtime": "node18",
                }
                
                response = requests.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                
                action = response.json()
                typer.echo(f"✅ Action created: {action['id']}")
                return action
            
            def deploy_action(self, action_id):
                """Deploy an action"""
                typer.echo(f"🚀 {'Would deploy' if dry_run else 'Deploying'} Action {action_id}...")
                
                if dry_run:
                    return
                
                url = f"{self.base_url}/actions/actions/{action_id}/deploy"
                response = requests.post(url, headers=self._headers())
                response.raise_for_status()
                
                typer.echo("✅ Action deployed")
                return response.json()
            
            def get_trigger_bindings(self, trigger_id):
                """Get current bindings for a trigger (Login flow)"""
                if dry_run:
                    return {"bindings": []}
                
                url = f"{self.base_url}/actions/triggers/{trigger_id}/bindings"
                response = requests.get(url, headers=self._headers())
                response.raise_for_status()
                return response.json()
            
            def update_trigger_bindings(self, trigger_id, action_id):
                """Add action to trigger flow"""
                typer.echo(f"🔗 {'Would add' if dry_run else 'Adding'} Action to flow {trigger_id}...")
                
                if dry_run:
                    return {"bindings": [{"action": {"id": action_id}}]}
                
                # Get current bindings
                current = self.get_trigger_bindings(trigger_id)
                current_refs = [b["action"]["id"] for b in current.get("bindings", [])]
                
                # Check if already bound
                if action_id in current_refs:
                    typer.echo(f"⚠️  Action already in flow {trigger_id}")
                    return current
                
                # Add our action to the end
                current_refs.append(action_id)
                
                # Update bindings
                url = f"{self.base_url}/actions/triggers/{trigger_id}/bindings"
                payload = {
                    "bindings": [{"ref": {"type": "action_id", "value": aid}} for aid in current_refs]
                }
                
                response = requests.patch(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                
                typer.echo(f"✅ Action added to flow {trigger_id}")
                return response.json()
        
        manager = Auth0ActionsManager()
        manager.get_token()
        typer.echo()
        
        # Check if action already exists
        typer.echo(f"🔍 Checking if '{ACTION_NAME}' already exists...")
        existing = manager.get_action_by_name(ACTION_NAME)
        
        if existing:
            typer.echo(f"✅ Action already exists: {existing['id']}")
            typer.echo(f"   Status: {existing.get('status', 'unknown')}")
            action = existing
            
            # Check if already deployed
            if existing.get("status") != "built":
                typer.echo("   Deploying existing version...")
                manager.deploy_action(action["id"])
        else:
            # Create new action
            action = manager.create_action(ACTION_NAME, ACTION_CODE, TRIGGER_ID)
            
            # Deploy it
            manager.deploy_action(action["id"])
        
        typer.echo()
        
        # Bind to Login flow
        typer.echo("🔗 Configuring Login flow...")
        bindings = manager.update_trigger_bindings(TRIGGER_ID, action["id"])
        
        typer.echo()
        typer.echo("=" * 70)
        typer.echo("✅ CONFIGURACIÓN COMPLETADA")
        typer.echo("=" * 70)
        typer.echo()
        typer.echo(f"Action ID: {action['id']}")
        typer.echo(f"Trigger: {TRIGGER_ID}")
        typer.echo(f"Flow bindings: {len(bindings.get('bindings', []))} actions")
        typer.echo()
        typer.echo("🎯 Next steps:")
        typer.echo("   1. Go to Auth0 Dashboard → Actions → Flows → Login")
        typer.echo("   2. Verify 'Add Roles to Token' appears in the flow")
        typer.echo("   3. Login to AURITY and verify JWT at jwt.io")
        typer.echo("   4. Look for claim: 'https://aurity.app/roles'")
        typer.echo()
        
    except ImportError as e:
        typer.echo(f"❌ Missing dependencies: {e}", err=True)
        typer.echo("Install with: pip install requests python-dotenv", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error: {redact_text(str(e))}", err=True)
        raise typer.Exit(1)


@app.command("verify-audience")
def verify_audience(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname or IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key-path", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
) -> None:
    """
    Verify Auth0 audience configuration on production server.
    
    Checks that the audience is set to app.aurity.io (without api subdomain).
    Uses SSH key authentication. Requires root access on production server.
    """
    import json
    from pathlib import Path
    
    # Lazy import paramiko
    try:
        import paramiko
    except ImportError:
        typer.echo("❌ paramiko not installed. Install with: pip install paramiko", err=True)
        raise typer.Exit(1)
    
    if not Path(key_path).expanduser().exists():
        typer.echo(f"❌ SSH key not found: {key_path}", err=True)
        raise typer.Exit(1)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        typer.echo(f"🔑 Connecting to {host} as {user}...")
        client.connect(host, username=user, key_filename=os.path.expanduser(key_path), timeout=30)
        typer.echo("✅ Connected")
        
        # Get config response
        typer.echo("📡 Fetching /api/auth/config...")
        stdin, stdout, stderr = client.exec_command("curl -s http://localhost:7001/api/auth/config")
        response = stdout.read().decode()
        
        typer.echo("\n📋 Full response:")
        typer.echo("=" * 80)
        
        try:
            config = json.loads(response)
            typer.echo(json.dumps(config, indent=2))
            
            typer.echo("\n" + "=" * 80)
            audience = config.get("audience")
            typer.echo(f"🎯 Current audience: {audience}")
            
            if audience == "https://app.aurity.io":
                typer.echo("✅ CORRECT - No 'api.' subdomain")
            elif audience == "https://api.app.aurity.io":
                typer.echo("❌ INCORRECT - Still has 'api.' subdomain")
            else:
                typer.echo(f"⚠️  UNEXPECTED - Value: {audience}")
                
        except json.JSONDecodeError:
            typer.echo(response)
            typer.echo("\n❌ Response is not valid JSON")
            raise typer.Exit(1)
            
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    finally:
        client.close()


@app.command("patch-auth0-config")
def patch_auth0_config(
    host: Annotated[
        str,
        typer.Option("--host", help="Production server hostname or IP")
    ] = "104.131.175.65",
    user: Annotated[
        str,
        typer.Option("--user", help="SSH username")
    ] = "root",
    key_path: Annotated[
        str,
        typer.Option("--key-path", help="Path to SSH private key")
    ] = "~/.ssh/id_rsa",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without making changes")
    ] = False,
) -> None:
    """
    Patch auth0_config.py on production server to update API identifier.
    
    Changes the AUTH0_API_IDENTIFIER from old duckdns domain to new app.aurity.io domain.
    Restarts backend and verifies the change. Uses SSH key authentication.
    """
    import time
    from pathlib import Path
    
    # Lazy import paramiko
    try:
        import paramiko
    except ImportError:
        typer.echo("❌ paramiko not installed. Install with: pip install paramiko", err=True)
        raise typer.Exit(1)
    
    if not Path(key_path).expanduser().exists():
        typer.echo(f"❌ SSH key not found: {key_path}", err=True)
        raise typer.Exit(1)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        typer.echo(f"🔑 Connecting to {host} as {user}...")
        if dry_run:
            typer.echo("   (dry-run: would connect)")
        else:
            client.connect(host, username=user, key_filename=os.path.expanduser(key_path), timeout=30)
        typer.echo("✅ Connected")
        
        # Read current file
        typer.echo("\n📖 Reading current auth0_config.py...")
        if dry_run:
            typer.echo("   (dry-run: would read file)")
            current_content = "# Mock content for dry-run"
        else:
            stdin, stdout, stderr = client.exec_command(
                "cat /opt/free-intelligence/backend/auth/auth0_config.py"
            )
            current_content = stdout.read().decode()
        typer.echo(f"   Size: {len(current_content)} bytes")
        
        # Patch the file
        typer.echo("\n🔧 Preparing patch...")
        old_line = 'AUTH0_API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.fi-aurity.duckdns.org")'
        new_line = 'AUTH0_API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.app.aurity.io")'
        
        new_content = current_content.replace(old_line, new_line)
        
        if new_content == current_content:
            typer.echo("⚠️  No line found to patch (may already be updated)")
        else:
            typer.echo("✅ Patch prepared")
            if dry_run:
                typer.echo("   (dry-run: would apply patch)")
        
        # Write patched file
        if not dry_run and new_content != current_content:
            typer.echo("\n💾 Writing patched file...")
            stdin, stdout, stderr = client.exec_command(
                f"cat > /opt/free-intelligence/backend/auth/auth0_config.py << 'ENDOFFILE'\n{new_content}\nENDOFFILE"
            )
            stdout.channel.recv_exit_status()
            typer.echo("✅ File updated")
        elif dry_run:
            typer.echo("\n💾 (dry-run: would write patched file)")
        
        # Restart backend
        typer.echo("\n🔄 Restarting backend...")
        if dry_run:
            typer.echo("   (dry-run: would restart backend)")
        else:
            stdin, stdout, stderr = client.exec_command("pkill -9 -f 'python.*main'")
            stdout.channel.recv_exit_status()
            time.sleep(2)
            
            start_cmd = """
            cd /opt/free-intelligence && \
            export PYTHONPATH=/opt/free-intelligence:$PYTHONPATH && \
            nohup python3.14 -m backend.app.main > /tmp/backend.log 2>&1 &
            """
            stdin, stdout, stderr = client.exec_command(start_cmd)
            stdout.channel.recv_exit_status()
            typer.echo("✅ Backend restarted")
        
        # Wait
        typer.echo("\n⏳ Waiting 8 seconds...")
        if not dry_run:
            time.sleep(8)
        
        # Verify
        typer.echo("\n🧪 Verifying new audience...")
        if dry_run:
            typer.echo("   (dry-run: would verify audience)")
            result = '{"audience": "https://api.app.aurity.io"}'
        else:
            stdin, stdout, stderr = client.exec_command(
                "curl -s http://localhost:7001/api/auth/config"
            )
            result = stdout.read().decode()
        
        typer.echo("📋 Full response:")
        typer.echo("=" * 80)
        typer.echo(result)
        typer.echo("=" * 80)
        
        if "api.app.aurity.io" in result:
            typer.echo("✅ AUDIENCE UPDATED SUCCESSFULLY!")
        else:
            typer.echo("❌ Audience NOT updated")
            if not dry_run:
                typer.echo("\n📋 Last logs:")
                stdin, stdout, stderr = client.exec_command("tail -n 20 /tmp/backend.log")
                typer.echo(stdout.read().decode())
        
        typer.echo("\n" + "=" * 80)
        typer.echo("✅ PATCH APPLIED")
        typer.echo("=" * 80)
        typer.echo("""
Permanent change applied:
- auth0_config.py updated on server
- audience: https://api.app.aurity.io

Test login from your mobile device now.
        """)
        
    except Exception as e:
        typer.echo(f"❌ Error: {redact_text(str(e))}", err=True)
        raise typer.Exit(1)
    finally:
        if not dry_run:
            client.close()


@app.command("migrate-roles-fm-to-fi")
def migrate_roles_fm_to_fi(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be migrated without making changes")
    ] = False,
) -> None:
    """
    Migrate Auth0 roles from FM-* (FerboliMovil) to FI-* (Free Intelligence).
    
    Maps FM-* roles to FI-* equivalents, removes old roles, assigns new ones.
    Assigns FI-superadmin to bernarduriza@gmail.com.
    """
    from backend.src.fi_auth.services.auth0_management import get_auth0_service
    
    typer.echo("🔄 Migrating Auth0 roles: FM-* → FI-*")
    typer.echo("=" * 70)
    
    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No changes will be made")
    
    service = get_auth0_service()
    
    # Role mapping
    role_mapping = {
        "FM-Admin": "FI-admin",
        "FM-Doctor": "FI-doctor",
        "FM-Nurse": "FI-nurse",
        "FM-Staff": "FI-staff",
    }
    superadmin_email = "bernarduriza@gmail.com"
    
    # Step 1: Get all available roles
    typer.echo("📋 Getting available roles...")
    all_roles = service.list_roles()
    role_name_to_id = {r["name"]: r["id"] for r in all_roles}
    
    typer.echo(f"✅ Found {len(all_roles)} total roles")
    fi_roles = [r for r in role_name_to_id if r.startswith('FI-')]
    fm_roles = [r for r in role_name_to_id if r.startswith('FM-')]
    typer.echo(f"   FI-* roles: {fi_roles}")
    typer.echo(f"   FM-* roles: {fm_roles}")
    typer.echo()
    
    # Verify all FI-* roles exist
    missing_roles = []
    for fi_role in role_mapping.values():
        if fi_role not in role_name_to_id:
            missing_roles.append(fi_role)
    
    if missing_roles:
        typer.echo("❌ ERROR: Missing FI-* roles in Auth0:")
        for role in missing_roles:
            typer.echo(f"   - {role}")
        typer.echo()
        typer.echo("⚠️  Create these roles in Auth0 Dashboard first:")
        typer.echo("   Auth0 Dashboard → User Management → Roles → Create Role")
        raise typer.Exit(1)
    
    # Step 2: Get all users
    typer.echo("👥 Getting users...")
    response = service.list_users(per_page=100)
    users = response.get("users", [])
    typer.echo(f"✅ Found {len(users)} users")
    typer.echo()
    
    # Step 3: Migrate each user
    migrated_count = 0
    skipped_count = 0
    superadmin_assigned = False
    
    for user in users:
        user_id = user["user_id"]
        email = user["email"]
        
        # Get current roles
        current_roles = service.get_user_roles(user_id)
        current_role_names = [r["name"] for r in current_roles]
        
        # Check if user has FM-* roles
        fm_roles = [r for r in current_role_names if r.startswith("FM-")]
        
        if not fm_roles and email != superadmin_email:
            typer.echo(f"⏭️  {email:40} → No FM-* roles, skipping")
            skipped_count += 1
            continue
        
        typer.echo(f"🔄 {email:40}")
        typer.echo(f"   Current roles: {', '.join(current_role_names) or '(none)'}")
        
        # Build new role set
        roles_to_remove = []
        roles_to_add = []
        
        # Map FM-* to FI-*
        for fm_role in fm_roles:
            if fm_role in role_mapping:
                fi_role = role_mapping[fm_role]
                
                # Get role IDs
                fm_role_id = role_name_to_id[fm_role]
                fi_role_id = role_name_to_id[fi_role]
                
                roles_to_remove.append(fm_role_id)
                roles_to_add.append(fi_role_id)
                
                typer.echo(f"   📝 {fm_role} → {fi_role}")
        
        # Add FI-superadmin to specific email
        if email == superadmin_email:
            if "FI-superadmin" in role_name_to_id:
                superadmin_id = role_name_to_id["FI-superadmin"]
                if superadmin_id not in roles_to_add:
                    roles_to_add.append(superadmin_id)
                    typer.echo("   ⭐ Assigning FI-superadmin")
                    superadmin_assigned = True
        
        # Execute migration
        try:
            if roles_to_remove and not dry_run:
                service.remove_roles(user_id, roles_to_remove)
                typer.echo(f"   ✅ Removed {len(roles_to_remove)} FM-* roles")
            elif roles_to_remove:
                typer.echo(f"   🔍 Would remove {len(roles_to_remove)} FM-* roles")
            
            if roles_to_add and not dry_run:
                service.assign_roles(user_id, roles_to_add)
                typer.echo(f"   ✅ Assigned {len(roles_to_add)} FI-* roles")
            elif roles_to_add:
                typer.echo(f"   🔍 Would assign {len(roles_to_add)} FI-* roles")
            
            migrated_count += 1
            typer.echo()
            
        except Exception as e:
            typer.echo(f"   ❌ ERROR: {redact_text(str(e))}")
            typer.echo()
            continue
    
    # Summary
    typer.echo("=" * 70)
    typer.echo("📊 MIGRATION SUMMARY")
    typer.echo("=" * 70)
    typer.echo(f"✅ Users migrated: {migrated_count}")
    typer.echo(f"⏭️  Users unchanged: {skipped_count}")
    typer.echo(f"⭐ Superadmin assigned: {'Yes' if superadmin_assigned else 'No'}")
    typer.echo()
    
    if not dry_run:
        typer.echo("🎉 Migration completed successfully!")
        typer.echo()
        
        # Verify
        typer.echo("🔍 Verifying results...")
        response = service.list_users(per_page=100)
        users = response.get("users", [])
        
        fi_role_count = 0
        fm_role_count = 0
        
        for user in users:
            roles = service.get_user_roles(user["user_id"])
            role_names = [r["name"] for r in roles]
            
            fi_roles = [r for r in role_names if r.startswith("FI-")]
            fm_roles = [r for r in role_names if r.startswith("FM-")]
            
            fi_role_count += len(fi_roles)
            fm_role_count += len(fm_roles)
        
        typer.echo(f"   Total FI-* roles: {fi_role_count}")
        typer.echo(f"   Total FM-* roles: {fm_role_count}")
        typer.echo()
        
        if fm_role_count > 0:
            typer.echo("⚠️  Some FM-* roles still assigned")
        else:
            typer.echo("✅ All FM-* roles have been migrated")
    else:
        typer.echo("🔍 Dry run completed - no changes made")
