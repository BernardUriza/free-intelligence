#!/usr/bin/env python3
"""
Setup Auth0 Action for JWT Custom Claims (Roles)

This script:
1. Creates an Auth0 Action to add roles to JWT tokens
2. Deploys the Action
3. Binds it to the Login flow (post-login trigger)

The Action adds roles to both ID token (frontend) and Access token (backend)
using the custom claim namespace: https://aurity.app/roles

Usage:
    python3 scripts/setup_auth0_action.py

Requirements:
    - Auth0 M2M app with Actions scopes (read:actions, create:actions, etc.)
    - Credentials in .claude/auth0_actions.env

Author: Claude Code
Date: 2025-11-20
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load credentials from .claude/auth0_actions.env
env_path = Path(__file__).parent.parent / ".claude" / "auth0_actions.env"
load_dotenv(env_path)

DOMAIN = os.getenv("AUTH0_DOMAIN")
CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")

if not all([DOMAIN, CLIENT_ID, CLIENT_SECRET]):
    print("❌ ERROR: Missing Auth0 credentials in .claude/auth0_actions.env")
    sys.exit(1)

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

    def __init__(self):
        self.domain = DOMAIN
        self.base_url = f"https://{DOMAIN}/api/v2"
        self.token = None

    def get_token(self):
        """Get Management API access token"""
        print("🔑 Obteniendo token de acceso...")

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
        print("✅ Token obtenido")

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
        print(f"📝 Creando Action: {name}...")

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
        print(f"✅ Action creada: {action['id']}")
        return action

    def deploy_action(self, action_id):
        """Deploy an action"""
        print(f"🚀 Desplegando Action {action_id}...")

        url = f"{self.base_url}/actions/actions/{action_id}/deploy"
        response = requests.post(url, headers=self._headers())
        response.raise_for_status()

        print("✅ Action desplegada")
        return response.json()

    def get_trigger_bindings(self, trigger_id):
        """Get current bindings for a trigger (Login flow)"""
        url = f"{self.base_url}/actions/triggers/{trigger_id}/bindings"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def update_trigger_bindings(self, trigger_id, action_id):
        """Add action to trigger flow"""
        print(f"🔗 Agregando Action al flow {trigger_id}...")

        # Get current bindings
        current = self.get_trigger_bindings(trigger_id)
        current_refs = [b["action"]["id"] for b in current.get("bindings", [])]

        # Check if already bound
        if action_id in current_refs:
            print(f"⚠️  Action ya está en el flow {trigger_id}")
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

        print(f"✅ Action agregada al flow {trigger_id}")
        return response.json()


def main():
    """Main setup function"""
    print("=" * 70)
    print("🔧 CONFIGURACIÓN DE AUTH0 ACTION - JWT CUSTOM CLAIMS")
    print("=" * 70)
    print()

    manager = Auth0ActionsManager()
    manager.get_token()
    print()

    # Check if action already exists
    print(f"🔍 Verificando si '{ACTION_NAME}' ya existe...")
    existing = manager.get_action_by_name(ACTION_NAME)

    if existing:
        print(f"✅ Action ya existe: {existing['id']}")
        print(f"   Estado: {existing.get('status', 'unknown')}")
        action = existing

        # Check if already deployed
        if existing.get("status") != "built":
            print("   Desplegando versión existente...")
            manager.deploy_action(action["id"])
    else:
        # Create new action
        action = manager.create_action(ACTION_NAME, ACTION_CODE, TRIGGER_ID)

        # Deploy it
        manager.deploy_action(action["id"])

    print()

    # Bind to Login flow
    print(f"🔗 Configurando Login flow...")
    bindings = manager.update_trigger_bindings(TRIGGER_ID, action["id"])

    print()
    print("=" * 70)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("=" * 70)
    print()
    print(f"Action ID: {action['id']}")
    print(f"Trigger: {TRIGGER_ID}")
    print(f"Flow bindings: {len(bindings.get('bindings', []))} actions")
    print()
    print("🎯 Próximos pasos:")
    print("   1. Ve a Auth0 Dashboard → Actions → Flows → Login")
    print("   2. Verifica que 'Add Roles to Token' aparezca en el flow")
    print("   3. Haz login en AURITY y verifica el JWT en jwt.io")
    print("   4. Busca la claim: 'https://aurity.app/roles'")
    print()


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
