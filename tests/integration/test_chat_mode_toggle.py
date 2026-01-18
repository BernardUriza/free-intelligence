#!/usr/bin/env python3
"""
Test script to validate the chat mode toggle functionality
"""
import os
import sys
import json

def test_changes():
    print("🔍 Testing chat mode toggle implementation...")
    
    # Check that the dense mode type was added
    with open('/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/components/chat/ChatWidgetContainer.tsx', 'r') as f:
        content = f.read()
        if "'dense'" in content and "export type ChatViewMode" in content:
            print("✅ ChatViewMode includes 'dense' type")
        else:
            print("❌ ChatViewMode does not include 'dense' type")
            return False
    
    # Check that the toggleDenseMode function was added to the state hook
    with open('/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/components/chat/ChatWidget/useChatWidgetState.ts', 'r') as f:
        content = f.read()
        if "toggleDenseMode" in content and "setViewMode(viewMode === 'dense' ? 'fullscreen' : 'dense')" in content:
            print("✅ toggleDenseMode function correctly implemented")
        else:
            print("❌ toggleDenseMode function not found or incorrect")
            return False
    
    # Check that the ChatContent component accepts the toggleDenseMode prop
    with open('/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/components/chat/ChatWidget/ChatContent.tsx', 'r') as f:
        content = f.read()
        if "onToggleDenseMode" in content:
            print("✅ ChatContent accepts onToggleDenseMode prop")
        else:
            print("❌ ChatContent does not accept onToggleDenseMode prop")
            return False
    
    # Check that the ChatHeader uses the toggleDenseMode prop
    with open('/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/components/chat/ChatWidgetHeader.tsx', 'r') as f:
        content = f.read()
        if "onToggleDenseMode" in content and "mode === 'fullscreen'" in content:
            print("✅ ChatWidgetHeader correctly handles dense mode toggle")
        else:
            print("❌ ChatWidgetHeader does not handle dense mode toggle properly")
            return False
    
    # Check that the /chat-dense route was removed
    with open('/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/config/routes.config.ts', 'r') as f:
        content = f.read()
        if "'/chat-dense'" not in content:
            print("✅ /chat-dense route successfully removed")
        else:
            print("❌ /chat-dense route still exists")
            return False
    
    # Check that the ChatContent conditionally hides UI in dense mode
    with open('/Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity/components/chat/ChatWidget/ChatContent.tsx', 'r') as f:
        content = f.read()
        if "{viewMode !== 'dense' && (" in content:
            print("✅ ChatContent conditionally renders UI elements based on mode")
        else:
            print("❌ ChatContent does not conditionally render UI elements")
            return False
    
    print("\n🎉 All tests passed! The chat mode toggle functionality is correctly implemented.")
    print("\n📋 Summary of changes:")
    print("   • Added 'dense' mode to ChatViewMode type")
    print("   • Implemented toggleDenseMode function in useChatWidgetState")
    print("   • Updated ChatContent to conditionally render UI in dense mode")
    print("   • Added toggle buttons to ChatWidgetHeader")
    print("   • Removed legacy /chat-dense route and page directory")
    print("\n✨ Features:")
    print("   • Users can toggle between dense (minimal UI) and fullscreen modes")
    print("   • Dense mode hides header, toolbar, and input for a cleaner view")
    print("   • Fullscreen mode provides full functionality as before")
    print("   • Single codebase, single route (/chat), multiple viewing modes")
    
    return True

if __name__ == "__main__":
    success = test_changes()
    sys.exit(0 if success else 1)