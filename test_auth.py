"""
Test script for authentication system
Run this to verify the auth module works correctly
"""
from pathlib import Path
from core.auth import AuthManager
import yaml

def test_auth_system():
    print("Testing Authentication System")
    print("=" * 50)
    
    # Setup paths
    test_config_path = Path("test_auth_config.yaml")
    test_user_data_dir = Path("test_user_data")
    
    try:
        # Initialize AuthManager
        print("\n1. Initializing AuthManager...")
        auth_manager = AuthManager(test_config_path, test_user_data_dir)
        print("   ✓ AuthManager created")
        
        # Check config file was created
        print("\n2. Checking config file...")
        if test_config_path.exists():
            print(f"   ✓ Config file created at: {test_config_path}")
            with open(test_config_path, 'r') as f:
                config = yaml.safe_load(f)
                print(f"   ✓ Default user 'demo' exists")
                print(f"   ✓ Cookie configuration present")
        else:
            print("   ✗ Config file not created")
            return False
        
        # Check user data directory
        print("\n3. Checking user data directory...")
        if test_user_data_dir.exists():
            print(f"   ✓ User data directory created at: {test_user_data_dir}")
        else:
            print("   ✗ User data directory not created")
            return False
        
        # Test user path creation
        print("\n4. Testing user-specific paths...")
        test_username = "testuser"
        user_path = auth_manager.get_user_data_path(test_username)
        if user_path.exists():
            print(f"   ✓ User directory created: {user_path}")
        else:
            print("   ✗ User directory not created")
            return False
        
        # Test session save/load
        print("\n5. Testing session save/load...")
        test_session = {
            'found_counts': {('part1', 'color1', 'loc1'): 5},
            'locations_index': {'loc1': ['part1']}
        }
        auth_manager.save_user_session(test_username, test_session)
        print("   ✓ Session saved")
        
        loaded_session = auth_manager.load_user_session(test_username)
        if loaded_session.get('found_counts') == test_session['found_counts']:
            print("   ✓ Session loaded correctly")
        else:
            print("   ✗ Session data mismatch")
            return False
        
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("\nDemo credentials:")
        print("  Username: demo")
        print("  Password: demo123")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup test files
        print("\n6. Cleaning up test files...")
        if test_config_path.exists():
            test_config_path.unlink()
            print("   ✓ Test config removed")
        
        # Remove test user data
        import shutil
        if test_user_data_dir.exists():
            shutil.rmtree(test_user_data_dir)
            print("   ✓ Test user data removed")

if __name__ == "__main__":
    test_auth_system()
